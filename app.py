import streamlit as st
import pandas as pd
import numpy as np
from models import PortfolioCompany, Fund
from analytics import plot_jcurve, plot_heatmap_grid
import io, tempfile, zipfile, xlsxwriter
import plotly.io as pio

st.set_page_config(layout="wide", page_title="PE Fund Analytics")

st.title("Private Equity Fund Analytics")
st.text("Analyze fund-level metrics and visualize the J-curve effect.")
st.text("Upload deals via CSV or add them manually.")
st.text("Explore sensitivity of fund returns to exit multiples and leverage.")
st.text("Please note this is a demo application.")
st.text("CSV upload format: Company,Industry,Entry_Year,Exit_Year,Entry_EBITDA,Entry_EBITDA_Multiple,Revenue_Growth_Rate,EBITDA_Margin,Capex_Percent,WC_Percent,Debt_to_EBITDA,Interest_Rate,Exit_EBITDA_Multiple,Equity_Contribution")

# --- Initialize fund in session_state ---
if "fund" not in st.session_state:
    st.session_state.fund = Fund("My PE Fund", 100_000_000.0)
 
# Sidebar: Fund settings
st.sidebar.header("Fund settings")
fund_name = st.sidebar.text_input("Fund name", st.session_state.fund.name)
committed_capital = st.sidebar.number_input(
    "Committed capital (USD)",
    value=st.session_state.fund.committed_capital,
    step=1_000_000.0
)

# Update the fund object
st.session_state.fund.name = fund_name
st.session_state.fund.committed_capital = committed_capital
fund = st.session_state.fund

# Reset fund button
if st.sidebar.button("🔄 Reset Fund (Clear Deals)"):
    st.session_state.fund = Fund(fund_name, committed_capital)
    st.sidebar.success("Fund and deals have been cleared.")

# --- Sidebar: Upload deals from CSV ---
st.sidebar.header("📂 Bulk Upload Deals (CSV)")
uploaded_file = st.sidebar.file_uploader("Upload CSV", type=["csv"])
if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    required_cols = [
        "Company","Industry","Entry_Year","Exit_Year",
        "Entry_EBITDA","Entry_EBITDA_Multiple",
        "Revenue_Growth_Rate","EBITDA_Margin",
        "Capex_Percent","WC_Percent",
        "Debt_to_EBITDA","Interest_Rate",
        "Exit_EBITDA_Multiple","Equity_Contribution"
    ]
    if all(col in df.columns for col in required_cols):
        # Clear existing CSV-uploaded deals first
        if "csv_deals" not in st.session_state:
            st.session_state.csv_deals = []
        else:
            # Remove old CSV deals from fund
            for pc, pct in st.session_state.csv_deals:
                if pc in [d[0] for d in fund.deals]:
                    fund.deals = [(dpc, dpct) for dpc, dpct in fund.deals if dpc != pc]
            st.session_state.csv_deals = []

        # Add new CSV deals
        for _, row in df.iterrows():
            entry_ev = row["Entry_EBITDA"] * row["Entry_EBITDA_Multiple"] * 1_000_000  
            revenue = (row["Entry_EBITDA"] * 1_000_000) / row["EBITDA_Margin"]  
            hold_period = int(row["Exit_Year"] - row["Entry_Year"])
            debt_value = row["Debt_to_EBITDA"] * row["Entry_EBITDA"] * 1_000_000
            debt_pct = debt_value / entry_ev if entry_ev > 0 else 0

            pc = PortfolioCompany(
                name=row["Company"],
                entry_ev=entry_ev,
                entry_year=int(row["Entry_Year"]),
                revenue=revenue,
                revenue_cagr=row["Revenue_Growth_Rate"],
                ebitda_margin=row["EBITDA_Margin"],
                capex_pct_revenue=row["Capex_Percent"],
                change_wc_pct_revenue=row["WC_Percent"],
                debt_percent=debt_pct,
                debt_annual_interest=row["Interest_Rate"],
                debt_amort_annual=0.0,
                hold_period=hold_period,
                exit_ev_ebitda_multiple=row["Exit_EBITDA_Multiple"]
            )
            equity_pct = row["Equity_Contribution"] * 1_000_000 / committed_capital if committed_capital > 0 else 0
            fund.add_deal(pc, equity_invested_pct=equity_pct)
            st.session_state.csv_deals.append((pc, equity_pct))

        st.sidebar.success(f"Uploaded {len(df)} deals from CSV")
    else:
        st.sidebar.error(f"CSV must include columns: {required_cols}")

