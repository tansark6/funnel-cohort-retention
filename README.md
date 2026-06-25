# 📊 Acquisition Funnel & Cohort Retention Analyzer

An interactive Streamlit app that analyzes customer acquisition funnels and retention patterns from e-commerce transaction data — built to demonstrate the **acquisition and retention** stage of the customer lifecycle.
🔗 **Live Demo:** [funnel-cohort-retention-tansark.streamlit.app](https://funnel-cohort-retention-tansark.streamlit.app/)
🔗 **GitHub Repo:** [github.com/tansark6/funnel-cohort-retention](https://github.com/tansark6/funnel-cohort-retention)

---

## Overview

Most acquisition analytics stops at "how many customers did we get?" This project goes a step further and asks two more useful questions:

1. **Where do customers drop off after their first purchase?** (the funnel)
2. **How long do they actually stick around, and does that vary by when they joined?** (the cohort retention pattern)

The app is fully interactive — upload your own transaction CSV, or explore the bundled sample dataset out of the box.

---

## Key Insights (on the sample dataset)

| Metric | Value |
|---|---|
| Total customers analyzed | 5,878* |
| Customers who made a 2nd purchase within 90 days | 46.7% |
| Customers who became repeat/loyal buyers (3rd+ purchase within 180 days) | 33.1% of total (71.0% of those who reached stage 2) |
| Retention by month 1 | ~23% |
| Retention pattern after month 1 | Flattens out, hovering ~20–30% |

*\*Figures shown are from a representative cleaned sample; see [Dataset](#dataset) below.*

**The headline finding:** the steepest customer loss happens in the **first month** after acquisition — retention drops from 100% to ~23% almost immediately, then stabilizes into a long, fairly flat tail. This suggests retention spend is best **front-loaded into the first 30 days** post-purchase (onboarding sequences, early incentives, follow-up outreach) rather than spread evenly across a customer's lifetime — since whoever survives that first month tends to stay engaged at a roughly steady rate afterward.

---

## Features

- 📁 **Upload your own data** or use the bundled sample dataset
- 📉 **Purchase-Frequency Funnel** — tracks customers through Acquired → Activated → Loyal stages
- 🔥 **Cohort Retention Heatmap** — classic month-of-acquisition × months-since-acquisition retention grid
- 📈 **Weighted Retention Curve** — overall retention trend across all cohorts combined
- 🔢 **Key metrics dashboard** — total customers, repeat purchase rate, retention at 1/3 months
- ⬇️ **Export** — download the computed retention table as CSV

---

## Dataset

**Source:** [Online Retail II](https://www.kaggle.com/datasets/lakshmi25npathi/online-retail-dataset) (UCI / Kaggle) — real transaction data from a UK-based online retailer selling unique all-occasion gift items, Dec 2009–Dec 2011.

- **Raw size:** ~1.07M transaction line items
- **Columns:** `Invoice`, `StockCode`, `Description`, `Quantity`, `InvoiceDate`, `Price`, `Customer ID`, `Country`

This dataset has no browse/cart event data (unlike a typical web analytics funnel), so the funnel here is defined by **purchase frequency** rather than browse-to-buy behavior — see [Methodology](#methodology) for the exact stage definitions.

---

## Methodology

**1. Cleaning**
- Removed transactions with missing `Customer ID` (anonymous/guest checkouts — can't be tracked across a journey)
- Removed cancelled orders (`Invoice` prefixed with `C`)
- Removed non-positive quantity/price rows (data entry errors, adjustments)

**2. Cohort Assignment**
- Each customer's **cohort** = the calendar month of their first purchase
- **Cohort Index** = number of months elapsed since that first purchase, for every subsequent transaction

**3. Retention Table**
- For each cohort, calculated the % of customers still making purchases in each subsequent month
- This produces the classic cohort retention heatmap (rows = acquisition month, columns = months since acquisition)

**4. Purchase-Frequency Funnel**
Since the data lacks top-of-funnel browse events, the funnel is redefined around purchase recency:
- **Stage 1 — Acquired:** made a first purchase
- **Stage 2 — Activated:** made a 2nd purchase within 90 days of the first
- **Stage 3 — Loyal:** made a 3rd+ purchase within 180 days of the first

Stages are **strictly nested** (Stage 3 is always a subset of Stage 2, which is always a subset of Stage 1) — an early version of this logic calculated each stage independently, which briefly produced a non-monotonic funnel (Stage 3 > Stage 2). Fixed by requiring Stage 3 customers to have already qualified for Stage 2.

**5. Weighted Retention Curve**
A simple average across cohorts would overweight short-lived cohorts that haven't had time to churn yet. Instead, the curve is weighted by how many customers were actually *eligible* to be retained at each month (i.e., cohorts old enough to have reached that point).

---

## Tech Stack

- **Python** — pandas, numpy
- **Visualization** — Plotly (interactive charts inside Streamlit)
- **App framework** — Streamlit
- **Data storage** — PyArrow / Parquet (see note below)

---

## A Data Engineering Note: Why Parquet?

The raw dataset is ~254MB as a CSV — over GitHub's 100MB file size limit. Rather than using Git LFS, the cleaned dataset is shipped as a **compressed Parquet file** instead:

- Cleaning removes ~23% of rows (missing IDs, cancellations, bad values)
- Parquet's columnar compression shrinks repetitive fields (country names, stock codes) dramatically
- **Result: 254MB → 9.48MB (96% size reduction)**, comfortably under GitHub's limits and fast to load on Streamlit Cloud

The app still accepts full raw CSV uploads at runtime — only the *bundled default dataset* uses the pre-cleaned Parquet shortcut.

---

## Project Structure

```
funnel-cohort-retention/
│
├── data/
│   └── raw/
│       └── online_retail_II_cleaned.parquet   # bundled sample dataset (cleaned, compressed)
│
├── notebooks/
│   └── 01_exploration.ipynb                   # full build process: cleaning → cohorts → funnel → viz
│
├── app/
│   └── app.py                                 # deployed Streamlit app
│
├── outputs/
│   └── figures/                               # exported chart images
│
├── requirements.txt
└── README.md
```

---

## Running Locally

```bash
git clone https://github.com/tansark6/funnel-cohort-retention.git
cd funnel-cohort-retention

conda create -n funnel-cohort-project python=3.11
conda activate funnel-cohort-project
pip install -r requirements.txt

streamlit run app/app.py
```

---

## Future Improvements

- Add channel/country-level filtering to the dashboard
- Extend the funnel with CAC (Customer Acquisition Cost) once cost-per-channel data is available
- Add statistical testing (e.g., comparing retention rates across cohorts or countries) to validate observed differences aren't due to chance

---

## Author

Built as part of a data analytics portfolio targeting acquisition, retention, and customer lifecycle analytics roles.
