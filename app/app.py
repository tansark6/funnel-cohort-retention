import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Acquisition Funnel & Cohort Retention", layout="wide")

st.title("📊 Acquisition Funnel & Cohort Retention Analyzer")
st.markdown("Upload a transaction-level CSV (or use the sample dataset) to explore customer acquisition funnels and retention patterns.")

# ============================================================
# SIDEBAR — DATA INPUT
# ============================================================
st.sidebar.header("Data Input")
uploaded_file = st.sidebar.file_uploader("Upload your own CSV", type=["csv"])

if uploaded_file is not None:
    raw_source = uploaded_file
    st.sidebar.success("Using uploaded file")
else:
    raw_source = "data/raw/online_retail_II_cleaned.parquet"
    st.sidebar.info("Using default sample dataset (Online Retail II)")

st.sidebar.markdown("**Required columns:** `Invoice`, `Quantity`, `InvoiceDate`, `Price`, `Customer ID`")


# ============================================================
# CACHED PIPELINE FUNCTIONS
# ============================================================

@st.cache_data
def load_and_clean(source):
    # Pre-cleaned default dataset ships as Parquet (small, fast) -- skip re-cleaning
    if isinstance(source, str) and source.endswith('.parquet'):
        return pd.read_parquet(source)

    # User-uploaded files are raw CSVs -- run the full cleaning pipeline
    df = pd.read_csv(source, encoding='ISO-8859-1')

    df = df.dropna(subset=['Customer ID'])
    df = df[~df['Invoice'].astype(str).str.startswith('C')]
    df = df[(df['Quantity'] > 0) & (df['Price'] > 0)]
    df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'])
    df['Customer ID'] = df['Customer ID'].astype(int)
    df['TotalPrice'] = df['Quantity'] * df['Price']

    return df


@st.cache_data
def build_cohort_data(df):
    df = df.copy()
    df['InvoiceMonth'] = df['InvoiceDate'].dt.to_period('M')

    cohort_lookup = df.groupby('Customer ID')['InvoiceMonth'].min().reset_index()
    cohort_lookup.columns = ['Customer ID', 'CohortMonth']
    df = df.merge(cohort_lookup, on='Customer ID', how='left')

    def period_diff(later, earlier):
        return (later.year - earlier.year) * 12 + (later.month - earlier.month)

    df['CohortIndex'] = df.apply(lambda row: period_diff(row['InvoiceMonth'], row['CohortMonth']), axis=1)

    cohort_data = df.groupby(['CohortMonth', 'CohortIndex'])['Customer ID'].nunique().reset_index()
    cohort_data.columns = ['CohortMonth', 'CohortIndex', 'NumCustomers']
    cohort_counts = cohort_data.pivot(index='CohortMonth', columns='CohortIndex', values='NumCustomers')

    cohort_sizes = cohort_counts.iloc[:, 0]
    retention_table = cohort_counts.divide(cohort_sizes, axis=0) * 100

    return cohort_counts, retention_table, cohort_sizes


@st.cache_data
def build_funnel(df):
    orders = df.groupby(['Customer ID', 'Invoice'])['InvoiceDate'].min().reset_index()
    orders = orders.sort_values(['Customer ID', 'InvoiceDate'])
    orders['PurchaseRank'] = orders.groupby('Customer ID').cumcount() + 1

    first_purchase = orders[orders['PurchaseRank'] == 1][['Customer ID', 'InvoiceDate']]
    first_purchase = first_purchase.rename(columns={'InvoiceDate': 'FirstPurchaseDate'})
    orders = orders.merge(first_purchase, on='Customer ID')
    orders['DaysSinceFirst'] = (orders['InvoiceDate'] - orders['FirstPurchaseDate']).dt.days

    stage1_customers = orders['Customer ID'].nunique()

    second_orders = orders[orders['PurchaseRank'] == 2]
    stage2_ids = set(second_orders[second_orders['DaysSinceFirst'] <= 90]['Customer ID'])
    stage2_customers = len(stage2_ids)

    third_plus_orders = orders[(orders['PurchaseRank'] >= 3) & (orders['Customer ID'].isin(stage2_ids))]
    stage3_ids = set(third_plus_orders[third_plus_orders['DaysSinceFirst'] <= 180]['Customer ID'])
    stage3_customers = len(stage3_ids)

    funnel = pd.DataFrame({
        'Stage': ['1. First Purchase (Acquired)',
                  '2. Second Purchase within 90 days (Activated)',
                  '3. Third+ Purchase within 180 days (Loyal)'],
        'Customers': [stage1_customers, stage2_customers, stage3_customers]
    })
    funnel['% of Total'] = (funnel['Customers'] / stage1_customers * 100).round(1)
    funnel['% from Previous Stage'] = (funnel['Customers'] / funnel['Customers'].shift(1) * 100).round(1)
    funnel.loc[0, '% from Previous Stage'] = 100.0

    return funnel


