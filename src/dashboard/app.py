"""Streamlit dashboard for guided pricing operations."""

from datetime import datetime
from pathlib import Path
import sys

import pandas as pd
import plotly.express as px
import streamlit as st

# Add project root to path for direct Streamlit execution.
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.data.sample_data_generator import load_sample_data
from scripts.load_demo_scenario import (
    DEFAULT_SCENARIO_DIR,
    build_from_raw_dir,
    copy_demo_scenario,
)
from src.data.build_pricing_dataset import (
    build_dashboard_pricing_dataset,
    load_global_usd_reference,
    load_market_observations,
    load_processed_pricing_data,
    load_retailer_internal_data,
    save_dashboard_pricing_dataset,
)
from src.data.manual_entry import (
    append_daily_market_update,
    append_fx_rate_snapshot,
    append_new_product,
    generate_product_id,
    get_known_brands,
    get_latest_update_for_product,
    get_products_missing_update_today,
    load_daily_market_updates,
    load_fx_rate_snapshots,
    load_products_master,
    normalize_brand,
    product_id_exists,
    upsert_retailer_internal_data,
    validate_new_product_payload,
    validate_retailer_internal_payload,
)
from src.pricing.recommendation import recommend_price
from src.utils.formatting import (
    format_action_badge,
    format_action_label,
    format_margin,
    format_optional_percent,
    format_optional_toman,
    format_percent,
    format_price_change,
    format_price_change_percent,
    format_price_input_value,
    format_price_preview,
    format_risk_badge,
    format_risk_label,
    format_toman,
    humanize_label,
    parse_price_input,
    safe_display,
)
from src.utils.validation import get_column_info, validate_csv_columns, validate_csv_data


PROCESSED_DATASET_PATH = Path("data/processed/dashboard_pricing_data.csv")
SCENARIO_DIR = DEFAULT_SCENARIO_DIR
RAW_MARKET_PATH = "data/raw/market_observations_template.csv"
RAW_PRODUCTS_PATH = "data/raw/products_master.csv"
RAW_RETAILER_PATH = "data/raw/retailer_internal_demo_template.csv"
RAW_USD_PATH = "data/raw/global_usd_reference_template.csv"
RAW_UPDATES_PATH = "data/raw/daily_market_updates.csv"
RAW_FX_PATH = "data/raw/fx_rate_snapshots.csv"

STRATEGY_LABELS = {
    "trust_builder": "Trust Builder",
    "balanced": "Balanced",
    "profit_protection": "Profit Protection",
    "market_penetration": "Market Penetration",
    "premium_positioning": "Premium Positioning",
    "clearance_cashflow": "Clearance / Cashflow",
}
STRATEGY_KEYS = list(STRATEGY_LABELS.keys())
PUBLIC_DATA_SOURCE_OPTIONS = ["Demo Scenario (20 Products)", "Upload CSV"]
DEFAULT_PUBLIC_DATA_SOURCE = PUBLIC_DATA_SOURCE_OPTIONS[0]


def processed_dataset_is_ready(processed_path: Path = PROCESSED_DATASET_PATH) -> bool:
    """Return True when the processed dashboard dataset exists and has rows."""
    processed_path = Path(processed_path)
    if not processed_path.exists():
        return False
    try:
        df = load_processed_pricing_data(str(processed_path))
    except (FileNotFoundError, ValueError, pd.errors.EmptyDataError):
        return False
    return not df.empty and "product_id" in df.columns


def prepare_demo_dataset(
    processed_path: Path = PROCESSED_DATASET_PATH,
    scenario_dir: Path = SCENARIO_DIR,
    raw_dir: Path = Path("data/raw"),
) -> pd.DataFrame:
    """Ensure the packaged 20-product demo has a processed dataset."""
    processed_path = Path(processed_path)
    if processed_dataset_is_ready(processed_path):
        return load_processed_pricing_data(str(processed_path))

    copy_demo_scenario(Path(scenario_dir), Path(raw_dir))
    build_from_raw_dir(Path(raw_dir), processed_path)
    return load_processed_pricing_data(str(processed_path))


def is_valid_source_link(link: str) -> bool:
    """Return True when a source link is present and usable."""
    if not link:
        return False
    normalized = str(link).strip()
    return normalized != "" and normalized.lower() not in {"#", "n/a", "na", "none"}


def normalize_price_input_state(key: str) -> None:
    """Normalize a valid text price field to grouped English digits."""
    raw_value = st.session_state.get(key, "")
    parsed_value = parse_price_input(raw_value)
    if parsed_value is not None:
        st.session_state[key] = format_price_input_value(parsed_value)


def show_price_input_feedback(value: str) -> None:
    """Show immediate validation and readability feedback for a toman input."""
    parsed_value = parse_price_input(value)
    if str(value or "").strip() and parsed_value is None:
        st.warning("Please enter a valid number.")
        return

    preview = format_price_preview(parsed_value)
    if preview:
        st.caption(preview)
    if parsed_value is not None and parsed_value >= 100_000_000:
        st.warning("This is a very large number. Make sure the value is in toman, not rial.")


def numeric_value(value: object, fallback: float = 0.0) -> float:
    """Convert display data into a finite number for metrics and charts."""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return fallback
    return numeric if pd.notna(numeric) else fallback


