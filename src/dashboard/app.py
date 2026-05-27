"""Streamlit dashboard for pricing recommendations."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys
import io

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.data.sample_data_generator import load_sample_data
from src.data.build_pricing_dataset import load_processed_pricing_data
from src.data.manual_entry import (
    load_products_master,
    load_daily_market_updates,
    load_fx_rate_snapshots,
    append_daily_market_update,
    append_fx_rate_snapshot,
    get_latest_update_for_product,
    get_products_missing_update_today,
    validate_daily_market_update,
    validate_fx_rate_snapshot,
)
from src.data.build_pricing_dataset import build_dashboard_pricing_dataset, load_market_observations, load_retailer_internal_data, load_global_usd_reference
from src.pricing.recommendation import recommend_price
from src.utils.formatting import (
    format_toman,
    format_percent,
    format_margin,
    format_action_label,
    format_risk_label,
    format_price_comparison,
    get_risk_color,
    get_action_color,
    format_price_preview,
    format_price_input_value,
    parse_price_input,
    humanize_label,
)
from src.utils.validation import validate_csv_columns, validate_csv_data, get_column_info


def is_valid_source_link(link: str) -> bool:
    if not link:
        return False
    normalized = str(link).strip()
    if normalized == "":
        return False
    if normalized.lower() in {"#", "n/a", "na", "none"}:
        return False
    return True


def normalize_price_input_state(key: str) -> None:
    """Normalize a valid text price field to grouped English digits."""
    raw_value = st.session_state.get(key, "")
    parsed_value = parse_price_input(raw_value)
    if parsed_value is not None:
        st.session_state[key] = format_price_input_value(parsed_value)


def show_price_input_feedback(value: str) -> None:
    """Show immediate validation and readability feedback for a toman input."""
    parsed_value = parse_price_input(value)
    if value.strip() and parsed_value is None:
        st.warning("Please enter a valid number.")
        return

    preview = format_price_preview(parsed_value)
    if preview:
        st.markdown(f'<div dir="ltr"><code>{preview}</code></div>', unsafe_allow_html=True)
    if parsed_value is not None and parsed_value >= 100_000_000:
        st.warning("این عدد خیلی بزرگ است. مطمئن هستید قیمت را به تومان وارد کرده‌اید نه ریال؟")


def load_data_with_mode():
    """Load data from sample, processed real data, or uploaded CSV."""
    data_mode = st.sidebar.radio(
        "📂 Data Source",
        options=[
            "Sample Data (Generated)",
            "Processed Real Market Dataset",
            "Upload CSV"
        ],
        help="Choose between generated sample data, real market data, or upload your own CSV",
    )
    
    if data_mode == "Processed Real Market Dataset":
        st.sidebar.markdown("**Real Market Data**")
        try:
            df = load_processed_pricing_data()
            st.sidebar.success(f"✅ Loaded {len(df)} products from processed dataset")
            return df
        except FileNotFoundError as e:
            st.sidebar.warning(str(e))
            st.info(
                "📝 **To use real market data:**\n"
                "1. Edit files in `data/raw/`\n"
                "2. Run: `python scripts/build_pricing_dataset.py`\n"
                "3. Refresh this page"
            )
            return None
        except ValueError as e:
            st.sidebar.error(str(e))
            st.error(f"❌ Dataset validation failed: {str(e)}")
            return None
    
    elif data_mode == "Upload CSV":
        st.sidebar.markdown("**Upload Real Data**")
        uploaded_file = st.sidebar.file_uploader(
            "Choose CSV file",
            type=["csv"],
            help="CSV must contain all required columns"
        )
        
        if uploaded_file is not None:
            try:
                df = pd.read_csv(uploaded_file)
                
                # Validate columns
                col_valid, missing_cols = validate_csv_columns(df)
                if not col_valid:
                    st.sidebar.error(f"❌ Missing columns: {', '.join(missing_cols)}")
                    st.info("📋 **Required Columns:**\n" + get_column_info())
                    return None
                
                # Validate data
                data_valid, issues = validate_csv_data(df)
                if not data_valid:
                    st.sidebar.error(f"❌ Data issues:\n" + "\n".join(issues))
                    return None
                
                st.sidebar.success(f"✅ Loaded {len(df)} products")
                return df
                
            except Exception as e:
                st.sidebar.error(f"❌ Error reading file: {str(e)}")
                return None
        else:
            st.sidebar.info("📤 Waiting for CSV upload...")
            return None
    
    else:
        # Sample Data (Generated)
        return load_sample_data()


def main():
    """Main Streamlit application."""
    st.set_page_config(page_title="Pricing Intelligence", layout="wide")
    
    st.title("📊 Inflation-Aware Pricing Intelligence")
    st.markdown("Rule-based pricing recommendations for smartwatches in volatile markets")
    
    # Load data
    st.sidebar.title("⚙️ Controls")
    
    df = load_data_with_mode()
    
    if df is None or len(df) == 0:
        st.warning("⏳ Please load data using the sidebar to continue.")
        return
    
    # Pricing Strategy Selector (Phase 2)
    st.sidebar.markdown("---")
    is_phase2 = "our_current_price" in df.columns
    if is_phase2:
        st.sidebar.subheader("🎯 Pricing Strategy")
        strategy_label_map = {
            "trust_builder": "Trust Builder",
            "balanced": "Balanced",
            "profit_protection": "Profit Protection",
            "market_penetration": "Market Penetration",
            "premium_positioning": "Premium Positioning",
            "clearance_cashflow": "Clearance / Cashflow",
        }
        selected_strategy_label = st.sidebar.selectbox(
            "Strategy",
            options=list(strategy_label_map.values()),
            index=1,  # Default to "Balanced"
            help="Select pricing strategy for Phase 2 recommendations",
        )
        selected_strategy = {
            label: key for key, label in strategy_label_map.items()
        }[selected_strategy_label]
    else:
        selected_strategy = None
    
    # USD Shock Simulator
    st.sidebar.markdown("---")
    usd_shock = st.sidebar.slider(
        "💵 USD Exchange Rate Shock (%)",
        min_value=-10.0,
        max_value=30.0,
        value=0.0,
        step=0.5,
        help="Simulate USD rate changes to see price recommendations",
    )
    
    # Generate recommendations with USD shock
    @st.cache_data
    def get_recommendations(shock, data_hash, strategy_override):
        recommendations = []
        for _, row in df.iterrows():
            rec = recommend_price(row.to_dict(), usd_shock=shock, strategy=strategy_override)
            recommendations.append(rec)
        return pd.DataFrame(recommendations)
    
    recs_df = get_recommendations(usd_shock, hash(df.values.tobytes()), selected_strategy if is_phase2 else None)
    
    # KPI Section
    st.sidebar.markdown("---")
    st.sidebar.subheader("📈 Key Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Products", len(df))
    
    with col2:
        increase_count = (recs_df["action"] == "increase_price").sum()
        st.metric("↑ Increase", increase_count)
    
    with col3:
        decrease_count = (recs_df["action"] == "decrease_price").sum()
        st.metric("↓ Decrease", decrease_count)
    
    with col4:
        critical_count = (recs_df["risk_level"] == "critical").sum() + (recs_df["risk_level"] == "high").sum()
        st.metric("⚠ High Risk", critical_count)
    
    col5, col6 = st.columns(2)
    with col5:
        avg_margin = recs_df["current_margin"].mean()
        st.metric("Avg Margin", f"{avg_margin:.1%}")
    
    with col6:
        avg_rec_margin = recs_df["expected_margin"].mean()
        st.metric("Expected Margin", f"{avg_rec_margin:.1%}")
    
    # Filters
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔍 Filters")
    
    # Brand filter: only show if 'brand' column exists in recommendations
    if "brand" in recs_df.columns:
        brand_options = sorted(recs_df["brand"].unique())
        selected_brands = st.sidebar.multiselect(
            "Brand",
            options=brand_options,
            default=brand_options[:5] if len(brand_options) >= 5 else brand_options,
        )
    else:
        selected_brands = None
    
    action_label_map = {
        "increase_price": "Increase Price",
        "decrease_price": "Decrease Price",
        "hold_price": "Hold Price",
        "urgent_review": "Urgent Review",
    }
    selected_action_labels = st.sidebar.multiselect(
        "Action",
        options=list(action_label_map.values()),
        default=list(action_label_map.values()),
    )
    selected_actions = [
        key for key, label in action_label_map.items() if label in selected_action_labels
    ]
    
    risk_label_map = {
        "low": "Low",
        "medium": "Medium",
        "high": "High",
        "critical": "Critical",
    }
    selected_risk_labels = st.sidebar.multiselect(
        "Risk Level",
        options=list(risk_label_map.values()),
        default=list(risk_label_map.values()),
    )
    selected_risk_levels = [
        key for key, label in risk_label_map.items() if label in selected_risk_labels
    ]
    
    # Apply filters robustly
    filtered_recs = recs_df.copy()
    if selected_brands is not None and len(selected_brands) > 0:
        filtered_recs = filtered_recs[filtered_recs["brand"].isin(selected_brands)]
    if len(selected_actions) > 0:
        filtered_recs = filtered_recs[filtered_recs["action"].isin(selected_actions)]
    if len(selected_risk_levels) > 0:
        filtered_recs = filtered_recs[filtered_recs["risk_level"].isin(selected_risk_levels)]
    filtered_recs = filtered_recs.reset_index(drop=True)
    
    # Main content area
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["📋 Recommendations", "📊 Analytics", "⚡ USD Shock", "🔍 Details", "📝 Market Update"]
    )
    
    # Tab 1: Recommendations Table
    with tab1:
        st.subheader("Price Recommendations")
        st.markdown(f"Showing {len(filtered_recs)} of {len(recs_df)} products")
        
        # Prepare display columns based on schema (Phase 2 or MVP)
        if is_phase2:
            # Phase 2 schema: show market-aware and strategy columns
            display_fields = [
                "product_name",
                "brand",
                "base_usd_price",
                "usd_rate",
                "theoretical_toman_price",
                "iran_market_premium_pct",
                "market_min_price",
                "market_median_price",
                "market_max_price",
                "our_current_price",
                "recommended_price",
                "selected_strategy",
                "action",
                "risk_level",
            ]
        else:
            # MVP schema: show traditional columns
            display_fields = [
                "product_id",
                "product_name",
                "brand",
                "current_price",
                "recommended_price",
                "action",
                "risk_level",
                "current_margin",
                "expected_margin",
            ]
        
        # Ensure all display fields exist
        for col in display_fields:
            if col not in filtered_recs.columns:
                if col in ["brand", "product_id", "product_name", "action", "risk_level", "selected_strategy"]:
                    filtered_recs[col] = "Unknown"
                elif col in ["base_usd_price", "usd_rate", "theoretical_toman_price", "iran_market_premium_pct", 
                            "market_min_price", "market_median_price", "market_max_price", "our_current_price",
                            "current_price", "recommended_price", "current_margin", "expected_margin"]:
                    filtered_recs[col] = 0.0
                else:
                    filtered_recs[col] = None
        
        display_df = filtered_recs[display_fields].copy()
        
        # Format columns
        if "base_usd_price" in display_df.columns:
            display_df["Base USD Price"] = display_df["base_usd_price"].apply(
                lambda x: f"${x:.2f}" if x and x > 0 else "N/A"
            )
        if "usd_rate" in display_df.columns:
            display_df["USD Rate"] = display_df["usd_rate"].apply(
                lambda x: f"{x:,.0f}" if x and x > 0 else "N/A"
            )
        if "theoretical_toman_price" in display_df.columns:
            display_df["Theoretical Toman"] = display_df["theoretical_toman_price"].apply(
                lambda x: format_toman(x) if x and x > 0 else "N/A"
            )
        if "iran_market_premium_pct" in display_df.columns:
            display_df["Iran Premium %"] = display_df["iran_market_premium_pct"].apply(
                lambda x: format_percent(x) if x is not None else "N/A"
            )
        if "market_min_price" in display_df.columns:
            display_df["Market Min"] = display_df["market_min_price"].apply(
                lambda x: format_toman(x) if x and x > 0 else "N/A"
            )
        if "market_median_price" in display_df.columns:
            display_df["Market Median"] = display_df["market_median_price"].apply(
                lambda x: format_toman(x) if x and x > 0 else "N/A"
            )
        if "market_max_price" in display_df.columns:
            display_df["Market Max"] = display_df["market_max_price"].apply(
                lambda x: format_toman(x) if x and x > 0 else "N/A"
            )
        if "our_current_price" in display_df.columns:
            display_df["Our Current"] = display_df["our_current_price"].apply(
                lambda x: format_toman(x) if x and x > 0 else "N/A"
            )
        if "current_price" in display_df.columns and "Our Current" not in display_df.columns:
            display_df["Current Price"] = display_df["current_price"].apply(lambda x: format_toman(x))
        if "recommended_price" in display_df.columns:
            display_df["Recommended"] = display_df["recommended_price"].apply(lambda x: format_toman(x))
        if "selected_strategy" in display_df.columns:
            display_df["Strategy"] = display_df["selected_strategy"].apply(
                lambda x: humanize_label(x) if x else "N/A"
            )
        if "action" in display_df.columns:
            display_df["Action"] = display_df["action"].apply(format_action_label)
        if "risk_level" in display_df.columns:
            display_df["Risk"] = display_df["risk_level"].apply(format_risk_label)
        if "current_margin" in display_df.columns:
            display_df["Current Margin"] = display_df["current_margin"].apply(format_margin)
        if "expected_margin" in display_df.columns:
            display_df["Expected Margin"] = display_df["expected_margin"].apply(format_margin)
        
        # Select final display columns - avoid duplicates
        if is_phase2:
            display_cols_names = [
                "product_name",
                "brand",
                "Base USD Price",
                "Theoretical Toman",
                "Iran Premium %",
                "Market Median",
                "Our Current",
                "Recommended",
                "Strategy",
                "Action",
                "Risk",
            ]
        else:
            display_cols_names = [
                "product_id",
                "product_name",
                "brand",
                "Current Price",
                "Recommended",
                "Action",
                "Risk",
                "Current Margin",
                "Expected Margin",
            ]
        
        # Filter to only available columns
        available_cols = [c for c in display_cols_names if c in display_df.columns]
        display_cols = display_df[available_cols]
        
        st.dataframe(display_cols, use_container_width=True, hide_index=True)
    
    # Tab 2: Analytics
    with tab2:
        col1, col2 = st.columns(2)
        
        with col1:
            # Action distribution
            action_counts = filtered_recs["action"].value_counts()
            fig_actions = px.pie(
    values=action_counts.values,
    names=[humanize_label(name) for name in action_counts.index],
    title="📈 Price Actions Distribution",
    color_discrete_map={
        "increase_price": "#90EE90",
        "decrease_price": "#FFB6C1",
        "hold_price": "#FFFFCC",
        "urgent_review": "#FF6347",
    },
)
            st.plotly_chart(fig_actions, use_container_width=True)
        
        with col2:
            # Risk distribution
            risk_counts = filtered_recs["risk_level"].value_counts()
            fig_risk = px.pie(
    values=risk_counts.values,
    names=[humanize_label(name) for name in risk_counts.index],
    title="⚠️ Risk Level Distribution",
    color_discrete_map={
        "low": "#00CC00",
        "medium": "#FFAA00",
        "high": "#FF6600",
        "critical": "#CC0000",
    },
)
            st.plotly_chart(fig_risk, use_container_width=True)
        
        # Phase 2 specific analytics
        if is_phase2 and "iran_market_premium_pct" in filtered_recs.columns:
            st.subheader("🌍 Iran Market Premium Analysis")
            premium_fig = px.histogram(
                filtered_recs,
                x="iran_market_premium_pct",
                nbins=15,
                title="Iran Market Premium Distribution",
                labels={"iran_market_premium_pct": "Market Premium %"},
            )
            st.plotly_chart(premium_fig, use_container_width=True)
        
        # Price comparison chart
        if "current_price" in filtered_recs.columns and "recommended_price" in filtered_recs.columns:
            st.subheader("💰 Current vs Recommended Price")
            comparison_data = filtered_recs[[
                "product_name",
                "current_price",
                "recommended_price"
            ]].head(15).copy()  # Limit to 15 for readability
            
            comparison_fig = go.Figure(
                data=[
                    go.Bar(
                        x=comparison_data["product_name"],
                        y=comparison_data["current_price"],
                        name="Current Price",
                        marker_color="lightblue",
                    ),
                    go.Bar(
                        x=comparison_data["product_name"],
                        y=comparison_data["recommended_price"],
                        name="Recommended Price",
                        marker_color="darkblue",
                    ),
                ]
            )
            comparison_fig.update_layout(
                xaxis_title="Product",
                yaxis_title="Price (Toman)",
                hovermode="x unified",
                height=400,
            )
            st.plotly_chart(comparison_fig, use_container_width=True)
        
        # Margin analysis
        st.subheader("💰 Current vs Expected Margin")
        margin_fig = go.Figure(
            data=[
                go.Bar(
                    x=filtered_recs["product_name"],
                    y=filtered_recs["current_margin"] * 100,
                    name="Current Margin %",
                    marker_color="lightblue",
                ),
                go.Bar(
                    x=filtered_recs["product_name"],
                    y=filtered_recs["expected_margin"] * 100,
                    name="Expected Margin %",
                    marker_color="darkblue",
                ),
            ]
        )
        margin_fig.update_layout(
            xaxis_title="Product",
            yaxis_title="Margin %",
            hovermode="x unified",
            height=400,
        )
        st.plotly_chart(margin_fig, use_container_width=True)
    # Tab 3: USD Shock Simulator
    with tab3:
        st.subheader("💵 USD Exchange Rate Shock Simulator")
        
        st.info(
            f"📊 **Current USD Shock: {usd_shock:+.1f}%**\n\n"
            f"Use the slider on the left to test how price recommendations change with USD rate movements."
        )
        
        # Show products affected
        affected = recs_df[recs_df["triggered_rules"].apply(lambda x: "usd_rate" in str(x))]
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Products Affected by USD", len(affected))
        with col2:
            st.metric("Total Products", len(recs_df))
        with col3:
            pct_affected = (len(affected) / len(recs_df) * 100) if len(recs_df) > 0 else 0
            st.metric("Exposure %", f"{pct_affected:.0f}%")
        
        st.markdown("---")
        
        # Show price changes
        shock_view = filtered_recs[[
            "product_name",
            "current_price",
            "recommended_price",
            "action",
        ]].copy()
        
        shock_view["Current"] = shock_view["current_price"].apply(format_toman)
        shock_view["Recommended"] = shock_view["recommended_price"].apply(format_toman)
        shock_view["Action"] = shock_view["action"].apply(format_action_label)
        
        display_shock = shock_view[[
            "product_name",
            "Current",
            "Recommended",
            "Action",
        ]]
        display_shock.columns = ["Product", "Current Price", "Recommended Price", "Action"]
        
        st.dataframe(display_shock, use_container_width=True, hide_index=True)
    
    # Tab 4: Details
    with tab4:
        st.subheader("🔍 Product Details & Analysis")
        
        if len(filtered_recs) == 0:
            st.warning("No products match the current filters.")
        else:
            selected_product = st.selectbox(
                "Select a product:",
                options=filtered_recs["product_name"],
            )
            
            product_rec = filtered_recs[filtered_recs["product_name"] == selected_product].iloc[0]
            
            # Global Reference Data (Phase 2)
            if is_phase2:
                st.markdown("### 🌍 Global Reference")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    base_usd = product_rec.get("base_usd_price", 0)
                    st.metric(
                        "Base USD Price",
                        f"${base_usd:.2f}" if base_usd else "N/A",
                    )
                
                with col2:
                    usd_rate = product_rec.get("usd_rate", 0)
                    st.metric(
                        "USD Rate",
                        f"{usd_rate:,.0f}" if usd_rate else "N/A",
                    )
                
                with col3:
                    theo_toman = product_rec.get("theoretical_toman_price", 0)
                    st.metric(
                        "Theoretical Toman",
                        format_toman(theo_toman) if theo_toman else "N/A",
                    )
                
                st.markdown("---")
                
                # Market Data (Phase 2)
                st.markdown("### 📊 Market Data")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    iran_prem = product_rec.get("iran_market_premium_pct")
                    st.metric(
                        "Iran Market Premium",
                        format_percent(iran_prem) if iran_prem is not None else "N/A",
                    )
                
                with col2:
                    st.metric(
                        "Seller Count",
                        f"{int(product_rec.get('seller_count', 0))}" if product_rec.get('seller_count') else "N/A",
                    )
                
                with col3:
                    avail_sellers = product_rec.get("available_seller_count", 0)
                    st.metric(
                        "Available Sellers",
                        f"{int(avail_sellers)}" if avail_sellers else "N/A",
                    )
                
                st.markdown("---")
                
                # Market Price Range
                st.markdown("### 💹 Market Price Range")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    market_min = product_rec.get("market_min_price", 0)
                    st.metric(
                        "Market Min",
                        format_toman(market_min) if market_min else "N/A",
                    )
                
                with col2:
                    market_med = product_rec.get("market_median_price", 0)
                    st.metric(
                        "Market Median",
                        format_toman(market_med) if market_med else "N/A",
                    )
                
                with col3:
                    market_max = product_rec.get("market_max_price", 0)
                    st.metric(
                        "Market Max",
                        format_toman(market_max) if market_max else "N/A",
                    )
                
                if product_rec.get("torob_min_price") or product_rec.get("digikala_price"):
                    st.markdown("---")
                    st.markdown("### 🛍️ Platform Prices")
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        torob_min = product_rec.get("torob_min_price", 0)
                        st.metric(
                            "Torob Min",
                            format_toman(torob_min) if torob_min else "N/A",
                        )
                    
                    with col2:
                        torob_med = product_rec.get("torob_median_price", 0)
                        st.metric(
                            "Torob Median",
                            format_toman(torob_med) if torob_med else "N/A",
                        )
                    
                    with col3:
                        digikala = product_rec.get("digikala_price", 0)
                        st.metric(
                            "Digikala",
                            format_toman(digikala) if digikala else "N/A",
                        )
                
                st.markdown("---")
                
                # Our Internal Data (Phase 2)
                st.markdown("### 🏪 Our Retail Data")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    our_curr = product_rec.get("our_current_price", 0)
                    st.metric(
                        "Our Current Price",
                        format_toman(our_curr) if our_curr else "N/A",
                    )
                
                with col2:
                    our_cost = product_rec.get("our_cost_price", 0)
                    st.metric(
                        "Our Cost Price",
                        format_toman(our_cost) if our_cost else "N/A",
                    )
                
                with col3:
                    our_inv = product_rec.get("our_inventory", 0)
                    st.metric(
                        "Our Inventory",
                        f"{int(our_inv)}" if our_inv else "N/A",
                    )
                
                st.markdown("---")
                
                # Our Sales and Targets (Phase 2)
                st.markdown("### 📈 Our Performance")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    sales_7d = product_rec.get("our_sales_7d", 0)
                    st.metric(
                        "Sales (7d)",
                        f"{int(sales_7d)}" if sales_7d else "0",
                    )
                
                with col2:
                    sales_30d = product_rec.get("our_sales_30d", 0)
                    st.metric(
                        "Sales (30d)",
                        f"{int(sales_30d)}" if sales_30d else "0",
                    )
                
                with col3:
                    target_margin = product_rec.get("our_target_margin", 0)
                    st.metric(
                        "Target Margin",
                        format_percent(target_margin) if target_margin else "N/A",
                    )
                
                st.markdown("---")
            
            # Price comparison (MVP or Phase 2)
            st.markdown("### 💰 Price Information")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if is_phase2:
                    our_curr = product_rec.get("our_current_price", 0)
                    st.metric(
                        "Current Price",
                        format_toman(our_curr) if our_curr else "N/A",
                    )
                else:
                    st.metric(
                        "Current Price",
                        format_toman(product_rec.get("current_price", 0)),
                    )
            
            with col2:
                st.metric(
                    "Recommended Price",
                    format_toman(product_rec["recommended_price"]),
                )
            
            with col3:
                current_price = product_rec.get("our_current_price") or product_rec.get("current_price", 0)
                if current_price > 0:
                    price_diff_pct = (
                        (product_rec["recommended_price"] - current_price) / current_price * 100
                    )
                    st.metric(
                        "Price Change",
                        f"{price_diff_pct:+.1f}%",
                    )
            
            st.markdown("---")
            
            # Profitability
            st.markdown("### 📊 Profitability Metrics")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                cost_price = product_rec.get("our_cost_price") or product_rec.get("cost_price", 0)
                st.metric("Cost Price", format_toman(cost_price))
            
            with col2:
                st.metric(
                    "Current Margin",
                    format_margin(product_rec.get("current_margin", 0)),
                )
            
            with col3:
                st.metric(
                    "Expected Margin",
                    format_margin(product_rec.get("expected_margin", 0)),
                )
            
            st.markdown("---")
            
            # Strategy and Pricing (Phase 2)
            if is_phase2 and product_rec.get("strategy_prices"):
                st.markdown("### 🎯 Strategy Price Options")
                
                strategy_prices = product_rec.get("strategy_prices", {})
                selected_strat = product_rec.get("selected_strategy", "N/A")
                
                # Display all strategy prices
                strategy_labels = {
                    "trust_builder": "🤝 Trust Builder",
                    "balanced": "⚖️ Balanced",
                    "profit_protection": "💰 Profit Protection",
                    "market_penetration": "🎯 Market Penetration",
                    "premium_positioning": "👑 Premium Positioning",
                    "clearance_cashflow": "🏷️ Clearance / Cashflow",
                }
                
                cols = st.columns(3)
                col_idx = 0
                for strategy_key, price in strategy_prices.items():
                    with cols[col_idx % 3]:
                        label = strategy_labels.get(strategy_key, strategy_key.replace("_", " ").title())
                        is_selected = (strategy_key == selected_strat)
                        
                        if is_selected:
                            st.success(f"**{label}**\n{format_toman(price)}\n✓ Selected")
                        else:
                            st.info(f"**{label}**\n{format_toman(price)}")
                    col_idx += 1
                
                st.markdown("---")
            
            # Risk and positioning
            st.markdown("### ⚠️ Risk & Market Position")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "Risk Level",
                    format_risk_label(product_rec["risk_level"]),
                )
            
            with col2:
                st.metric(
                    "Recommended Action",
                    format_action_label(product_rec["action"]),
                )
            
            with col3:
                st.metric(
                    "Competitor Position",
                    "See below →",
                )
            
            st.markdown("---")
            
            # Explanation and rules
            st.markdown("### 📝 Recommendation Details")
            
            st.markdown("**Competitor Position:**")
            st.info(product_rec.get("competitor_position", "N/A"))
            
            st.markdown("**Triggered Rules:**")
            if product_rec.get("triggered_rules"):
                for rule in product_rec["triggered_rules"]:
                    st.write(f"• {humanize_label(rule)}")
            else:
                st.write("No specific rules triggered.")
            
            st.markdown("**Full Explanation:**")
            st.markdown(product_rec.get("explanation", "N/A"))
    
    # Tab 5: Market Update Console
    with tab5:
        st.subheader("📝 Market Update Console")
        st.markdown("Manually update market prices and exchange rates.")
        
        # Try to load products master
        try:
            products_df = load_products_master()
            updates_df = load_daily_market_updates()
        except FileNotFoundError:
            st.error("❌ Products master or updates file not found. Please ensure data/raw/ files exist.")
            st.stop()
        
        # Section 1: Today's Update Status
        st.markdown("### 📊 Today's Update Status")
        
        from datetime import datetime
        today = datetime.now().strftime('%Y-%m-%d')
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            active_count = len(products_df[products_df.get('active', True) == True])
            st.metric("📦 Active Products", active_count)
        
        with col2:
            if not updates_df.empty:
                updates_df['date'] = pd.to_datetime(updates_df['observed_at']).dt.strftime('%Y-%m-%d')
                updated_today = len(updates_df[updates_df['date'] == today]['product_id'].unique())
            else:
                updated_today = 0
            st.metric("✅ Updated Today", updated_today)
        
        with col3:
            missing_count = active_count - updated_today
            st.metric("⏳ Missing Today", missing_count)
        
        with col4:
            missing_products = get_products_missing_update_today(products_df, updates_df, today)
            high_priority = len(missing_products[missing_products.get('priority', 'medium') == 'high'])
            st.metric("🔴 High-Priority Missing", high_priority)
        
        st.markdown("---")
        
        # Section 2: Quick Product Update
        st.markdown("### 💡 Quick Product Update")
        
        col1, col2 = st.columns(2)
        
        with col1:
            product_options = {f"{row['product_id']} - {row['product_name']}": row['product_id'] 
                             for _, row in products_df.iterrows()}
            selected_product = st.selectbox(
                "Select Product",
                options=list(product_options.keys()),
                key="product_select"
            )
            selected_product_id = product_options[selected_product]
        
        # Show product details
        product_row = products_df[products_df['product_id'] == selected_product_id].iloc[0]
        
        st.markdown(f"**Product:** {product_row['brand']} {product_row['model']}")
        priority_label = {
            'high': '🔥 High Priority',
            'medium': '⚡ Medium Priority',
            'low': 'ℹ️ Low Priority',
        }.get(str(product_row.get('priority', '')).lower(), str(product_row.get('priority', 'Unknown')).title())
        st.markdown(f"**Priority:** {priority_label}")
        
        # Show source links
        sources_cols = st.columns(3)
        with sources_cols[0]:
            if is_valid_source_link(product_row.get('torob_url')):
                st.markdown(f"[🔗 Torob]({product_row['torob_url']})")
            else:
                st.markdown("_Link not added yet_")
        with sources_cols[1]:
            if is_valid_source_link(product_row.get('digikala_url')):
                st.markdown(f"[🔗 Digikala]({product_row['digikala_url']})")
            else:
                st.markdown("_Link not added yet_")
        with sources_cols[2]:
            if is_valid_source_link(product_row.get('global_reference_url')):
                st.markdown(f"[🔗 Global Ref]({product_row['global_reference_url']})")
            else:
                st.markdown("_Link not added yet_")
        
        st.markdown("---")
        
        # Price input fields
        st.markdown("**Enter Market Prices (at least one required):**")
        st.markdown("_Compact price preview is shown below each input to help readability._")
        
        col1, col2 = st.columns(2)
        with col1:
            torob_min = st.text_input(
                "Torob Min Price (تومان)", value="", placeholder="e.g. 37,200,000",
                key="torob_min_price", on_change=normalize_price_input_state, args=("torob_min_price",),
            )
            show_price_input_feedback(torob_min)
            torob_median = st.text_input(
                "Torob Median Price (تومان)", value="", placeholder="e.g. 37,200,000",
                key="torob_median_price", on_change=normalize_price_input_state, args=("torob_median_price",),
            )
            show_price_input_feedback(torob_median)
        
        with col2:
            digikala_price = st.text_input(
                "Digikala Price (تومان)", value="", placeholder="e.g. 38,000,000",
                key="digikala_price", on_change=normalize_price_input_state, args=("digikala_price",),
            )
            show_price_input_feedback(digikala_price)
            market_max = st.text_input(
                "Market Max Price (تومان)", value="", placeholder="e.g. 40,000,000",
                key="market_max_price", on_change=normalize_price_input_state, args=("market_max_price",),
            )
            show_price_input_feedback(market_max)
        
        availability_options = {
            'Available': 'available',
            'Low Stock': 'low_stock',
            'Unavailable': 'unavailable',
        }
        availability_label = st.selectbox(
            "Availability Status",
            options=list(availability_options.keys()),
            key="availability"
        )
        availability = availability_options[availability_label]
        
        notes = st.text_area("Notes", placeholder="e.g., price checked at 14:30", key="market_notes")
        
        # Save button
        if st.button("💾 Save Market Update", key="save_market"):
            parsed_torob_min = parse_price_input(torob_min)
            parsed_torob_median = parse_price_input(torob_median)
            parsed_digikala = parse_price_input(digikala_price)
            parsed_market_max = parse_price_input(market_max)

            invalid_fields = []
            if torob_min and parsed_torob_min is None:
                invalid_fields.append("Torob Min Price")
            if torob_median and parsed_torob_median is None:
                invalid_fields.append("Torob Median Price")
            if digikala_price and parsed_digikala is None:
                invalid_fields.append("Digikala Price")
            if market_max and parsed_market_max is None:
                invalid_fields.append("Market Max Price")

            if invalid_fields:
                st.error(
                    f"❌ Invalid price values in: {', '.join(invalid_fields)}."
                    " Please enter numbers using digits, commas, or spaces."
                )
            else:
                update_dict = {
                    'product_id': selected_product_id,
                    'observed_at': datetime.now().isoformat(),
                    'torob_min_price': parsed_torob_min,
                    'torob_median_price': parsed_torob_median,
                    'digikala_price': parsed_digikala,
                    'market_max_price': parsed_market_max,
                    'availability_note': availability,
                    'notes': notes,
                }

                try:
                    append_daily_market_update('data/raw/daily_market_updates.csv', update_dict)
                    st.success(f"✅ Market update saved for {product_row['product_name']}!")
                    st.rerun()
                except ValueError as e:
                    st.error(f"❌ Validation error: {str(e)}")
        
        st.markdown("---")
        
        # Section 3: FX Rate Update
        st.markdown("### 💱 FX Rate Update")
        
        col1, col2 = st.columns(2)
        with col1:
            fx_source = st.selectbox(
                "FX Source",
                options=["manual", "nobitex_usdt_proxy", "navasan", "tgju", "bonbast"],
                help="Future versions will support API integration",
                key="fx_source"
            )
        
        with col2:
            fx_symbol = st.text_input("Symbol", value="USDIRT", key="fx_symbol")
        
        fx_rate = st.text_input(
            "Rate (Toman per Unit)", value="45,000", placeholder="e.g. 45,000",
            key="fx_rate_toman", on_change=normalize_price_input_state, args=("fx_rate_toman",),
        )
        show_price_input_feedback(fx_rate)
        fx_notes = st.text_area("Notes (e.g., source URL, timestamp)", placeholder="e.g., from Nobitex at 14:30", key="fx_notes")
        
        if st.button("💾 Save FX Rate", key="save_fx"):
            parsed_fx_rate = parse_price_input(fx_rate)
            if parsed_fx_rate is None or parsed_fx_rate <= 0:
                st.error("❌ Please enter a valid FX rate in Toman using digits, commas, or spaces.")
            else:
                fx_dict = {
                    'source': fx_source,
                    'symbol': fx_symbol,
                    'rate_toman': parsed_fx_rate,
                    'observed_at': datetime.now().isoformat(),
                    'notes': fx_notes,
                }
            
            try:
                append_fx_rate_snapshot('data/raw/fx_rate_snapshots.csv', fx_dict)
                st.success(f"✅ FX rate saved: {fx_symbol} = {fx_rate:,.0f} Toman")
                st.rerun()
            except ValueError as e:
                st.error(f"❌ Validation error: {str(e)}")
        
        st.markdown("---")
        
        # Section 4: Build Dataset
        st.markdown("### 🔨 Build Processing Dataset")
        st.markdown(
            "After updating market prices and FX rates, rebuild the processed dataset "
            "so the dashboard can use the new data."
        )
        
        col1, col2 = st.columns(2)
        with col1:
            st.code("python scripts/build_pricing_dataset.py", language="bash")
        
        with col2:
            if st.button("🚀 Run Build Pipeline", key="run_build"):
                try:
                    st.info("Building processed dataset...")
                    
                    # Load raw data
                    market = load_market_observations('data/raw/market_observations_template.csv')
                    retailer = load_retailer_internal_data('data/raw/retailer_internal_demo_template.csv')
                    usd = load_global_usd_reference('data/raw/global_usd_reference_template.csv')
                    
                    # Build dashboard dataset
                    result = build_dashboard_pricing_dataset(market, retailer, usd)
                    
                    # Save
                    from src.data.build_pricing_dataset import save_dashboard_pricing_dataset
                    save_dashboard_pricing_dataset(result)
                    
                    st.success(f"✅ Build successful! Generated {len(result)} products.")
                    st.markdown("**Next step:** Go back to Data Source selector and choose 'Processed Real Market Dataset'")
                    
                except Exception as e:
                    st.error(f"❌ Build failed: {str(e)}")


if __name__ == "__main__":
    main()