# Sidebar: Add a deal manually
st.sidebar.header("Add a portfolio company (manual)")
with st.sidebar.form("add_deal_form", clear_on_submit=True):
    name = st.text_input("Deal name", "TargetCo")
    entry_ev = st.number_input("Entry EV (USD)", value=50_000_000.0, step=1_000_000.0)
    revenue = st.number_input("Current Revenue (USD)", value=20_000_000.0, step=100_000.0)
    revenue_cagr = st.number_input("Revenue CAGR (decimal)", value=0.10)
    ebitda_margin = st.number_input("EBITDA margin (decimal)", value=0.20)
    capex_pct = st.number_input("CapEx % revenue (decimal)", value=0.05)
    wc_pct = st.number_input("ΔWC % revenue (decimal)", value=0.01)
    debt_pct = st.number_input("Debt % of EV at entry (decimal)", value=0.5)
    debt_interest = st.number_input("Debt annual interest (decimal)", value=0.06)
    debt_amort = st.number_input("Debt annual amort (USD)", value=5_000_000.0)
    hold_period = st.number_input("Hold period (years)", value=5, min_value=1, max_value=10)
    exit_mult = st.number_input("Exit EV/EBITDA multiple", value=7.0)
    equity_contribution = st.number_input("Equity Contribution (USD)", value=10_000_000.0, step=1_000_000.0)
    submit = st.form_submit_button("Add deal")
    if submit:
        pc = PortfolioCompany(
            name=name,
            entry_ev=entry_ev,
            entry_year=2025,
            revenue=revenue,
            revenue_cagr=revenue_cagr,
            ebitda_margin=ebitda_margin,
            capex_pct_revenue=capex_pct,
            change_wc_pct_revenue=wc_pct,
            debt_percent=debt_pct,
            debt_annual_interest=debt_interest,
            debt_amort_annual=debt_amort,
            hold_period=hold_period,
            exit_ev_ebitda_multiple=exit_mult
        )
        # map equity contribution to % of fund committed capital
        equity_pct = equity_contribution / committed_capital if committed_capital > 0 else 0
        fund.add_deal(pc, equity_invested_pct=equity_pct)
        st.sidebar.success(f"Added {name}")

# Show current deals in fund
st.subheader("Deals in fund")
if len(fund.deals) == 0:
    st.info("No deals added. Add deals manually or upload CSV in the left sidebar.")
