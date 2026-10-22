"""Streamlit dashboard for the golden-cross trading strategy."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from trading_strategy import (
    calculate_moving_averages,
    get_stock_data,
    identify_golden_cross,
    implement_strategy,
)


st.set_page_config(
    page_title="MSFT Strategy Dashboard",
    page_icon="📈",
    layout="wide",
)

TICKER = "MSFT"
PERIOD = "5y"


@st.cache_data(ttl=3600, show_spinner="Loading market data and calculating trades...")
def load_dashboard_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load valid price rows and calculate the strategy data once per hour."""
    data = get_stock_data(TICKER, period=PERIOD)
    if data.empty or "Close" not in data.columns:
        raise ValueError(f"No historical price data was returned for {TICKER}.")

    # Exclude partial/missing closing-price rows so they cannot create invalid trades.
    data = data.loc[data["Close"].notna()].copy()
    if data.empty:
        raise ValueError(f"No valid closing prices were returned for {TICKER}.")

    data = calculate_moving_averages(data)
    data = identify_golden_cross(data)
    positions = implement_strategy(data)
    return data, positions


def create_price_chart(data: pd.DataFrame, positions: pd.DataFrame) -> go.Figure:
    """Build the price, moving-average, and trade-marker chart."""
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=data.index,
            y=data["Close"],
            name="Closing price",
            mode="lines",
            line={"color": "#17324d", "width": 2},
            hovertemplate="%{x|%b %d, %Y}<br>Close: $%{y:.2f}<extra></extra>",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=data.index,
            y=data["MA50"],
            name="50-day MA",
            mode="lines",
            line={"color": "#2f80ed", "width": 1.8},
            hovertemplate="%{x|%b %d, %Y}<br>50-day MA: $%{y:.2f}<extra></extra>",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=data.index,
            y=data["MA200"],
            name="200-day MA",
            mode="lines",
            line={"color": "#f0a43a", "width": 1.8},
            hovertemplate="%{x|%b %d, %Y}<br>200-day MA: $%{y:.2f}<extra></extra>",
        )
    )

    if not positions.empty:
        buys = positions.dropna(subset=["BuyDate", "BuyPrice"])
        sells = positions.dropna(subset=["SellDate", "SellPrice"])
        figure.add_trace(
            go.Scatter(
                x=buys["BuyDate"],
                y=buys["BuyPrice"],
                name="Buy",
                mode="markers",
                marker={
                    "color": "#18a66a",
                    "size": 12,
                    "symbol": "triangle-up",
                    "line": {"color": "white", "width": 1},
                },
                hovertemplate="BUY<br>%{x|%b %d, %Y}<br>Price: $%{y:.2f}<extra></extra>",
            )
        )
        figure.add_trace(
            go.Scatter(
                x=sells["SellDate"],
                y=sells["SellPrice"],
                name="Sell",
                mode="markers",
                marker={
                    "color": "#e05252",
                    "size": 12,
                    "symbol": "triangle-down",
                    "line": {"color": "white", "width": 1},
                },
                hovertemplate="SELL<br>%{x|%b %d, %Y}<br>Price: $%{y:.2f}<extra></extra>",
            )
        )

    figure.update_layout(
        template="plotly_white",
        height=570,
        margin={"l": 12, "r": 12, "t": 20, "b": 12},
        hovermode="x unified",
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "left",
            "x": 0,
        },
        xaxis={
            "title": None,
            "showgrid": False,
            "rangeslider": {"visible": True},
        },
        yaxis={
            "title": "Price (USD)",
            "tickprefix": "$",
            "gridcolor": "#edf1f5",
            "zeroline": False,
        },
        paper_bgcolor="white",
        plot_bgcolor="white",
    )
    return figure


def show_price_page(data: pd.DataFrame, positions: pd.DataFrame) -> None:
    """Show the full-period price chart and trade entry/exit markers."""
    st.title("Price chart")
    st.caption(
        f"{TICKER} · {PERIOD} of daily prices · 50-day and 200-day moving averages"
    )
    st.plotly_chart(
        create_price_chart(data, positions),
        width="stretch",
        config={"displaylogo": False, "responsive": True},
    )
    st.markdown(
        '<span class="legend-dot buy-dot"></span> Buy on golden cross'
        '&nbsp;&nbsp;&nbsp;'
        '<span class="legend-dot sell-dot"></span> Sell at target or holding limit',
        unsafe_allow_html=True,
    )
    st.caption("Drag the chart range selector to zoom in on a specific period.")


