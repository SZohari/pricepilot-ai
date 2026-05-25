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
)
from src.utils.validation import validate_csv_columns, validate_csv_data, get_column_info


def load_data_with_mode():
    """Load data from sample or uploaded CSV."""
    data_mode = st.sidebar.radio(
        "📂 Data Source",
        options=["Sample Data (Generated)", "Upload CSV"],
        help="Choose between generated sample data or upload your own CSV",
    )
    
    if data_mode == "Upload CSV":
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
    def get_recommendations(shock, data_hash):
        recommendations = []
        for _, row in df.iterrows():
            rec = recommend_price(row.to_dict(), usd_shock=shock)
            recommendations.append(rec)
        return pd.DataFrame(recommendations)
    
    recs_df = get_recommendations(usd_shock, hash(df.values.tobytes()))
    
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
    
    selected_actions = st.sidebar.multiselect(
        "Action",
        options=["increase_price", "decrease_price", "hold_price", "urgent_review"],
        default=["increase_price", "decrease_price", "hold_price", "urgent_review"],
    )
    
    selected_risk_levels = st.sidebar.multiselect(
        "Risk Level",
        options=["low", "medium", "high", "critical"],
        default=["low", "medium", "high", "critical"],
    )
    
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
    tab1, tab2, tab3, tab4 = st.tabs(
        ["📋 Recommendations", "📊 Analytics", "⚡ USD Shock", "🔍 Details"]
    )
    
    # Tab 1: Recommendations Table
    with tab1:
        st.subheader("Price Recommendations")
        st.markdown(f"Showing {len(filtered_recs)} of {len(recs_df)} products")
        
        # Prepare display columns, robust to missing metadata
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
                if col in ["brand"]:
                    filtered_recs[col] = "Unknown"
                elif col in ["current_price", "recommended_price", "current_margin", "expected_margin"]:
                    filtered_recs[col] = 0.0
                else:
                    filtered_recs[col] = "Unknown"
        
        display_df = filtered_recs[display_fields].copy()
        
        # Format prices using toman formatter
        display_df["Current Price"] = display_df["current_price"].apply(lambda x: format_toman(x))
        display_df["Recommended Price"] = display_df["recommended_price"].apply(lambda x: format_toman(x))
        display_df["Action"] = display_df["action"].apply(format_action_label)
        display_df["Risk"] = display_df["risk_level"].apply(format_risk_label)
        display_df["Current Margin"] = display_df["current_margin"].apply(format_margin)
        display_df["Expected Margin"] = display_df["expected_margin"].apply(format_margin)
        
        # Select columns for display
        display_cols = display_df[[
            "product_id",
            "product_name",
            "brand",
            "Current Price",
            "Recommended Price",
            "Action",
            "Risk",
            "Current Margin",
            "Expected Margin",
        ]]
        
        st.dataframe(display_cols, use_container_width=True, hide_index=True)
    
    # Tab 2: Analytics
    with tab2:
        col1, col2 = st.columns(2)
        
        with col1:
            # Action distribution
            action_counts = filtered_recs["action"].value_counts()
            fig_actions = px.pie(
                x=action_counts.values,
                labels=action_counts.index,
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
                x=risk_counts.values,
                labels=risk_counts.index,
                title="⚠️ Risk Level Distribution",
                color_discrete_map={
                    "low": "#00CC00",
                    "medium": "#FFAA00",
                    "high": "#FF6600",
                    "critical": "#CC0000",
                },
            )
            st.plotly_chart(fig_risk, use_container_width=True)
        
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
            
            # Price comparison
            st.markdown("### 💰 Price Information")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "Current Price",
                    format_toman(product_rec["current_price"]),
                )
            
            with col2:
                st.metric(
                    "Recommended Price",
                    format_toman(product_rec["recommended_price"]),
                )
            
            with col3:
                price_diff_pct = (
                    (product_rec["recommended_price"] - product_rec["current_price"]) / 
                    product_rec["current_price"] * 100
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
                st.metric("Cost Price", format_toman(product_rec.get("cost_price", 0)))
            
            with col2:
                st.metric(
                    "Current Margin",
                    format_margin(product_rec["current_margin"]),
                )
            
            with col3:
                st.metric(
                    "Expected Margin",
                    format_margin(product_rec["expected_margin"]),
                )
            
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
            st.info(product_rec["competitor_position"])
            
            st.markdown("**Triggered Rules:**")
            if product_rec["triggered_rules"]:
                for rule in product_rec["triggered_rules"]:
                    st.write(f"• {rule.replace('_', ' ').title()}")
            else:
                st.write("No specific rules triggered.")
            
            st.markdown("**Full Explanation:**")
            st.markdown(product_rec["explanation"])


if __name__ == "__main__":
    main()
