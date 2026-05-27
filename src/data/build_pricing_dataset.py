"""
Build pipeline: Convert raw market observations into dashboard-ready Phase 2 pricing dataset.

Pure functions for:
1. Loading raw data (market observations, retailer internal, USD reference)
2. Aggregating market observations
3. Merging all data sources
4. Calculating derived fields
5. Generating Phase 2 dashboard schema output
"""

from typing import Dict, List, Optional, Tuple
import pandas as pd
from pathlib import Path

from src.data.market_aggregation import (
    aggregate_market_observations,
    validate_market_observations,
)


def _latest_rows_by_timestamp(df: pd.DataFrame, group_column: str) -> pd.DataFrame:
    """Return the latest row per group, using file order to break timestamp ties."""
    if df is None or df.empty or group_column not in df.columns:
        return pd.DataFrame()

    ordered = df.copy()
    ordered['_row_order'] = range(len(ordered))
    ordered['_observed_at'] = pd.to_datetime(ordered.get('observed_at'), errors='coerce')
    ordered = ordered.sort_values(
        ['_observed_at', '_row_order'],
        kind='stable',
        na_position='first',
    )
    return ordered.drop_duplicates(subset=[group_column], keep='last')


def apply_daily_market_updates(
    market_agg: pd.DataFrame,
    daily_updates_df: Optional[pd.DataFrame],
    products_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """Overlay each product's latest manual market update on aggregated prices."""
    result = market_agg.copy()
    platform_fallbacks = {
        'torob_min_price': 'market_min_price',
        'torob_median_price': 'market_median_price',
        'digikala_price': 'market_median_price',
    }
    for column, fallback_column in platform_fallbacks.items():
        if column not in result.columns:
            result[column] = result[fallback_column]
        else:
            result[column] = pd.to_numeric(result[column], errors='coerce').fillna(result[fallback_column])

    latest_updates = _latest_rows_by_timestamp(daily_updates_df, 'product_id')
    if latest_updates.empty:
        return result

    numeric_columns = [
        'torob_min_price',
        'torob_median_price',
        'digikala_price',
        'market_max_price',
    ]
    for column in numeric_columns:
        if column in latest_updates.columns:
            latest_updates[column] = pd.to_numeric(latest_updates[column], errors='coerce')

    if products_df is not None and not products_df.empty:
        existing_ids = set(result['product_id'])
        for _, update in latest_updates.iterrows():
            if update['product_id'] in existing_ids:
                continue
            catalog = products_df[products_df['product_id'] == update['product_id']]
            supplied = [
                update.get(column) for column in numeric_columns
                if pd.notna(update.get(column)) and update.get(column) > 0
            ]
            if catalog.empty or not supplied:
                continue
            catalog_row = catalog.iloc[0]
            min_price = update.get('torob_min_price')
            median_price = update.get('torob_median_price')
            max_price = update.get('market_max_price')
            min_price = min_price if pd.notna(min_price) and min_price > 0 else min(supplied)
            median_price = median_price if pd.notna(median_price) and median_price > 0 else min_price
            max_price = max_price if pd.notna(max_price) and max_price > 0 else max(supplied + [min_price, median_price])
            result = pd.concat([result, pd.DataFrame([{
                'product_id': update['product_id'],
                'product_name': catalog_row['product_name'],
                'brand': catalog_row['brand'],
                'model': catalog_row['model'],
                'market_min_price': float(min_price),
                'market_median_price': float(median_price),
                'market_max_price': float(max_price),
                'market_avg_price': float(sum(supplied) / len(supplied)),
                'seller_count': 1,
                'available_seller_count': 1,
                'torob_min_price': float(min_price),
                'torob_median_price': float(median_price),
                'digikala_price': float(update.get('digikala_price')) if pd.notna(update.get('digikala_price')) and update.get('digikala_price') > 0 else float(median_price),
            }])], ignore_index=True)
            existing_ids.add(update['product_id'])

    for _, update in latest_updates.iterrows():
        matching = result['product_id'] == update['product_id']
        if not matching.any():
            continue

        supplied_prices = []
        for source_column, target_column in [
            ('torob_min_price', 'market_min_price'),
            ('torob_median_price', 'market_median_price'),
            ('digikala_price', 'digikala_price'),
        ]:
            value = update.get(source_column)
            if pd.notna(value) and value > 0:
                result.loc[matching, source_column] = value
                if source_column != 'digikala_price':
                    result.loc[matching, target_column] = value
                supplied_prices.append(value)

        market_max = update.get('market_max_price')
        if pd.notna(market_max) and market_max > 0:
            result.loc[matching, 'market_max_price'] = market_max
        elif supplied_prices:
            inferred_prices = supplied_prices + [
                result.loc[matching, 'market_min_price'].iloc[0],
                result.loc[matching, 'market_median_price'].iloc[0],
                result.loc[matching, 'market_max_price'].iloc[0],
            ]
            result.loc[matching, 'market_max_price'] = max(
                value for value in inferred_prices if pd.notna(value)
            )

    return result


def latest_positive_fx_rate(fx_snapshots_df: Optional[pd.DataFrame]) -> Optional[float]:
    """Return the latest positive manual FX rate, or None when none is valid."""
    if fx_snapshots_df is None or fx_snapshots_df.empty or 'rate_toman' not in fx_snapshots_df.columns:
        return None

    valid = fx_snapshots_df.copy()
    valid['rate_toman'] = pd.to_numeric(valid['rate_toman'], errors='coerce')
    valid = valid[valid['rate_toman'] > 0]
    if valid.empty:
        return None

    latest = _latest_rows_by_timestamp(valid.assign(_fx_group='rate'), '_fx_group')
    return float(latest.iloc[0]['rate_toman'])


def load_market_observations(path: str) -> pd.DataFrame:
    """
    Load raw market observations from CSV.
    
    Args:
        path: Path to market_observations_template.csv
        
    Returns:
        DataFrame with columns: product_id, listed_price, availability_status, seller_name, etc.
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If data validation fails
    """
    if not Path(path).exists():
        raise FileNotFoundError(f"Market observations file not found: {path}")
    
    df = pd.read_csv(path)
    
    is_valid, issues = validate_market_observations(df)
    if not is_valid:
        raise ValueError(f"Market observations validation failed:\n" + "\n".join(issues))
    
    return df


def load_retailer_internal_data(path: str) -> pd.DataFrame:
    """
    Load retailer internal data from CSV.
    
    Args:
        path: Path to retailer_internal_demo_template.csv
        
    Returns:
        DataFrame with columns: product_id, our_current_price, our_cost_price, etc.
        
    Raises:
        FileNotFoundError: If file doesn't exist
    """
    if not Path(path).exists():
        raise FileNotFoundError(f"Retailer internal data file not found: {path}")
    
    df = pd.read_csv(path)
    
    required_cols = [
        'product_id',
        'our_current_price',
        'our_cost_price',
        'our_inventory',
        'our_sales_7d',
        'our_sales_30d',
        'our_target_margin',
        'our_strategy',
    ]
    
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Retailer data missing required columns: {', '.join(missing)}")
    
    return df


def load_global_usd_reference(path: str) -> pd.DataFrame:
    """
    Load global USD reference data from CSV.
    
    Args:
        path: Path to global_usd_reference_template.csv
        
    Returns:
        DataFrame with columns: product_id, base_usd_price, usd_rate, etc.
        
    Raises:
        FileNotFoundError: If file doesn't exist
    """
    if not Path(path).exists():
        raise FileNotFoundError(f"USD reference file not found: {path}")
    
    df = pd.read_csv(path)
    
    required_cols = [
        'product_id',
        'brand',
        'model',
        'base_usd_price',
        'base_usd_price_source',
        'usd_rate',
    ]
    
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"USD reference missing required columns: {', '.join(missing)}")
    
    return df