def product_options(products_df: pd.DataFrame) -> dict[str, str]:
    """Create display labels mapped to product IDs."""
    if products_df.empty:
        return {}
    return {
        f"{row['product_id']} - {row['product_name']}": row["product_id"]
        for _, row in products_df.iterrows()
    }


def render_source_link(label: str, url: object) -> None:
    """Render a product source link or a clear empty state."""
    if is_valid_source_link(url):
        st.markdown(f"[{label}]({url})")
    else:
        st.caption("Link not added yet.")


def load_data_with_mode() -> tuple[pd.DataFrame | None, str]:
    """Load data from sample, processed real data, or uploaded CSV."""
    data_mode = st.sidebar.radio(
        "Data source",
        options=PUBLIC_DATA_SOURCE_OPTIONS,
        help="Choose the dataset used for recommendations.",
    )
    with st.sidebar.expander("Advanced / Developer"):
        use_sample_data = st.checkbox("Use Sample Data (Generated)", value=False)

    if use_sample_data:
        st.sidebar.caption("Generated developer sample data.")
        return load_sample_data(), "Sample Data (Generated)"

    if data_mode == "Demo Scenario (20 Products)":
        st.sidebar.caption(
            "This public demo uses a packaged 20-product Iranian smartwatch scenario. "
            "It is realistic demo data, not live scraped market data."
        )
        try:
            df = prepare_demo_dataset()
            st.sidebar.success(f"Loaded {len(df)} products.")
            return df, data_mode
        except ValueError as exc:
            st.sidebar.error(f"Dataset validation failed: {exc}")
            return None, data_mode
        except Exception:
            st.sidebar.error("Demo dataset could not be prepared. Please check scenario files.")
            return None, data_mode

    if data_mode == "Upload CSV":
        uploaded_file = st.sidebar.file_uploader(
            "Upload pricing CSV",
            type=["csv"],
            help="CSV must contain the required pricing columns.",
        )
        if uploaded_file is None:
            st.sidebar.info("Waiting for CSV upload.")
            return None, data_mode
        try:
            df = pd.read_csv(uploaded_file)
        except Exception as exc:
            st.sidebar.error(f"Could not read CSV: {exc}")
            return None, data_mode

        col_valid, missing_cols = validate_csv_columns(df)
        if not col_valid:
            st.sidebar.error(f"Missing columns: {', '.join(missing_cols)}")
            st.info("Required CSV columns:\n" + get_column_info())
            return None, data_mode

        data_valid, issues = validate_csv_data(df)
        if not data_valid:
            st.sidebar.error("Please fix the CSV data issues.")
            for issue in issues:
                st.warning(issue)
            return None, data_mode

        st.sidebar.success(f"Loaded {len(df)} products.")
        return df, data_mode

    return None, data_mode


def render_sidebar(df: pd.DataFrame | None) -> tuple[pd.DataFrame | None, str | None, int | None, float, str]:
    """Render global controls and return data, strategy, FX rate, shock, and data mode."""
    st.sidebar.title("Controls")
    df, data_mode = load_data_with_mode()

    selected_strategy = None
    manual_usd_rate = None
    usd_shock = 0.0
    if df is not None and not df.empty:
        st.sidebar.divider()
        st.sidebar.subheader("Pricing strategy")
        selected_strategy_label = st.sidebar.selectbox(
            "Apply strategy",
            options=list(STRATEGY_LABELS.values()),
            index=1,
            help="Applies this strategy to recommendation calculations for the current view.",
        )
        selected_strategy = {
            label: key for key, label in STRATEGY_LABELS.items()
        }[selected_strategy_label]

        st.sidebar.caption("Use the same strategy across the dashboard for a clean comparison.")
        st.sidebar.divider()
        st.sidebar.subheader("Exchange rate")
        st.sidebar.caption("Use today’s exchange rate to test how replacement cost affects pricing.")
        manual_usd_rate_text = st.sidebar.text_input(
            "Manual USD Rate",
            value="170,000",
            help="Enter the USD/Toman rate. Examples: 170000, 170,000, ۱۷۰,۰۰۰.",
            key="manual_usd_rate",
            on_change=normalize_price_input_state,
            args=("manual_usd_rate",),
        )
        manual_usd_rate = parse_price_input(manual_usd_rate_text)
        if manual_usd_rate is None or manual_usd_rate <= 0:
            st.sidebar.warning("Enter a valid USD rate in toman.")
            manual_usd_rate = None
        else:
            st.sidebar.caption(format_price_preview(manual_usd_rate))

        with st.sidebar.expander("Advanced: FX simulation"):
            usd_shock = st.slider(
                "USD percentage shock",
                min_value=-10.0,
                max_value=30.0,
                value=0.0,
                step=0.5,
                help="Optional stress test on top of the manual USD rate.",
            )

    st.sidebar.divider()
    st.sidebar.info("Workflow: 1. Update data -> 2. Build dataset -> 3. Review recommendations")
    return df, selected_strategy, manual_usd_rate, usd_shock, data_mode


