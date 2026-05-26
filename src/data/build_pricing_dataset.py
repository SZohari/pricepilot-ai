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
        
    Returns:
        DataFrame with Phase 2 schema, one row per product_id
    """
    
    # Step 1: Aggregate market observations
    market_agg = aggregate_market_observations(market_df)
    
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
    
    # Step 4: Calculate derived fields
    
    # Use provided usd_rate override if available, otherwise use from merged data
    if usd_rate is not None:
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