else:
    deals_summary = []
    for pc, pct in fund.deals:
        df = pc.project()
        entry_equity = pc.entry_equity * pct
        exit_equity = df['exit_equity_value'].sum() * pct
        moic = exit_equity / entry_equity if entry_equity != 0 else np.nan
        try:
            import numpy_financial as nf
            irr = nf.irr([-entry_equity] + [0] * (pc.hold_period - 1) + [exit_equity])
        except Exception:
            irr = np.irr([-entry_equity] + [0] * (pc.hold_period - 1) + [exit_equity])
        deals_summary.append({
            "name": pc.name,
            "entry_ev": pc.entry_ev,
            "entry_equity": entry_equity,
            "exit_equity": exit_equity,
            "MOIC": moic,
            "IRR": irr
        })
    st.dataframe(pd.DataFrame(deals_summary).set_index("name"))

    # Fund metrics
    metrics = fund.metrics()
    st.subheader("Fund-level metrics")
    col1, col2, col3 = st.columns(3)
    col1.metric("DPI", f"{metrics['DPI']:.2f}")
    col2.metric("TVPI", f"{metrics['TVPI']:.2f}")
    ir = metrics['IRR']
    col3.metric("IRR", f"{ir:.2%}" if not np.isnan(ir) else "N/A")

    # J-Curve
    st.subheader("J-Curve (net fund cashflows)")
    cf = metrics['cashflows']
    fig = plot_jcurve(cf, title="Fund J-Curve (Net Cash Flows & Cumulative)")
    st.plotly_chart(fig, use_container_width=True)

    # --- Sensitivity demo ---
    if st.checkbox("Show sensitivity: Exit Multiple × Leverage"):
        st.write("Heatmap showing fund MOIC across varying exit multiples and leverage assumptions.")

        # --- Sliders for base scenario ---
        base_exit_mult = st.slider("Base Exit Multiple (× EBITDA)", 5, 10, 7)
        base_leverage = st.slider("Base Leverage (% of EV)", 20, 70, 50)

        # Create grids around slider values
        exit_mults = [base_exit_mult - 2, base_exit_mult - 1, base_exit_mult, base_exit_mult + 1, base_exit_mult + 2]
        leverages = [(base_leverage - 20)/100, (base_leverage - 10)/100, base_leverage/100, (base_leverage + 10)/100, (base_leverage + 20)/100]

        # Clip values to reasonable bounds
        exit_mults = [max(1, x) for x in exit_mults]
        leverages = [min(max(0.0, l), 0.9) for l in leverages]



        def other_params_fn(exit_multiple, leverage):
            # Use sliders as starting point if needed
            return PortfolioCompany(
                name="sens",
                entry_ev=50_000_000,
                entry_year=2025,
                revenue=20_000_000,
                revenue_cagr=0.10,
                ebitda_margin=0.20,
                capex_pct_revenue=0.05,
                change_wc_pct_revenue=0.01,
                debt_percent=leverage,
                debt_annual_interest=0.06,
                debt_amort_annual=5_000_000,
                hold_period=5,
                exit_ev_ebitda_multiple=exit_multiple
            )

        from analytics import sensitivity_grid_lbo
        grid = sensitivity_grid_lbo(50_000_000, 20_000_000*0.20, exit_mults, leverages, other_params_fn)

        # Format table
        grid_display = grid.copy()
        grid_display = grid_display.applymap(lambda x: f"{x:.2f}" if isinstance(x, (int, float)) else x)

        col1, col2 = st.columns([1, 2])
        with col1:
            st.write("**MOIC Sensitivity Table**")
            st.dataframe(grid_display)

        with col2:
            st.write("**MOIC Heatmap**")
            fig = plot_heatmap_grid(
                grid,
                title="MOIC by Exit Multiple × Leverage",
                xaxis_title="Exit Multiple (× EBITDA)",
                yaxis_title="Leverage (% of EV)",
                colorscale="Viridis"
            )
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("""
        **Legend**  
        - **X-axis:** Exit EV/EBITDA multiple (valuation at exit).  
        - **Y-axis:** Debt financing at entry (as % of EV).  
        - **Cell values:** MOIC (multiple of invested capital).  
        - Lighter colors → higher MOIC.  
        """)

if st.button("Download Sensitivity Report"):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:

        # --- Excel ---
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
            # Write numeric and formatted sheets
            grid.to_excel(writer, sheet_name='sensitivity_grid', index=True)
            grid_display.to_excel(writer, sheet_name='sensitivity_display', index=True)

            workbook  = writer.book

            # Function to apply manual color interpolation
            def color_cells(ws, data):
                min_val, max_val = np.nanmin(data), np.nanmax(data)
                mid_val = (min_val + max_val) / 2
                for i, row in enumerate(data, start=1):
                    for j, val in enumerate(row, start=1):
                        if val <= mid_val:
                            # interpolate red → yellow
                            ratio = (val - min_val) / (mid_val - min_val + 1e-6)
                            red = 255
                            green = int(255 * ratio)
                            blue = 0
                        else:
                            # interpolate yellow → green
                            ratio = (val - mid_val) / (max_val - mid_val + 1e-6)
                            red = int(255 * (1 - ratio))
                            green = 255
                            blue = 0
                        hex_color = f'#{red:02X}{green:02X}{blue:02X}'
                        cell_format = workbook.add_format({'bg_color': hex_color})
                        ws.write(i, j, val, cell_format)

            # Apply coloring to both sheets
            color_cells(writer.sheets['sensitivity_grid'], grid.values)
            color_cells(writer.sheets['sensitivity_display'], grid.values)

        zip_file.writestr(f"{fund_name}_sensitivity.xlsx", excel_buffer.getvalue())

        # --- PDF heatmap ---
        tmpfile = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        pio.write_image(fig, tmpfile.name, format="pdf", width=800, height=600)
        with open(tmpfile.name, "rb") as f:
            zip_file.writestr(f"{fund_name}_heatmap.pdf", f.read())

    zip_buffer.seek(0)
    st.download_button(
        "Download Full Sensitivity Report (Excel + PDF)",
        data=zip_buffer,
        file_name=f"{fund_name}_sensitivity_report.zip"
    )