def apply_manual_usd_rate(row_dict: dict, manual_usd_rate: int | None) -> dict:
    """Apply a manual USD/Toman rate to display-time recommendation inputs."""
    if manual_usd_rate is None:
        return row_dict

    adjusted = dict(row_dict)
    adjusted["usd_rate"] = manual_usd_rate
    base_usd_price = numeric_value(adjusted.get("base_usd_price"), 0)
    if base_usd_price > 0:
        adjusted["theoretical_toman_price"] = base_usd_price * manual_usd_rate
    return adjusted


def build_recommendations(
    df: pd.DataFrame,
    usd_shock: float,
    selected_strategy: str | None,
    manual_usd_rate: int | None = None,
) -> pd.DataFrame:
    """Generate recommendations and preserve useful source fields for display."""
    recommendations = []
    for _, row in df.iterrows():
        row_dict = apply_manual_usd_rate(row.to_dict(), manual_usd_rate)
        strategy_override = selected_strategy if "our_current_price" in row_dict else None
        rec = recommend_price(row_dict, usd_shock=usd_shock, strategy=strategy_override)
        for field in [
            "market_min_price",
            "market_median_price",
            "market_max_price",
            "market_avg_price",
            "torob_min_price",
            "torob_median_price",
            "digikala_price",
            "seller_count",
            "available_seller_count",
            "base_usd_price",
            "usd_rate",
            "theoretical_toman_price",
            "our_current_price",
            "our_cost_price",
            "our_inventory",
            "our_sales_7d",
            "our_sales_30d",
            "our_target_margin",
            "our_strategy",
        ]:
            if field in row_dict and field not in rec:
                rec[field] = row_dict.get(field)
        rec["market_median_price"] = row_dict.get(
            "market_median_price",
            row_dict.get("competitor_median_price", rec.get("market_median_price")),
        )
        recommendations.append(rec)
    return pd.DataFrame(recommendations)


def render_kpi_cards(recs_df: pd.DataFrame) -> None:
    """Render top-level pricing operation KPIs."""
    increase_count = int((recs_df["action"] == "increase_price").sum())
    decrease_count = int((recs_df["action"] == "decrease_price").sum())
    risk_count = int(recs_df["risk_level"].isin(["high", "critical"]).sum())
    avg_premium = recs_df["iran_market_premium_pct"].dropna().mean() if "iran_market_premium_pct" in recs_df else None

    cols = st.columns(5)
    cols[0].metric("Total products", len(recs_df))
    cols[1].metric("Need increase", increase_count)
    cols[2].metric("Need decrease", decrease_count)
    cols[3].metric("High/Critical risk", risk_count)
    cols[4].metric(
        "Avg Iran premium",
        format_percent(avg_premium) if avg_premium is not None and pd.notna(avg_premium) else "—",
    )


def recommendation_table(recs_df: pd.DataFrame) -> pd.DataFrame:
    """Return a clean decision-focused recommendation table."""
    display_rows = []
    for _, rec in recs_df.iterrows():
        current_price = rec.get("current_price")
        recommended_price = rec.get("recommended_price")
        display_rows.append(
            {
                "Product": safe_display(rec.get("product_name")),
                "Brand": safe_display(rec.get("brand")),
                "Our Current Price": format_optional_toman(current_price),
                "Recommended Price": format_optional_toman(recommended_price),
                "Price Change": format_price_change(current_price, recommended_price),
                "Price Change %": format_price_change_percent(current_price, recommended_price),
                "Strategy": safe_display(humanize_label(rec.get("selected_strategy"))),
                "Action": format_action_badge(rec.get("action")),
                "Risk": format_risk_badge(rec.get("risk_level")),
                "Market Median": format_optional_toman(rec.get("market_median_price")),
                "Iran Premium %": format_optional_percent(rec.get("iran_market_premium_pct")),
            }
        )
    return pd.DataFrame(display_rows).fillna("—")


def render_overview_tab(recs_df: pd.DataFrame, data_mode: str) -> None:
    """Render the guided overview and main recommendations table."""
    st.info(
        "PricePilot AI helps retailers adjust prices using market prices, store costs, "
        "inventory, FX rate, and strategy."
    )
    st.caption(f"Current data source: {data_mode}")
    render_kpi_cards(recs_df)

    st.subheader("Recommended pricing decisions")
    st.caption("Decision-focused view. Technical input fields are kept out of this table.")
    if recs_df.empty:
        st.warning("No recommendations available for the selected data source.")
        return
    st.dataframe(recommendation_table(recs_df), width="stretch", hide_index=True)


def render_strategy_prices(strategy_prices: object, selected_strategy: object) -> None:
    """Render all available strategy price options."""
    if not isinstance(strategy_prices, dict) or not strategy_prices:
        st.info("Strategy price options are not available for this product.")
        return

    cols = st.columns(3)
    for idx, strategy_key in enumerate(STRATEGY_KEYS):
        if strategy_key not in strategy_prices:
            continue
        label = STRATEGY_LABELS[strategy_key]
        price = strategy_prices[strategy_key]
        with cols[idx % 3]:
            if strategy_key == selected_strategy:
                st.success(f"{label}\n\n{format_optional_toman(price)}\n\nSelected")
            else:
                st.info(f"{label}\n\n{format_optional_toman(price)}")


