import numpy as np
import pandas as pd

class PortfolioCompany:
    """
    Simple LBO-ish model for a portfolio company.
    Produces yearly free cash flow to equity and exit proceeds.
    """

    def __init__(self,
                 name: str,
                 entry_ev: float,
                 entry_year: int,
                 revenue: float,
                 revenue_cagr: float,
                 ebitda_margin: float,
                 capex_pct_revenue: float,
                 change_wc_pct_revenue: float,
                 debt_percent: float,
                 debt_annual_interest: float,
                 debt_amort_annual: float,
                 hold_period: int,
                 exit_ev_ebitda_multiple: float,
                 exit_year=None):
        self.name = name
        self.entry_ev = float(entry_ev)
        self.entry_year = entry_year
        self.revenue = float(revenue)
        self.revenue_cagr = float(revenue_cagr)
        self.ebitda_margin = float(ebitda_margin)
        self.capex_pct_revenue = float(capex_pct_revenue)
        self.change_wc_pct_revenue = float(change_wc_pct_revenue)
        self.debt_percent = float(debt_percent)  # of EV at entry
        self.debt_annual_interest = float(debt_annual_interest)
        self.debt_amort_annual = float(debt_amort_annual)
        self.hold_period = int(hold_period)
        self.exit_ev_ebitda_multiple = float(exit_ev_ebitda_multiple)
        self.exit_year = exit_year or (self.entry_year + self.hold_period)

        # derived
        self.entry_debt = self.entry_ev * self.debt_percent
        self.entry_equity = self.entry_ev - self.entry_debt

    def project(self):
        """
        Returns dataframe with yearly P&L, free cash flow to equity, and exit proceeds at the final year.
        """
        years = [self.entry_year + i for i in range(self.hold_period + 1)]
        df = pd.DataFrame(index=years)
        df.index.name = "year"

        # revenue path
        rev = [self.revenue * ((1 + self.revenue_cagr) ** i) for i in range(self.hold_period + 1)]
        df['revenue'] = rev
        df['ebitda'] = df['revenue'] * self.ebitda_margin
        # assume tax rate = 25% (simple)
        tax_rate = 0.25
        df['tax'] = df['ebitda'] * tax_rate
        df['capex'] = df['revenue'] * self.capex_pct_revenue
        df['change_wc'] = df['revenue'] * self.change_wc_pct_revenue
        # interest & debt schedule (simple)
        debt_balances = []
        bal = self.entry_debt
        for i in range(self.hold_period + 1):
            debt_balances.append(max(bal, 0.0))
            # amortize at end of year (not below 0)
            bal = bal - self.debt_amort_annual
        df['debt_balance'] = debt_balances
        # interest expense
        df['interest'] = df['debt_balance'] * self.debt_annual_interest
        # pre-tax income approximated as ebitda - interest
        df['pre_tax_income'] = df['ebitda'] - df['interest']
        df['net_income'] = df['pre_tax_income'] * (1 - tax_rate)
        # Free cash flow to firm ~ EBITDA - tax - capex - change WC + depreciation (ignore dep)
        df['fcf'] = df['ebitda'] - df['tax'] - df['capex'] - df['change_wc'] - df['interest']  # approx
        # Free cash flow to equity (after debt amortization and interest)
        # Equity FCF adds back debt amortization as source of funds is equity -> simplified:
        df['debt_amort'] = [min(self.debt_amort_annual, db) for db in df['debt_balance']]
        df['fcfe'] = df['fcf'] + df['debt_amort'] * 0  # keep simple; more advanced treat differently

        # Exit at final year
        exit_ebitda = df['ebitda'].iloc[-1]
        exit_ev = exit_ebitda * self.exit_ev_ebitda_multiple
        exit_debt = df['debt_balance'].iloc[-1]
        exit_equity_value = exit_ev - exit_debt

        df['exit_ev'] = 0.0
        df.at[self.exit_year, 'exit_ev'] = exit_ev
        df['exit_debt'] = 0.0
        df.at[self.exit_year, 'exit_debt'] = exit_debt
        df['exit_equity_value'] = 0.0
        df.at[self.exit_year, 'exit_equity_value'] = exit_equity_value

        # Cash flows to equity timeline: at entry (negative), distributions at exit (positive).
        # We will create a separate series for fund-level cashflows.
        return df

class Fund:
    """
    Holds multiple PortfolioCompany objects, aggregates fund cashflows, computes DPI, TVPI, IRR.
    """

    def __init__(self, name: str, committed_capital: float):
        self.name = name
        self.committed_capital = float(committed_capital)
        self.deals = []

    def add_deal(self, pc: PortfolioCompany, equity_invested_pct=1.0):
        """
        equity_invested_pct = fraction of entry_equity funded by this fund (useful if syndication)
        """
        self.deals.append((pc, float(equity_invested_pct)))

    def aggregate_cashflows(self):
        """
        Builds a time series of net fund cash flows:
        - Negative at entry: capital calls (equity invested)
        - Positive at exit: exit proceeds distributed to fund (assume fully distributed)
        Returns a pandas Series indexed by year.
        """
        all_years = set()
        entries = []
        exits = []
        for pc, pct in self.deals:
            df = pc.project()
            entry_year = pc.entry_year
            equity = pc.entry_equity * pct
            all_years.add(entry_year)
            # entry capital call: negative
            entries.append((entry_year, -equity))
            # exit distributions:
            exit_year = pc.exit_year
            exit_equity_value = df['exit_equity_value'].sum()  # nonzero only at exit row
            all_years.add(exit_year)
            exits.append((exit_year, float(exit_equity_value * pct)))

        years = sorted(all_years)
        cash = {y: 0.0 for y in years}
        for y, amt in entries:
            cash[y] += amt
        for y, amt in exits:
            cash[y] += amt

        # Convert to pandas Series
        s = pd.Series(cash).sort_index()
        s.index.name = 'year'
        return s

    def metrics(self):
        """
        Returns DPI, TVPI, IRR as dict.
        For TVPI we treat unrealized = 0 (or could accept marks if available).
        """
        cf = self.aggregate_cashflows()
        paid_in = -cf[cf < 0].sum()  # positive number
        distributions = cf[cf > 0].sum()
        dpi = distributions / paid_in if paid_in > 0 else np.nan
        # TVPI = (distributions + residual value) / paid_in. Residual assumed 0 here.
        tvpi = (distributions + 0.0) / paid_in if paid_in > 0 else np.nan

        # Compute IRR: need cashflow vector ordered by year
        # fill missing years between min and max
        years = list(range(int(cf.index.min()), int(cf.index.max()) + 1))
        cf_full = pd.Series(0.0, index=years)
        for y, v in cf.items():
            cf_full.at[int(y)] = v
        # Convert to list in chronological order
        cf_list = cf_full.tolist()
        # Use numpy_financial if available; fallback to numpy.irr
        try:
            import numpy_financial as nf
            irr = nf.irr(cf_list)
        except Exception:
            irr = np.irr(cf_list)
        return {"DPI": dpi, "TVPI": tvpi, "IRR": irr, "cashflows": cf_full}
