# PE Fund Analytics Dashboard

if you wish to deploy this yourself, be my guest, I find streamlit very easy to develop in, and deploying is two clicks once you clone the repository to your own github. have fun!
My deployment is located at pedashboardapp.streamlit.app - make sure to download the sample csv or create your own following the syntax below!

## Overview

This Streamlit app is a **Private Equity Fund Analytics Dashboard** designed for small-scale, hands-on fund analysis. It allows a user to:

- Track deals and fund-level metrics.
- Visualize the fund J-Curve.
- Perform sensitivity analysis on **Exit Multiple × Leverage**.
- Export numerical tables and charts for reporting.

It is designed for single-person use but includes many features common in industry tools.

---

## Features

### 1. Fund Setup
- Set the fund name and committed capital in the sidebar.
- Reset fund and clear all deals.
- Supports both manual deal entry and CSV bulk uploads.

### 2. Deal Management
- **Manual Entry:** Add a portfolio company with detailed inputs:
  - Entry EV
  - Revenue & growth assumptions
  - EBITDA margin
  - CapEx & working capital percentages
  - Debt terms & hold period
  - Exit multiple
  - Equity contribution
- **CSV Upload:** Upload multiple deals at once with required columns:
```
Company,Industry,Entry_Year,Exit_Year,Entry_EBITDA,Entry_EBITDA_Multiple,Revenue_Growth_Rate,EBITDA_Margin,Capex_Percent,WC_Percent,Debt_to_EBITDA,Interest_Rate,Exit_EBITDA_Multiple,Equity_Contribution
```

### 3. Deal-Level Metrics
- Calculates **Entry Equity**, **Exit Equity**, **MOIC**, and **IRR** per deal.
- Displays all deals in a table for quick review.

### 4. Fund-Level Metrics
- Computes aggregated fund-level metrics:
  - **DPI (Distributions to Paid-In)**
  - **TVPI (Total Value to Paid-In)**
  - **IRR**
- Generates a **J-Curve visualization** showing net cash flows and cumulative distributions.

### 5. Sensitivity Analysis
- Interactive heatmap and table for **MOIC vs Exit Multiple × Leverage**.
- Sliders allow the user to set a **base exit multiple** and **base leverage**, dynamically updating the grid and heatmap.
- Displays both:
  - **Table:** Formatted numeric MOIC values.
  - **Heatmap:** Color-coded visual (lighter → higher MOIC).
- Allows download of **full sensitivity report** as a ZIP containing:
  - Excel spreadsheet (numeric table + formatted table)
  - PDF of the heatmap

### 6. Export Options
- Single ZIP file containing:
  - `Excel`: sensitivity table and formatted display
  - `PDF`: heatmap of MOIC across exit multiple and leverage
- Note: The Excel file is designed for **Microsoft Excel compatibility**. Conditional formatting may not render correctly in Google Sheets or Apple Numbers.

---

## Installation

1. Clone the repository:

```
git clone <repo_url>
```

2. Create a virtual environment:

```
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows
```

3. Install dependencies:

```
pip install -r requirements.txt
```

4. Run the dashboard:

```
streamlit run app.py
```

---

## Usage

1. **Sidebar Setup**
   - Enter fund name and committed capital.
   - Upload CSV or add deals manually.
   - Reset fund if needed.

2. **Main Panel**
   - View all deals and fund metrics.
   - Check the J-Curve to visualize fund cashflows.
   - Enable sensitivity analysis to see the MOIC heatmap and table.
   - Adjust sliders to simulate different exit multiples and leverage scenarios.

3. **Export Reports**
   - Click **Download Full Sensitivity Report** to get Excel + PDF in a ZIP.

---

## Notes

- The app is **designed for feasibility as a single-user tool**; it does not include multi-user authentication or complex LP reporting features.
- MOIC heatmaps and sensitivity tables are dynamically recalculated based on slider input.
- The Excel file contains **safe formatting** compatible with Excel; Google Sheets or Numbers may not render the conditional formatting perfectly.

---

## Dependencies

- Python 3.13+
- Streamlit
- Pandas
- Numpy
- Plotly
- XlsxWriter
- Tempfile
- Zipfile
- Numpy_financial (optional for IRR calculation)

---

## File Structure

- `app.py` — main Streamlit dashboard
- `models.py` — Fund and PortfolioCompany classes
- `analytics.py` — plotting and sensitivity grid functions
- `requirements.txt` — Python dependencies
- `README.md` — this file

---

## Author
  
kaipokrandt@gmail.com  