def render_decision_center_tab(recs_df: pd.DataFrame) -> None:
    """Render a readable product-level decision view."""
    if recs_df.empty:
        st.warning("No products are available for review.")
        return

    product_names = recs_df["product_name"].fillna("Unnamed product").tolist()
    selected_product = st.selectbox("Select product", options=product_names)
    product_rec = recs_df[recs_df["product_name"] == selected_product].iloc[0]

    st.subheader(safe_display(product_rec.get("product_name")))
    st.caption(
        f"{safe_display(product_rec.get('brand'))} | "
        f"Strategy: {humanize_label(product_rec.get('selected_strategy') or product_rec.get('our_strategy')) or 'Balanced'} | "
        f"Action: {humanize_label(product_rec.get('action'))}"
    )

    cols = st.columns(4)
    cols[0].metric("Current price", format_optional_toman(product_rec.get("current_price")))
    cols[1].metric("Recommended price", format_optional_toman(product_rec.get("recommended_price")))
    cols[2].metric(
        "Price change",
        format_price_change(product_rec.get("current_price"), product_rec.get("recommended_price")),
        format_price_change_percent(product_rec.get("current_price"), product_rec.get("recommended_price")),
    )
    cols[3].metric("Risk", format_risk_label(product_rec.get("risk_level")))

    st.markdown("#### Market position")
    market_cols = st.columns(4)
    market_cols[0].metric("Market min", format_optional_toman(product_rec.get("market_min_price")))
    market_cols[1].metric("Market median", format_optional_toman(product_rec.get("market_median_price")))
    market_cols[2].metric("Market max", format_optional_toman(product_rec.get("market_max_price")))
    market_cols[3].metric("Our current", format_optional_toman(product_rec.get("current_price")))

    st.markdown("#### Strategy explanation")
    explanation = product_rec.get("explanation")
    st.info(explanation if explanation else "No explanation is available for this recommendation.")

    st.markdown("#### Triggered rules")
    triggered_rules = product_rec.get("triggered_rules")
    if isinstance(triggered_rules, list) and triggered_rules:
        for rule in triggered_rules:
            st.write(f"- {humanize_label(rule)}")
    else:
        st.caption("No additional rule triggers for this product.")

    st.markdown("#### Strategy price options")
    render_strategy_prices(product_rec.get("strategy_prices"), product_rec.get("selected_strategy"))

    with st.expander("Additional context"):
        context_cols = st.columns(3)
        context_cols[0].metric("Current margin", format_margin(product_rec.get("current_margin", 0)))
        context_cols[1].metric("Expected margin", format_margin(product_rec.get("expected_margin", 0)))
        context_cols[2].metric("Inventory", int(numeric_value(product_rec.get("our_inventory"), 0)))
        st.caption(f"Market position: {safe_display(product_rec.get('competitor_position'))}")


def render_market_update_section(products_df: pd.DataFrame, updates_df: pd.DataFrame) -> None:
    """Render market price update workflow."""
    options = product_options(products_df)
    if not options:
        st.warning("No products found in the product master.")
        return

    col1, col2 = st.columns([1, 1])
    with col1:
        selected_product_label = st.selectbox("Product", options=list(options.keys()), key="product_select")
        selected_product_id = options[selected_product_label]
    product_row = products_df[products_df["product_id"] == selected_product_id].iloc[0]

    latest_update = get_latest_update_for_product(updates_df, selected_product_id)
    with col2:
        if latest_update:
            observed_at = safe_display(latest_update.get("observed_at"))
            st.success(f"Latest market update: {observed_at}")
        else:
            st.info("No recent market update saved for this product.")

    st.caption(f"{safe_display(product_row.get('brand'))} {safe_display(product_row.get('model'))}")
    source_cols = st.columns(3)
    with source_cols[0]:
        render_source_link("Torob source", product_row.get("torob_url"))
    with source_cols[1]:
        render_source_link("Digikala source", product_row.get("digikala_url"))
    with source_cols[2]:
        render_source_link("Global reference", product_row.get("global_reference_url"))

    price_cols = st.columns(2)
    with price_cols[0]:
        torob_min = st.text_input(
            "Torob min price (toman)",
            placeholder="e.g. 37,200,000",
            key="torob_min_price",
            on_change=normalize_price_input_state,
            args=("torob_min_price",),
        )
        show_price_input_feedback(torob_min)
        torob_median = st.text_input(
            "Torob median price (toman)",
            placeholder="e.g. 37,200,000",
            key="torob_median_price",
            on_change=normalize_price_input_state,
            args=("torob_median_price",),
        )
        show_price_input_feedback(torob_median)
    with price_cols[1]:
        digikala_price = st.text_input(
            "Digikala price (toman)",
            placeholder="e.g. 38,000,000",
            key="digikala_price",
            on_change=normalize_price_input_state,
            args=("digikala_price",),
        )
        show_price_input_feedback(digikala_price)
        market_max = st.text_input(
            "Market max price (toman)",
            placeholder="e.g. 40,000,000",
            key="market_max_price",
            on_change=normalize_price_input_state,
            args=("market_max_price",),
        )
        show_price_input_feedback(market_max)

    availability_options = {
        "Available": "available",
        "Low Stock": "low_stock",
        "Unavailable": "unavailable",
    }
    availability_label = st.selectbox("Availability", options=list(availability_options.keys()), key="availability")
    notes = st.text_area("Notes", placeholder="Optional: source, timestamp, or observation context", key="market_notes")

    if st.button("Save market update", key="save_market"):
        raw_prices = {
            "Torob min price": torob_min,
            "Torob median price": torob_median,
            "Digikala price": digikala_price,
            "Market max price": market_max,
        }
        parsed_prices = {label: parse_price_input(value) for label, value in raw_prices.items()}
        invalid_fields = [
            label for label, value in parsed_prices.items()
            if str(raw_prices[label] or "").strip() and value is None
        ]
        if invalid_fields:
            st.error(f"Invalid price values in: {', '.join(invalid_fields)}.")
            return
        if not any(value is not None and value > 0 for value in parsed_prices.values()):
            st.error("Enter at least one market price before saving.")
            return

        update_dict = {
            "product_id": selected_product_id,
            "observed_at": datetime.now().isoformat(),
            "torob_min_price": parsed_prices["Torob min price"],
            "torob_median_price": parsed_prices["Torob median price"],
            "digikala_price": parsed_prices["Digikala price"],
            "market_max_price": parsed_prices["Market max price"],
            "availability_note": availability_options[availability_label],
            "notes": notes,
        }
        try:
            append_daily_market_update(RAW_UPDATES_PATH, update_dict)
            st.success(f"Market update saved for {product_row['product_name']}.")
            st.rerun()
        except ValueError as exc:
            st.error(f"Validation error: {exc}")