def show_statistics_page(positions: pd.DataFrame) -> None:
    """Show overall performance statistics for the strategy's trades."""
    st.title("Trade statistics")
    st.caption("Summary of all golden-cross trade signals.")

    total_trades = len(positions)
    if positions.empty:
        completed = positions.copy()
    else:
        completed = positions.dropna(
            subset=["BuyPrice", "SellPrice", "ProfitPct"]
        ).copy()
    wins = completed.loc[completed["ProfitPct"] > 0]
    losses = completed.loc[completed["ProfitPct"] <= 0]
    incomplete_count = total_trades - len(completed)
    win_rate = len(wins) / len(completed) * 100 if not completed.empty else 0
    average_return = completed["ProfitPct"].mean() if not completed.empty else None

    metrics = st.columns(4)
    metrics[0].metric("Total trades", total_trades)
    metrics[1].metric("Completed", len(completed))
    metrics[2].metric("Win rate", f"{win_rate:.1f}%" if not completed.empty else "—")
    metrics[3].metric(
        "Average return",
        f"{average_return:.2f}%" if average_return is not None else "—",
    )

    st.divider()
    left, right = st.columns(2)
    with left:
        st.subheader("Trade outcomes")
        outcome_cols = st.columns(3)
        outcome_cols[0].metric("Winning trades", len(wins))
        outcome_cols[1].metric("Losing trades", len(losses))
        outcome_cols[2].metric("Incomplete data", incomplete_count)
    with right:
        st.subheader("Holding period")
        if not completed.empty:
            st.metric("Average days held", f"{completed['HoldingDays'].mean():.1f}")
        else:
            st.metric("Average days held", "—")

    if not completed.empty:
        best_return = completed["ProfitPct"].max()
        worst_return = completed["ProfitPct"].min()
        best_cols = st.columns(2)
        best_cols[0].metric("Best trade", f"{best_return:.2f}%")
        best_cols[1].metric("Worst trade", f"{worst_return:.2f}%")

    if incomplete_count:
        st.info(
            f"{incomplete_count} trade(s) have missing price or return data. "
            "They are included in Total trades but excluded from completed-trade "
            "performance statistics."
        )
    if positions.empty:
        st.info("No golden-cross trade signals were detected in this period.")


def show_detailed_page(positions: pd.DataFrame) -> None:
    """Show each trade with formatted dates, prices, and return."""
    st.title("Detailed trades")
    st.caption("Trade-by-trade entry, exit, holding period, and outcome.")

    if positions.empty:
        st.info("No golden-cross trade signals were detected in this period.")
        return

    trades = positions.copy()
    trades["Status"] = trades["SellPrice"].notna().map(
        {True: "Complete", False: "Incomplete price data"}
    )
    trades["BuyDate"] = pd.to_datetime(trades["BuyDate"]).dt.strftime("%Y-%m-%d")
    trades["SellDate"] = pd.to_datetime(trades["SellDate"]).dt.strftime("%Y-%m-%d")
    trades = trades.rename(
        columns={
            "BuyDate": "Buy date",
            "BuyPrice": "Buy price ($)",
            "SellDate": "Sell date",
            "SellPrice": "Sell price ($)",
            "HoldingDays": "Holding days",
            "ProfitPct": "Return (%)",
            "SellReason": "Sell reason",
        }
    )
    display_columns = [
        "Status",
        "Buy date",
        "Buy price ($)",
        "Sell date",
        "Sell price ($)",
        "Holding days",
        "Return (%)",
        "Sell reason",
    ]
    st.dataframe(
        trades[display_columns],
        hide_index=True,
        width="stretch",
        column_config={
            "Buy price ($)": st.column_config.NumberColumn(format="$%.2f"),
            "Sell price ($)": st.column_config.NumberColumn(format="$%.2f"),
            "Return (%)": st.column_config.NumberColumn(format="%.2f%%"),
        },
    )


st.markdown(
    """
    <style>
    .block-container {padding-top: 2rem; padding-bottom: 2rem; max-width: 1400px;}
    [data-testid="stSidebar"] {background: #f4f7fb;}
    [data-testid="stMetric"] {
        background: #f7f9fc;
        border: 1px solid #e8edf3;
        padding: 16px 18px;
        border-radius: 12px;
    }
    .legend-dot {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 6px;
    }
    .buy-dot {background: #18a66a;}
    .sell-dot {background: #e05252;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.sidebar.title("MSFT Strategy")
st.sidebar.caption("Golden-cross backtest · 5-year view")
page = st.sidebar.radio(
    "Dashboard pages",
    ["Price chart", "Trade statistics", "Detailed trades"],
    label_visibility="collapsed",
)

try:
    market_data, trade_positions = load_dashboard_data()
except ValueError as error:
    st.error(str(error))
    st.stop()

if page == "Price chart":
    show_price_page(market_data, trade_positions)
elif page == "Trade statistics":
    show_statistics_page(trade_positions)
else:
    show_detailed_page(trade_positions)
