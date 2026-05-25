"""
Market data aggregation utilities for Phase 3 real data foundation.

Pure functions for aggregating market observations into product-level insights.
No external dependencies beyond pandas.
"""

from typing import Dict, List, Optional
import pandas as pd


def aggregate_market_observations(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate market observations by product_id to calculate market-level statistics.
    
    This function takes a dataframe of individual price observations and produces
    a summary with min, median, max, and seller information per product.
    
    Args:
        df: DataFrame with columns:
            - product_id
            - normalized_product_name
            - brand
            - model
            - listed_price
            - availability_status
            - seller_name
            - source
            
    Returns:
        DataFrame with aggregated market data (one row per product_id):
            - product_id
            - product_name
            - brand
            - model
            - market_min_price
            - market_median_price
            - market_max_price
            - market_avg_price
            - seller_count
            - available_seller_count
            - price_spread_percent
    """
    if df.empty:
        # Return empty dataframe with expected columns
        return pd.DataFrame(columns=[
            'product_id',
            'product_name',
            'brand',
            'model',
            'market_min_price',
            'market_median_price',
            'market_max_price',
            'market_avg_price',
            'seller_count',
            'available_seller_count',
            'price_spread_percent',
        ])
    
    # Group by product_id
    agg_groups = df.groupby('product_id', group_keys=False)
    
    results = []
    
    for product_id, group in agg_groups:
        # Get representative product info from first row
        first_row = group.iloc[0]
        product_name = first_row.get('normalized_product_name', 'Unknown')
        brand = first_row.get('brand', 'Unknown')
        model = first_row.get('model', 'Unknown')
        
        # Calculate price statistics (ensure float conversion)
        prices = pd.to_numeric(group['listed_price'], errors='coerce').dropna()
        
        if len(prices) == 0:
            # Skip products with no price data
            continue
        
        min_price = prices.min()
        median_price = prices.median()
        max_price = prices.max()
        avg_price = prices.mean()
        
        # Calculate seller statistics
        seller_counts = calculate_seller_counts(group)
        seller_count = seller_counts['total']
        available_seller_count = seller_counts['available']
        
        # Calculate price spread
        spread_pct = calculate_price_spread_percent(group)
        
        results.append({
            'product_id': product_id,
            'product_name': product_name,
            'brand': brand,
            'model': model,
            'market_min_price': float(min_price),
            'market_median_price': float(median_price),
            'market_max_price': float(max_price),
            'market_avg_price': float(avg_price),
            'seller_count': int(seller_count),
            'available_seller_count': int(available_seller_count),
            'price_spread_percent': float(spread_pct),
        })
    
    return pd.DataFrame(results)


def calculate_market_min_median_max(df: pd.DataFrame) -> Dict[str, float]:
    """
    Calculate min, median, and max prices from market observations.
    
    Args:
        df: DataFrame with 'listed_price' column
        
    Returns:
        Dictionary with keys: 'min', 'median', 'max'
    """
    prices = pd.to_numeric(df['listed_price'], errors='coerce').dropna()
    
    if len(prices) == 0:
        return {'min': 0.0, 'median': 0.0, 'max': 0.0}
    
    return {
        'min': float(prices.min()),
        'median': float(prices.median()),
        'max': float(prices.max()),
    }


def calculate_seller_counts(df: pd.DataFrame) -> Dict[str, int]:
    """
    Calculate total unique sellers and available sellers count.
    
    Available means availability_status == 'available' or 'low_stock'.
    
    Args:
        df: DataFrame with columns:
            - seller_name
            - availability_status
            
    Returns:
        Dictionary with keys: 'total', 'available'
    """
    total_sellers = df['seller_name'].nunique()
    
    available_statuses = ['available', 'low_stock']
    available_rows = df[df['availability_status'].isin(available_statuses)]
    available_sellers = available_rows['seller_name'].nunique()
    
    return {
        'total': int(total_sellers),
        'available': int(available_sellers),
    }


def calculate_price_spread_percent(df: pd.DataFrame) -> float:
    """
    Calculate price spread as (max - min) / median * 100.
    
    This shows how much prices vary relative to the median price.
    If all prices are identical, returns 0.0.
    
    Args:
        df: DataFrame with 'listed_price' column
        
    Returns:
        Spread percentage (float), non-negative
    """
    prices = pd.to_numeric(df['listed_price'], errors='coerce').dropna()
    
    if len(prices) < 2:
        # Need at least 2 prices to calculate spread
        return 0.0
    
    min_price = prices.min()
    max_price = prices.max()
    median_price = prices.median()
    
    if median_price == 0:
        # Avoid division by zero
        return 0.0
    
    spread = ((max_price - min_price) / median_price) * 100
    
    return float(spread)


def merge_market_observations_with_internal(
    market_agg_df: pd.DataFrame,
    internal_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Merge aggregated market observations with internal retailer data.
    
    This creates a combined dataframe for Phase 2 schema with both
    market-level and internal-level pricing information.
    
    Args:
        market_agg_df: Output from aggregate_market_observations()
        internal_df: DataFrame with our internal data:
            - product_id
            - our_current_price
            - our_cost_price
            - our_inventory
            - our_sales_7d
            - our_sales_30d
            - our_target_margin
            - our_strategy
            
    Returns:
        Merged DataFrame with market + internal data
    """
    merged = market_agg_df.merge(
        internal_df,
        on='product_id',
        how='inner',
    )
    
    return merged


def validate_market_observations(df: pd.DataFrame) -> tuple[bool, List[str]]:
    """
    Validate that market observations dataframe has required columns and data quality.
    
    Args:
        df: DataFrame to validate
        
    Returns:
        Tuple of (is_valid: bool, issues: List[str])
    """
    issues = []
    
    required_columns = [
        'observation_id',
        'observed_at',
        'product_id',
        'normalized_product_name',
        'brand',
        'model',
        'listed_price',
        'availability_status',
        'seller_name',
    ]
    
    for col in required_columns:
        if col not in df.columns:
            issues.append(f"Missing required column: {col}")
    
    if df.empty:
        issues.append("DataFrame is empty")
        return (False, issues)
    
    # Check for negative prices
    price_col = df.get('listed_price')
    if price_col is not None:
        negative_prices = (price_col < 0).sum()
        if negative_prices > 0:
            issues.append(f"Found {negative_prices} negative prices")
    
    # Check for missing product_ids
    missing_ids = df['product_id'].isna().sum()
    if missing_ids > 0:
        issues.append(f"Found {missing_ids} rows with missing product_id")
    
    is_valid = len(issues) == 0
    return (is_valid, issues)