def render_store_update_section(products_df: pd.DataFrame) -> None:
    """Render our store data update workflow."""
    options = product_options(products_df)
    if not options:
        st.warning("No products found in the product master.")
        return

    try:
        store_df = load_retailer_internal_data(RAW_RETAILER_PATH)
    except (FileNotFoundError, ValueError) as exc:
        st.error(str(exc))
        store_df = pd.DataFrame()

    selected_label = st.selectbox("Product", options=list(options.keys()), key="store_product_select")
    product_id = options[selected_label]
    stored_rows = store_df[store_df["product_id"] == product_id] if not store_df.empty else pd.DataFrame()
    stored = stored_rows.iloc[-1] if not stored_rows.empty else None

    if stored is not None:
        st.caption(
            f"Current {format_toman(stored['our_current_price'])} | "
            f"Cost {format_toman(stored['our_cost_price'])} | "
            f"Inventory {int(stored['our_inventory'])} | "
            f"Sales 7d/30d {int(stored['our_sales_7d'])}/{int(stored['our_sales_30d'])} | "
            f"Margin {float(stored['our_target_margin']):.0%} | "
            f"Strategy {humanize_label(stored['our_strategy'])}"
        )

    current_key = f"store_current_price_{product_id}"
    cost_key = f"store_cost_price_{product_id}"
    col1, col2 = st.columns(2)
    with col1:
        store_current_price = st.text_input(
            "Current price (toman)",
            value=format_price_input_value(stored["our_current_price"]) if stored is not None else "",
            key=current_key,
            on_change=normalize_price_input_state,
            args=(current_key,),
        )
        show_price_input_feedback(store_current_price)
        store_inventory = st.number_input(
            "Inventory",
            min_value=0,
            value=int(stored["our_inventory"]) if stored is not None else 0,
            step=1,
            key=f"store_inventory_{product_id}",
        )
        store_sales_7d = st.number_input(
            "Sales (7d)",
            min_value=0,
            value=int(stored["our_sales_7d"]) if stored is not None else 0,
            step=1,
            key=f"store_sales_7d_{product_id}",
        )
    with col2:
        store_cost_price = st.text_input(
            "Cost price (toman)",
            value=format_price_input_value(stored["our_cost_price"]) if stored is not None else "",
            key=cost_key,
            on_change=normalize_price_input_state,
            args=(cost_key,),
        )
        show_price_input_feedback(store_cost_price)
        store_sales_30d = st.number_input(
            "Sales (30d)",
            min_value=0,
            value=int(stored["our_sales_30d"]) if stored is not None else 0,
            step=1,
            key=f"store_sales_30d_{product_id}",
        )
        store_target_margin = st.number_input(
            "Target margin",
            min_value=0.0,
            max_value=1.0,
            value=float(stored["our_target_margin"]) if stored is not None else 0.30,
            step=0.01,
            key=f"store_target_margin_{product_id}",
        )

    stored_strategy = stored["our_strategy"] if stored is not None and stored["our_strategy"] in STRATEGY_KEYS else "balanced"
    store_strategy_label = st.selectbox(
        "Strategy",
        options=list(STRATEGY_LABELS.values()),
        index=STRATEGY_KEYS.index(stored_strategy),
        key=f"store_strategy_{product_id}",
    )
    store_strategy = {label: key for key, label in STRATEGY_LABELS.items()}[store_strategy_label]

    if st.button("Save store data", key="save_store_data"):
        store_payload = {
            "our_current_price": store_current_price,
            "our_cost_price": store_cost_price,
            "our_inventory": store_inventory,
            "our_sales_7d": store_sales_7d,
            "our_sales_30d": store_sales_30d,
            "our_target_margin": store_target_margin,
            "our_strategy": store_strategy,
        }
        is_valid, issues = validate_retailer_internal_payload(store_payload)
        if not is_valid:
            for issue in issues:
                st.error(issue)
            return
        try:
            upsert_retailer_internal_data(RAW_RETAILER_PATH, product_id, store_payload)
            st.success("Store data updated. Rebuild the dataset to refresh recommendations.")
        except ValueError as exc:
            st.error(str(exc))


