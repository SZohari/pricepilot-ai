"""Decision workspace and transparent product drill-down."""
import pandas as pd
import plotly.express as px
import streamlit as st
from src.dashboard.presentation import decision_table, money


def render(results):
    if not results:
        st.info("This workspace is empty. Import a dataset in Data workspace.")
        return
    review_count = sum(r.requires_review for r in results)
    ready_count = sum(r.quality.status == "ready" for r in results)
    blocked_count = sum(r.recommended_price_gross is None for r in results)
    columns = st.columns(4)
    for col, label, value in zip(columns, ["Products", "Ready market data", "Needs review", "Pricing blocked"],
                                 [len(results), ready_count, review_count, blocked_count]):
        col.metric(label, value)
    search = st.text_input("Find a product", placeholder="Search by name or product ID")
    review_only = st.checkbox("Show only products needing review")
    visible = [r for r in results if (not search or search.casefold() in f"{r.product_name} {r.product_id}".casefold())
               and (not review_only or r.requires_review)]
    if not visible:
        st.info("No products match these filters.")
        return
    table = decision_table(visible)
    st.dataframe(table, hide_index=True, width="stretch")
    st.download_button("Export decisions as CSV", table.to_csv(index=False), "pricepilot-decisions.csv", "text/csv")
    st.divider()
    choice = st.selectbox("Inspect a decision", options=range(len(visible)), format_func=lambda i: visible[i].product_name)
    rec = visible[choice]
    left, right = st.columns([3, 2])
    with left:
        st.subheader(rec.product_name)
        st.caption(f"{rec.product_id} | {rec.selected_strategy.value.replace('_', ' ').title()} | {rec.risk_level.title()} risk")
        cols = st.columns(3)
        cols[0].metric("Current gross price", money(rec.current_price_gross))
        cols[1].metric("Proposed gross price", money(rec.recommended_price_gross))
        cols[2].metric("Minimum gross price", money(rec.floor_price_gross))
        for reason in rec.reasons:
            st.write(f"- {reason}")
        if rec.requires_review:
            st.warning("Human review required. No store price is changed by this recommendation.")
        if rec.strategy_prices:
            chart = pd.DataFrame([{"Strategy": name.replace("_", " ").title(), "Gross EUR": float(price)}
                                  for name, price in rec.strategy_prices.items()])
            st.plotly_chart(px.bar(chart, x="Gross EUR", y="Strategy", orientation="h",
                                   color_discrete_sequence=["#0F766E"]), width="stretch")
    with right:
        st.subheader("Evidence quality")
        st.json(rec.quality.model_dump())
        st.caption("Freshness is evaluated against the selected analysis date. Prices include listed delivery charges.")
        with st.expander("Structured decision / API contract"):
            st.json(rec.model_dump(mode="json"))