def build_dashboard_pricing_dataset(
    market_df: pd.DataFrame,
    retailer_df: pd.DataFrame,
    usd_df: pd.DataFrame,
    usd_rate: Optional[float] = None,
    daily_updates_df: Optional[pd.DataFrame] = None,
    fx_snapshots_df: Optional[pd.DataFrame] = None,
    products_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Build dashboard-ready Phase 2 pricing dataset from raw data sources.
    
    Pipeline:
    1. Aggregate market observations by product_id
    2. Merge with USD reference data
    3. Merge with retailer internal data
    4. Calculate theoretical_toman_price and iran_market_premium_pct
    5. Preserve all Phase 2 required fields
    
    Args:
        market_df: Raw market observations (from load_market_observations)
        retailer_df: Retailer internal data (from load_retailer_internal_data)
        usd_df: USD reference data (from load_global_usd_reference)
        usd_rate: Optional override for USD rate (uses usd_df value if not provided)
        daily_updates_df: Optional manually entered market updates to overlay by product.
        fx_snapshots_df: Optional manually entered FX snapshots; latest positive rate wins.
        products_df: Optional product catalog for products introduced by manual updates.
        
    Returns:
        DataFrame with Phase 2 schema, one row per product_id
    """
    
    # Step 1: Aggregate market observations
    market_agg = aggregate_market_observations(market_df)
    market_agg = apply_daily_market_updates(market_agg, daily_updates_df, products_df)
    
    if len(market_agg) == 0:
        raise ValueError("No products found after aggregating market observations")
    
    # Step 2: Merge with USD reference data
    merged = market_agg.merge(
        usd_df,
        on='product_id',
        how='inner',
        suffixes=('_market', '_usd'),
    )
    
    if len(merged) == 0:
        raise ValueError("No products matched between market aggregates and USD reference")
    
    # Step 3: Merge with retailer internal data
    merged = merged.merge(
        retailer_df,
        on='product_id',
        how='inner',
    )
    
    if len(merged) == 0:
        raise ValueError("No products matched between aggregates and retailer data")

    # If a products catalog is provided, prefer its authoritative metadata for
    # brand/model/product_name/product_query when present (override merged values).
    if products_df is not None and not products_df.empty:
        key_cols = ['brand', 'model', 'product_name', 'product_query']
        prod_index = products_df.set_index('product_id')
        for col in key_cols:
            if col not in prod_index.columns:
                continue
            # Build array aligned to merged rows
            mapped = prod_index[col].reindex(merged['product_id']).values
            # Ensure column exists in merged
            if col not in merged.columns:
                merged[col] = ''
            # Apply overrides where catalog has a non-empty value
            for i, v in enumerate(mapped):
                try:
                    if pd.notna(v) and str(v).strip() != '':
                        merged.at[i, col] = v
                except Exception:
                    # Defensive: skip any mapping errors
                    continue
    
    # Step 4: Calculate derived fields
    
    # A saved valid FX snapshot is the most recent user-entered exchange rate.
    snapshot_rate = latest_positive_fx_rate(fx_snapshots_df)
    if snapshot_rate is not None:
        merged['usd_rate'] = snapshot_rate
    elif usd_rate is not None:
        merged['usd_rate'] = usd_rate
    else:
        # Check if usd_rate exists in merged data
        if 'usd_rate' not in merged.columns:
            raise ValueError("USD rate not available in merged data - must be provided as parameter or in USD reference data")
        # If it exists as a string (from CSV), convert to float
        if merged['usd_rate'].dtype == 'object':
            merged['usd_rate'] = pd.to_numeric(merged['usd_rate'], errors='coerce')
    
    # Theoretical toman price = base USD price * exchange rate
    merged['theoretical_toman_price'] = (
        merged['base_usd_price'] * merged['usd_rate']
    ).astype(int)
    
    # Iran market premium % = (market_median - theoretical) / theoretical
    merged['iran_market_premium_pct'] = (
        (merged['market_median_price'] - merged['theoretical_toman_price']) / 
        merged['theoretical_toman_price']
    )
    
    # Step 5: Select and order Phase 2 schema columns
    phase2_columns = [
        'product_id',
        'product_name',
        'brand',
        'model',
        'category',
        'base_usd_price',
        'base_usd_price_source',
        'usd_rate',
        'theoretical_toman_price',
        'market_min_price',
        'market_median_price',
        'market_max_price',
        'market_avg_price',
        'seller_count',
        'available_seller_count',
        'torob_min_price',
        'torob_median_price',
        'digikala_price',
        'our_current_price',
        'our_cost_price',
        'our_inventory',
        'our_sales_7d',
        'our_sales_30d',
        'our_target_margin',
        'our_strategy',
        'observed_at',
        'iran_market_premium_pct',
    ]
    
    # Add columns that exist in merged data
    available_cols = [c for c in phase2_columns if c in merged.columns]
    
    result = merged[available_cols].copy()
    
    # Ensure no duplicates
    result = result.drop_duplicates(subset=['product_id'], keep='first')
    
    return result


def save_dashboard_pricing_dataset(
    df: pd.DataFrame,
    output_path: str = 'data/processed/dashboard_pricing_data.csv',
) -> Path:
    """
    Save dashboard-ready pricing dataset to CSV.
    
    Args:
        df: DataFrame from build_dashboard_pricing_dataset()
        output_path: Output file path (default: data/processed/dashboard_pricing_data.csv)
        
    Returns:
        Path to saved file
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    df.to_csv(output_file, index=False)
    
    return output_file


def load_processed_pricing_data(
    output_path: str = 'data/processed/dashboard_pricing_data.csv',
) -> Optional[pd.DataFrame]:
    """
    Load the processed dashboard-ready pricing dataset.
    
    This function is used by the Streamlit dashboard to load real market data
    that was generated by the build_pricing_dataset.py pipeline.
    
    Args:
        output_path: Path to the processed CSV file (default: data/processed/dashboard_pricing_data.csv)
        
    Returns:
        DataFrame with Phase 2 schema if file exists and is valid, None otherwise
        
    Raises:
        FileNotFoundError: If the processed file doesn't exist
        ValueError: If the file doesn't have required Phase 2 schema columns
    """
    output_file = Path(output_path)
    
    if not output_file.exists():
        raise FileNotFoundError(
            f"Processed dataset not found at {output_file}\n"
            f"Run: python scripts/build_pricing_dataset.py"
        )
    
    df = pd.read_csv(output_file)
    
    # Validate that it has the expected Phase 2 schema columns
    required_fields = [
        'product_id',
        'product_name',
        'market_median_price',
        'our_current_price',
        'our_cost_price',
        'our_target_margin',
        'our_strategy',
    ]
    
    missing = [f for f in required_fields if f not in df.columns]
    if missing:
        raise ValueError(
            f"Processed dataset missing required fields: {', '.join(missing)}\n"
            f"Run: python scripts/build_pricing_dataset.py to regenerate"
        )
    
    return df