def render_fx_update_section() -> None:
    """Render FX rate update workflow."""
    col1, col2 = st.columns(2)
    with col1:
        fx_source = st.selectbox(
            "FX source",
            options=["manual", "nobitex_usdt_proxy", "navasan", "tgju", "bonbast"],
            format_func=humanize_label,
            key="fx_source",
        )
    with col2:
        fx_symbol = st.text_input("Symbol", value="USDIRT", key="fx_symbol")

    fx_rate = st.text_input(
        "Manual FX rate (toman)",
        value="45,000",
        placeholder="e.g. 45,000",
        key="fx_rate_toman",
        on_change=normalize_price_input_state,
        args=("fx_rate_toman",),
    )
    parsed_fx_rate = parse_price_input(fx_rate)
    show_price_input_feedback(fx_rate)
    if parsed_fx_rate:
        st.caption(f"Preview: {parsed_fx_rate:,.0f} toman | {parsed_fx_rate * 10:,.0f} rial")

    fx_notes = st.text_area("Notes", placeholder="Optional: source URL or timestamp", key="fx_notes")
    if st.button("Save FX rate", key="save_fx"):
        if parsed_fx_rate is None or parsed_fx_rate <= 0:
            st.error("Please enter a valid positive FX rate in toman.")
            return

        fx_dict = {
            "source": fx_source,
            "symbol": fx_symbol,
            "rate_toman": parsed_fx_rate,
            "observed_at": datetime.now().isoformat(),
            "notes": fx_notes,
        }
        try:
            append_fx_rate_snapshot(RAW_FX_PATH, fx_dict)
            st.success(f"FX rate saved: {fx_symbol} = {parsed_fx_rate:,.0f} toman.")
            st.rerun()
        except ValueError as exc:
            st.error(f"Validation error: {exc}")


def render_add_product_section(products_df: pd.DataFrame) -> None:
    """Render add product workflow."""
    known_brands = get_known_brands(products_df)
    brand_options = sorted(set(known_brands)) + ["Other / Custom"]

    col1, col2, col3 = st.columns(3)
    with col1:
        brand_choice = st.selectbox("Brand", options=brand_options, key="new_product_brand_choice")
        new_brand = (
            st.text_input("Custom brand", key="new_product_brand")
            if brand_choice == "Other / Custom"
            else brand_choice
        )
        new_model = st.text_input("Model", key="new_product_model")
        new_product_name = st.text_input("Product name", key="new_product_name")
        new_product_query = st.text_input("Product search query", key="new_product_query")
        new_priority = st.selectbox("Priority", options=["high", "medium", "low"], index=1, key="new_product_priority")
        new_active = st.checkbox("Active", value=True, key="new_product_active")
    with col2:
        new_current_price = st.text_input(
            "Current price (toman)",
            placeholder="e.g. 37,200,000",
            key="new_current_price",
            on_change=normalize_price_input_state,
            args=("new_current_price",),
        )
        show_price_input_feedback(new_current_price)
        new_cost_price = st.text_input(
            "Cost price (toman)",
            placeholder="e.g. 25,000,000",
            key="new_cost_price",
            on_change=normalize_price_input_state,
            args=("new_cost_price",),
        )
        show_price_input_feedback(new_cost_price)
        new_inventory = st.number_input("Inventory", min_value=0, step=1, key="new_inventory")
        new_sales_7d = st.number_input("Sales (7d)", min_value=0, step=1, key="new_sales_7d")
        new_sales_30d = st.number_input("Sales (30d)", min_value=0, step=1, key="new_sales_30d")
        new_target_margin = st.number_input(
            "Target margin",
            min_value=0.0,
            max_value=1.0,
            value=0.30,
            step=0.01,
            key="new_target_margin",
        )
        new_strategy_label = st.selectbox(
            "Strategy",
            options=list(STRATEGY_LABELS.values()),
            index=1,
            key="new_strategy",
        )
        new_strategy = {label: key for key, label in STRATEGY_LABELS.items()}[new_strategy_label]
    with col3:
        new_base_usd_price = st.text_input("Base USD price", placeholder="e.g. 399.99", key="new_base_usd_price")
        new_base_usd_source = st.text_input("Base USD price source", placeholder="e.g. official_site", key="new_base_usd_source")
        new_usd_rate = st.text_input(
            "USD rate (toman)",
            placeholder="e.g. 90,000",
            key="new_usd_rate",
            on_change=normalize_price_input_state,
            args=("new_usd_rate",),
        )
        show_price_input_feedback(new_usd_rate)
        new_source_url = st.text_input("USD source URL", key="new_source_url")
        new_observed_at = st.date_input("USD observed at", key="new_observed_at")
        new_torob_url = st.text_input("Torob URL", key="new_torob_url")
        new_digikala_url = st.text_input("Digikala URL", key="new_digikala_url")
        new_global_url = st.text_input("Global reference URL", key="new_global_url")

    new_catalog_notes = st.text_area("Product notes", key="new_catalog_notes")
    new_usd_notes = st.text_area("USD reference notes", key="new_usd_notes")
    generated_product_id = generate_product_id(new_brand, new_model)
    if generated_product_id:
        st.caption(f"Product ID: {generated_product_id}")

    if st.button("Save new product", key="save_new_product"):
        normalized_brand = normalize_brand(new_brand, known_brands=known_brands)
        new_payload = {
            "product_id": generated_product_id,
            "brand": normalized_brand,
            "model": new_model,
            "product_name": new_product_name,
            "product_query": new_product_query,
            "priority": new_priority,
            "active": new_active,
            "torob_url": new_torob_url,
            "digikala_url": new_digikala_url,
            "global_reference_url": new_global_url,
            "catalog_notes": new_catalog_notes,
            "our_current_price": new_current_price,
            "our_cost_price": new_cost_price,
            "our_inventory": new_inventory,
            "our_sales_7d": new_sales_7d,
            "our_sales_30d": new_sales_30d,
            "our_target_margin": new_target_margin,
            "our_strategy": new_strategy,
            "base_usd_price": new_base_usd_price,
            "base_usd_price_source": new_base_usd_source,
            "usd_rate": new_usd_rate,
            "source_url": new_source_url,
            "observed_at": new_observed_at.isoformat(),
            "usd_notes": new_usd_notes,
        }
        is_valid, issues = validate_new_product_payload(new_payload)
        try:
            retailer_df = load_retailer_internal_data(RAW_RETAILER_PATH)
            usd_df = load_global_usd_reference(RAW_USD_PATH)
            duplicate = product_id_exists(generated_product_id, products_df, retailer_df, usd_df)
        except (FileNotFoundError, ValueError) as exc:
            is_valid = False
            issues.append(str(exc))
            duplicate = False
        if duplicate:
            issues.append(f"Product ID already exists: {generated_product_id}")
            is_valid = False
        if not is_valid:
            for issue in issues:
                st.error(issue)
            return
        try:
            append_new_product(RAW_PRODUCTS_PATH, RAW_RETAILER_PATH, RAW_USD_PATH, new_payload)
            st.success("Product added. Rebuild the dataset to include it in recommendations.")
        except ValueError as exc:
            st.error(str(exc))


