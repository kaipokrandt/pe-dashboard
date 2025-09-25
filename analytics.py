import plotly.graph_objects as go
import pandas as pd
import numpy as np
from scipy.interpolate import interp1d

def plot_jcurve(cashflow_series: pd.Series, title="Fund J-Curve"):
    years = cashflow_series.index.tolist()
    cumulative = cashflow_series.cumsum()
    fig = go.Figure()
    fig.add_trace(go.Bar(x=years, y=cashflow_series.values, name="Net Cash Flow"))
    fig.add_trace(go.Scatter(x=years, y=cumulative.values, mode="lines+markers", name="Cumulative"))
    fig.update_layout(title=title, xaxis_title="Year", yaxis_title="USD")
    return fig

def sensitivity_grid_lbo(entry_ev, ebitda, exit_multiples, leverages, other_params_fn):
    """
    Example helper: produce grid of IRRs for combinations of exit multiple and leverage.
    - other_params_fn should be a function that returns a PortfolioCompany with modified inputs.
    """
    grid = pd.DataFrame(index=exit_multiples, columns=leverages, dtype=float)
    for m in exit_multiples:
        for l in leverages:
            pc = other_params_fn(exit_multiple=m, leverage=l)
            df = pc.project()
            # simplistic: compute equity IRR: entry equity negative, exit_equity positive
            entry_equity = pc.entry_equity
            exit_equity = df['exit_equity_value'].sum()
            # cashflow: [-entry_equity, 0,..., exit_equity]
            cashflows = [-entry_equity] + [0] * (pc.hold_period - 1) + [exit_equity]
            # use numpy_financial or numpy
            try:
                import numpy_financial as nf
                irr = nf.irr(cashflows)
            except Exception:
                irr = np.irr(cashflows)
            grid.at[m, l] = irr
    return grid

def plot_heatmap_grid(grid, title="Sensitivity Heatmap",
                      xaxis_title="X", yaxis_title="Y", colorscale="Viridis"):
    import plotly.graph_objects as go
    import matplotlib as mpl

    z = grid.values
    x = grid.columns.tolist()
    y = grid.index.tolist()

    # Build colormap to compute brightness
    cmap = mpl.cm.get_cmap(colorscale.lower() if isinstance(colorscale, str) else "viridis")

    
    # Normalize z values to [0, 1] for colormap
    norm = mpl.colors.Normalize(vmin=z.min(), vmax=z.max())

    fig = go.Figure(data=go.Heatmap(
        z=z,
        x=x,
        y=y,
        colorscale=colorscale,
        colorbar=dict(title="MOIC")
    ))

    # Add annotations with dynamic color
    for i, row in enumerate(y):
        for j, col in enumerate(x):
            val = z[i][j]
            rgba = cmap(norm(val))
            # Compute perceived brightness (luma)
            brightness = 0.299 * rgba[0] + 0.587 * rgba[1] + 0.114 * rgba[2]
            text_color = "black" if brightness > 0.6 else "white"

            fig.add_annotation(
                x=col,
                y=row,
                text=f"{val:.2f}",
                showarrow=False,
                font=dict(color=text_color, size=12)
            )

    fig.update_layout(
        title=title,
        xaxis_title=xaxis_title,
        yaxis_title=yaxis_title
    )

    return fig
