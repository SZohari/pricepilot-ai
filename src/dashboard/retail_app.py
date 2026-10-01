"""Germany-focused portfolio workspace; UI is an adapter over shared use cases."""
from datetime import date
import os
from decimal import Decimal
import streamlit as st
from src.application.service import PricingService, demo_service, load_demo
from src.infrastructure.repository import SQLiteRepository
from src.domain.models import Scenario, Strategy
from src.dashboard.views import decisions, data_workspace

STYLE = """
<style>
.block-container {max-width: 1280px; padding-top: 2rem;}
[data-testid="stMetric"] {border:1px solid #d6e3e0;border-radius:12px;padding:16px;}
</style>
"""


def main():
    st.set_page_config(page_title="PricePilot | Retail Decision Intelligence", page_icon="ًں“ٹ", layout="wide")
    st.markdown(STYLE, unsafe_allow_html=True)
    st.title("PricePilot")
    st.caption("RETAIL DECISION INTELLIGENCE آ· GERMANY / EUR")
    configured_path = os.getenv("PRICEPILOT_DB_PATH")
    modes = ["Isolated demo"] + (["Local workspace"] if configured_path else [])
    mode = st.sidebar.radio("Workspace", modes)
    key = "retail_service_" + mode
    if key not in st.session_state:
        st.session_state[key] = (PricingService(SQLiteRepository(configured_path))
                                  if mode == "Local workspace" else demo_service())
    service = st.session_state[key]
    is_demo = mode == "Isolated demo"
    st.sidebar.caption("Synthetic products and prices. Edits stay in this session." if is_demo
                       else "Persistent local workspace. Changes are saved to SQLite.")
    reference_date = load_demo().as_of if is_demo else date.today()
    as_of = st.sidebar.date_input("Analysis date", value=reference_date, key="analysis_date_" + mode)
    strategy_names = ["Use product strategies"] + [s.value for s in Strategy]
    selected = st.sidebar.selectbox("Pricing strategy", strategy_names,
                                    format_func=lambda s: s.replace("_", " ").title())
    cost_change = st.sidebar.slider("Replacement-cost change (%)", -50, 100, 0, 5)
    st.sidebar.caption("Stress-test sourcing costs; market offers remain unchanged.")
    max_age = st.sidebar.slider("Maximum offer age (days)", 0, 60, 14)
    scenario = Scenario(as_of=as_of, cost_change_pct=Decimal(cost_change), max_age_days=max_age,
                        strategy=None if selected == strategy_names[0] else Strategy(selected))
    st.info("Demo evidence, explicit assumptions, human decisions. Recommendations never update a store automatically.")
    tab1, tab2, tab3 = st.tabs(["Decision workspace", "Data workspace", "Method & business case"])
    with tab1:
        decisions.render(service.recommendations(scenario))
    with tab2:
        data_workspace.render(service, as_of)
    with tab3:
        st.subheader("From market evidence to a reviewable decision")
        st.write("PricePilot helps a small retailer compare delivered market prices with sourcing costs, "
                 "inventory pressure and contribution-margin constraints.")
        st.markdown("""
1. **Data:** validate inputs; use the latest available offer per seller; exclude stale and future offers.
2. **Decision intelligence:** compare six deterministic strategies and make uncertainty visible.
3. **Business:** protect a minimum contribution margin and flag large or unsupported moves for review.

**Contribution margin** = (net revenue âˆ’ replacement cost âˆ’ variable cost âˆ’ fees) / net revenue.
Consumer prices include the configured VAT. Costs are net; fees are a share of net revenue.

The demo uses a configurable 19% VAT assumption. It does not model every tax case.
A reference date makes this synthetic scenario reproducible; it is not a current market feed.

**AI roadmap:** establish a reproducible policy baseline, collect dated price/sales outcomes, then
evaluate demand forecasts with time-based holdouts. No measured profit uplift or trained AI is claimed.
""")
        st.caption("Future UX clients can use the versioned /api/v1 endpoints without duplicating pricing logic.")