def render_build_dataset_section(products_df: pd.DataFrame) -> None:
    """Render processed dataset build workflow."""
    st.caption("After saving updates, rebuild the dataset to refresh recommendations.")
    if PROCESSED_DATASET_PATH.exists():
        modified = datetime.fromtimestamp(PROCESSED_DATASET_PATH.stat().st_mtime)
        st.success(f"Last processed dataset found: {modified.strftime('%Y-%m-%d %H:%M')}")
    else:
        st.warning("No processed dataset found. Build the dataset first.")

    st.code("python scripts/build_pricing_dataset.py", language="bash")
    if st.button("Recalculate recommendations from saved inputs", key="run_build"):
        try:
            with st.spinner("Building processed dataset..."):
                market = load_market_observations(RAW_MARKET_PATH)
                retailer = load_retailer_internal_data(RAW_RETAILER_PATH)
                usd = load_global_usd_reference(RAW_USD_PATH)
                daily_updates = load_daily_market_updates(RAW_UPDATES_PATH)
                fx_snapshots = load_fx_rate_snapshots(RAW_FX_PATH)
                result = build_dashboard_pricing_dataset(
                    market,
                    retailer,
                    usd,
                    daily_updates_df=daily_updates,
                    fx_snapshots_df=fx_snapshots,
                    products_df=products_df,
                )
                save_dashboard_pricing_dataset(result)
            st.success(f"Build complete. Generated {len(result)} recommendation rows.")
        except Exception as exc:
            st.error(f"Build failed: {exc}")


def render_data_operations_tab() -> None:
    """Render all data entry and maintenance workflows."""
    st.caption("Use these sections to maintain the saved inputs behind recommendations.")
    try:
        products_df = load_products_master()
        updates_df = load_daily_market_updates()
    except FileNotFoundError as exc:
        st.error(f"Raw data file missing: {exc}")
        return

    today = datetime.now().strftime("%Y-%m-%d")
    missing_products = get_products_missing_update_today(products_df, updates_df, today)
    active_count = len(products_df[products_df.get("active", True) == True])
    updated_today = 0
    if not updates_df.empty:
        updates_with_date = updates_df.copy()
        updates_with_date["date"] = pd.to_datetime(updates_with_date["observed_at"], errors="coerce").dt.strftime("%Y-%m-%d")
        updated_today = len(updates_with_date[updates_with_date["date"] == today]["product_id"].unique())

    status_cols = st.columns(3)
    status_cols[0].metric("Active products", active_count)
    status_cols[1].metric("Updated today", updated_today)
    status_cols[2].metric("Missing updates", len(missing_products))

    with st.expander("A. Update Market Prices", expanded=True):
        render_market_update_section(products_df, updates_df)
    with st.expander("B. Update Our Store Data"):
        render_store_update_section(products_df)
    with st.expander("C. Update FX Rate"):
        render_fx_update_section()
    with st.expander("D. Add New Product"):
        render_add_product_section(products_df)
    with st.expander("E. Build Processed Dataset"):
        render_build_dataset_section(products_df)