def weighted_retention_curve(cohort_counts, cohort_sizes):
    """Average retention % per month, weighted by how many customers were actually
    eligible to be retained at that point (not all cohorts have reached every month)."""
    curve = []
    for col in cohort_counts.columns:
        valid = cohort_counts[col].notna()
        retained = cohort_counts.loc[valid, col].sum()
        eligible = cohort_sizes.loc[valid].sum()
        pct = (retained / eligible * 100) if eligible > 0 else np.nan
        curve.append(pct)
    return pd.Series(curve, index=cohort_counts.columns)


# ============================================================
# RUN PIPELINE
# ============================================================

try:
    df_clean = load_and_clean(raw_source)
    cohort_counts, retention_table, cohort_sizes = build_cohort_data(df_clean)
    funnel = build_funnel(df_clean)
    retention_curve = weighted_retention_curve(cohort_counts, cohort_sizes)
except Exception as e:
    st.error(f"Couldn't process this file: {e}")
    st.stop()


# ============================================================
# KEY METRICS CARDS
# ============================================================

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Customers", f"{df_clean['Customer ID'].nunique():,}")
col2.metric("Repeat Purchase Rate", f"{funnel.iloc[1]['% of Total']:.1f}%")
month1 = retention_curve.get(1, np.nan)
month3 = retention_curve.get(3, np.nan)
col3.metric("Avg Retention @ 1 mo", f"{month1:.1f}%" if pd.notna(month1) else "N/A")
col4.metric("Avg Retention @ 3 mo", f"{month3:.1f}%" if pd.notna(month3) else "N/A")

st.divider()


# ============================================================
# FUNNEL CHART
# ============================================================

st.subheader("Purchase-Frequency Funnel")
fig_funnel = go.Figure(go.Bar(
    x=funnel['Customers'],
    y=funnel['Stage'],
    orientation='h',
    text=[f"{c:,} ({p}%)" for c, p in zip(funnel['Customers'], funnel['% of Total'])],
    textposition='outside',
    marker_color=['#2c7fb8', '#41b6c4', '#a1dab4']
))
fig_funnel.update_layout(yaxis=dict(autorange="reversed"), xaxis_title="Number of Customers", height=400)
st.plotly_chart(fig_funnel, use_container_width=True)


# ============================================================
# COHORT HEATMAP
# ============================================================

st.subheader("Cohort Retention Heatmap")
# Plotly can't JSON-serialize pandas Period objects -- convert the cohort month
# index to plain strings before plotting (this only affects display, not the data)
retention_table_display = retention_table.copy()
retention_table_display.index = retention_table_display.index.astype(str)

fig_heatmap = px.imshow(
    retention_table_display,
    labels=dict(x="Months Since First Purchase", y="Cohort Month", color="Retention %"),
    color_continuous_scale="YlGnBu",
    zmin=0, zmax=100,
    aspect="auto"
)
fig_heatmap.update_xaxes(side="top")
st.plotly_chart(fig_heatmap, use_container_width=True)


# ============================================================
# RETENTION CURVE
# ============================================================

st.subheader("Overall Retention Curve (all cohorts combined)")
fig_curve = px.line(
    x=retention_curve.index, y=retention_curve.values,
    labels={'x': 'Months Since First Purchase', 'y': 'Retention %'},
    markers=True
)
fig_curve.update_yaxes(range=[0, 100])
st.plotly_chart(fig_curve, use_container_width=True)


# ============================================================
# DOWNLOAD
# ============================================================

st.divider()
st.download_button(
    "Download Retention Table (CSV)",
    retention_table.to_csv().encode('utf-8'),
    "retention_table.csv",
    "text/csv"
)