def render_analytics_tab(recs_df: pd.DataFrame) -> None:
    """Render high-level visual summaries."""
    if recs_df.empty:
        st.warning("No recommendation data available for charts.")
        return

    chart_df = recs_df.copy()
    chart_df["Action"] = chart_df["action"].apply(humanize_label)
    chart_df["Risk"] = chart_df["risk_level"].apply(humanize_label)
    chart_df["Price Change %"] = chart_df.apply(
        lambda row: numeric_value(row.get("recommended_price"), 0) / numeric_value(row.get("current_price"), 1) - 1
        if numeric_value(row.get("current_price"), 0) > 0
        else 0,
        axis=1,
    ) * 100

    col1, col2 = st.columns(2)
    with col1:
        action_counts = chart_df["Action"].value_counts().reset_index()
        action_counts.columns = ["Action", "Count"]
        st.plotly_chart(px.bar(action_counts, x="Action", y="Count", title="Action distribution"), width="stretch")
    with col2:
        risk_counts = chart_df["Risk"].value_counts().reset_index()
        risk_counts.columns = ["Risk", "Count"]
        st.plotly_chart(px.bar(risk_counts, x="Risk", y="Count", title="Risk distribution"), width="stretch")

    col3, col4 = st.columns(2)
    with col3:
        st.plotly_chart(
            px.histogram(chart_df, x="Price Change %", nbins=15, title="Price change distribution"),
            width="stretch",
        )
    with col4:
        if "iran_market_premium_pct" in chart_df.columns:
            premium_df = chart_df.dropna(subset=["iran_market_premium_pct"]).copy()
            premium_df["Iran Premium %"] = premium_df["iran_market_premium_pct"] * 100
            st.plotly_chart(
                px.histogram(premium_df, x="Iran Premium %", nbins=15, title="Market premium distribution"),
                width="stretch",
            )
        else:
            st.info("Market premium data is not available for this dataset.")

    comparison_df = chart_df[["product_name", "current_price", "recommended_price"]].head(15).copy()
    comparison_df = comparison_df.rename(
        columns={
            "product_name": "Product",
            "current_price": "Current Price",
            "recommended_price": "Recommended Price",
        }
    )
    comparison_long = comparison_df.melt(id_vars="Product", var_name="Price Type", value_name="Price")
    st.plotly_chart(
        px.bar(
            comparison_long,
            x="Product",
            y="Price",
            color="Price Type",
            barmode="group",
            title="Current price vs recommended price",
        ),
        width="stretch",
    )


def render_system_tab(data_mode: str) -> None:
    """Render lightweight technical/project information."""
    st.caption("Technical details for demos, development, and API review.")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Current data source", data_mode)
        st.caption(f"Processed dataset path: {PROCESSED_DATASET_PATH}")
        if PROCESSED_DATASET_PATH.exists():
            st.success("Processed dataset is available.")
        else:
            st.warning("No processed dataset found. Go to Data Operations and build the dataset first.")
    with col2:
        st.code("uvicorn src.api.main:app --reload", language="bash")
        st.caption("API run command")
        st.code("streamlit run src/dashboard/app.py", language="bash")
        st.caption("Dashboard run command")

    st.info("Test status note: run the project test suite before a demo or handoff.")
    st.markdown("API docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)")


def main() -> None:
    """Main Streamlit application."""
    st.set_page_config(page_title="PricePilot AI", layout="wide")
    st.title("PricePilot AI")
    st.caption("Guided pricing operations for smartwatch retail teams.")

    df, selected_strategy, manual_usd_rate, usd_shock, data_mode = render_sidebar(None)
    if df is None or df.empty:
        if data_mode == "Demo Scenario (20 Products)":
            st.error("Demo dataset could not be prepared. Please check scenario files.")
        elif data_mode == "Upload CSV":
            st.info("Upload a CSV in the sidebar to review recommendations.")
        else:
            st.warning("No products are available for recommendations.")

        tabs = st.tabs(["🏠 Overview", "🎯 Decision Center", "📝 Data Operations", "📊 Analytics", "⚙️ System / API"])
        with tabs[2]:
            render_data_operations_tab()
        with tabs[4]:
            render_system_tab(data_mode)
        return

    recs_df = build_recommendations(df, usd_shock, selected_strategy, manual_usd_rate)
    tabs = st.tabs(["🏠 Overview", "🎯 Decision Center", "📝 Data Operations", "📊 Analytics", "⚙️ System / API"])
    with tabs[0]:
        render_overview_tab(recs_df, data_mode)
    with tabs[1]:
        render_decision_center_tab(recs_df)
    with tabs[2]:
        render_data_operations_tab()
    with tabs[3]:
        render_analytics_tab(recs_df)
    with tabs[4]:
        render_system_tab(data_mode)


if __name__ == "__main__":
    main()
