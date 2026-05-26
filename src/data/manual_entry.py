"""
Manual data entry helpers for market updates and FX snapshots.

Pure functions for:
1. Loading product master, daily updates, and FX snapshots
2. Appending new market updates and FX snapshots
3. Validating user input
4. Querying latest updates
5. Finding products missing today's update
"""

from typing import Dict, List, Optional, Tuple
import pandas as pd
from pathlib import Path
from datetime import datetime


def load_products_master(path: str = 'data/raw/products_master.csv') -> pd.DataFrame:
    """
    Load product master list.
    
    Args:
        path: Path to products_master.csv
        
    Returns:
        DataFrame with columns: product_id, brand, model, product_name, etc.
        
    Raises:
        FileNotFoundError: If file doesn't exist
    """
    if not Path(path).exists():
        raise FileNotFoundError(f"Products master file not found: {path}")
    
    df = pd.read_csv(path)
    return df


def load_daily_market_updates(path: str = 'data/raw/daily_market_updates.csv') -> pd.DataFrame:
    """
    Load daily market updates from CSV.
    
    Args:
        path: Path to daily_market_updates.csv
        
    Returns:
        DataFrame with columns: update_id, observed_at, product_id, prices, etc.
        If file only has headers, returns empty DataFrame.
        
    Raises:
        FileNotFoundError: If file doesn't exist
    """
    if not Path(path).exists():
        raise FileNotFoundError(f"Daily updates file not found: {path}")
    
    df = pd.read_csv(path)
    
    # If only headers, return empty dataframe with correct columns
    if len(df) == 0:
        return df
    
    # Ensure numeric columns are numeric
    numeric_cols = [
        'torob_min_price',
        'torob_median_price',
        'digikala_price',
        'market_max_price',
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    return df


def load_fx_rate_snapshots(path: str = 'data/raw/fx_rate_snapshots.csv') -> pd.DataFrame:
    """
    Load FX rate snapshots from CSV.
    
    Args:
        path: Path to fx_rate_snapshots.csv
        
    Returns:
        DataFrame with columns: observed_at, source, symbol, rate_toman, rate_irr, notes.
        If file only has headers, returns empty DataFrame.
        
    Raises:
        FileNotFoundError: If file doesn't exist
    """
    if not Path(path).exists():
        raise FileNotFoundError(f"FX rate snapshots file not found: {path}")
    
    df = pd.read_csv(path)
    
    # If only headers, return empty dataframe with correct columns
    if len(df) == 0:
        return df
    
    # Ensure numeric columns are numeric
    df['rate_toman'] = pd.to_numeric(df['rate_toman'], errors='coerce')
    df['rate_irr'] = pd.to_numeric(df['rate_irr'], errors='coerce')
    
    return df


def validate_daily_market_update(update_dict: Dict) -> Tuple[bool, List[str]]:
    """
    Validate a market update dictionary.
    
    Args:
        update_dict: Dictionary with keys like product_id, torob_min_price, etc.
        
    Returns:
        Tuple of (is_valid, error_messages)
    """
    issues = []
    
    # product_id is required
    if 'product_id' not in update_dict or not update_dict['product_id']:
        issues.append("product_id is required")
    
    # At least one price field must be provided
    price_fields = ['torob_min_price', 'torob_median_price', 'digikala_price', 'market_max_price']
    price_values = [update_dict.get(f) for f in price_fields]
    has_price = any(v is not None and str(v).strip() != '' for v in price_values)
    
    if not has_price:
        issues.append("At least one price field (torob_min/median, digikala, market_max) must be provided")
    
    # Validate numeric fields
    for field in price_fields:
        value = update_dict.get(field)
        if value is not None and str(value).strip() != '':
            try:
                float(value)
            except (ValueError, TypeError):
                issues.append(f"{field} must be numeric if provided")
    
    return (len(issues) == 0, issues)


def validate_fx_rate_snapshot(fx_dict: Dict) -> Tuple[bool, List[str]]:
    """
    Validate an FX rate snapshot dictionary.
    
    Args:
        fx_dict: Dictionary with keys like source, symbol, rate_toman, etc.
        
    Returns:
        Tuple of (is_valid, error_messages)
    """
    issues = []
    
    # source is required
    if 'source' not in fx_dict or not fx_dict['source']:
        issues.append("source is required")
    
    # symbol is required
    if 'symbol' not in fx_dict or not fx_dict['symbol']:
        issues.append("symbol is required")
    
    # rate_toman is required and must be positive
    if 'rate_toman' not in fx_dict or not fx_dict['rate_toman']:
        issues.append("rate_toman is required")
    else:
        try:
            rate = float(fx_dict['rate_toman'])
            if rate <= 0:
                issues.append("rate_toman must be positive")
        except (ValueError, TypeError):
            issues.append("rate_toman must be numeric")
    
    return (len(issues) == 0, issues)


def append_daily_market_update(
    path: str,
    update_dict: Dict,
) -> bool:
    """
    Append a market update to daily_market_updates.csv.
    
    Args:
        path: Path to daily_market_updates.csv
        update_dict: Dictionary with update data
        
    Returns:
        True if successful
        
    Raises:
        ValueError: If validation fails
    """
    # Validate first
    is_valid, issues = validate_daily_market_update(update_dict)
    if not is_valid:
        raise ValueError("Update validation failed:\n" + "\n".join(issues))
    
    # Load existing data
    try:
        df = pd.read_csv(path)
    except Exception:
        # File might not exist or be empty, create with headers
        df = pd.DataFrame(columns=[
            'update_id',
            'observed_at',
            'product_id',
            'torob_min_price',
            'torob_median_price',
            'digikala_price',
            'market_max_price',
            'availability_note',
            'notes',
        ])
    
    # Generate update_id (timestamp-based)
    now = datetime.now()
    update_id = f"UPD-{now.strftime('%Y%m%d-%H%M%S')}"
    
    # Build new row
    new_row = {
        'update_id': update_id,
        'observed_at': update_dict.get('observed_at', now.isoformat()),
        'product_id': update_dict.get('product_id', ''),
        'torob_min_price': update_dict.get('torob_min_price', ''),
        'torob_median_price': update_dict.get('torob_median_price', ''),
        'digikala_price': update_dict.get('digikala_price', ''),
        'market_max_price': update_dict.get('market_max_price', ''),
        'availability_note': update_dict.get('availability_note', ''),
        'notes': update_dict.get('notes', ''),
    }
    
    # Append to dataframe
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    
    # Save to CSV
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    
    return True


def append_fx_rate_snapshot(
    path: str,
    fx_dict: Dict,
) -> bool:
    """
    Append an FX rate snapshot to fx_rate_snapshots.csv.
    
    Args:
        path: Path to fx_rate_snapshots.csv
        fx_dict: Dictionary with FX snapshot data
        
    Returns:
        True if successful
        
    Raises:
        ValueError: If validation fails
    """
    # Validate first
    is_valid, issues = validate_fx_rate_snapshot(fx_dict)
    if not is_valid:
        raise ValueError("FX snapshot validation failed:\n" + "\n".join(issues))
    
    # Load existing data
    try:
        df = pd.read_csv(path)
    except Exception:
        # File might not exist or be empty, create with headers
        df = pd.DataFrame(columns=[
            'observed_at',
            'source',
            'symbol',
            'rate_toman',
            'rate_irr',
            'notes',
        ])
    
    # Build new row
    now = datetime.now()
    new_row = {
        'observed_at': fx_dict.get('observed_at', now.isoformat()),
        'source': fx_dict.get('source', ''),
        'symbol': fx_dict.get('symbol', ''),
        'rate_toman': fx_dict.get('rate_toman', ''),
        'rate_irr': fx_dict.get('rate_irr', ''),
        'notes': fx_dict.get('notes', ''),
    }
    
    # Append to dataframe
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    
    # Save to CSV
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    
    return True


def get_latest_update_for_product(
    updates_df: pd.DataFrame,
    product_id: str,
) -> Optional[Dict]:
    """
    Get the most recent update for a product.
    
    Args:
        updates_df: DataFrame from load_daily_market_updates
        product_id: Product ID to search for
        
    Returns:
        Dictionary of the latest update, or None if not found
    """
    if updates_df.empty:
        return None
    
    product_updates = updates_df[updates_df['product_id'] == product_id]
    if product_updates.empty:
        return None
    
    # Get most recent (last row)
    latest = product_updates.iloc[-1]
    return latest.to_dict()


def get_products_missing_update_today(
    products_df: pd.DataFrame,
    updates_df: pd.DataFrame,
    today: str = None,
) -> pd.DataFrame:
    """
    Get list of products that don't have an update today.
    
    Args:
        products_df: DataFrame from load_products_master
        updates_df: DataFrame from load_daily_market_updates
        today: Date string in format 'YYYY-MM-DD' (defaults to today)
        
    Returns:
        DataFrame of products with no update today (filtered by active=true)
    """
    if today is None:
        today = datetime.now().strftime('%Y-%m-%d')
    
    # Filter to active products
    active = products_df[products_df.get('active', True) == True].copy()
    
    if updates_df.empty:
        # All active products are missing updates
        return active
    
    # Check which products have updates today
    updates_df['date'] = pd.to_datetime(updates_df['observed_at']).dt.strftime('%Y-%m-%d')
    updated_today = set(updates_df[updates_df['date'] == today]['product_id'].unique())
    
    # Return products not in updated_today
    missing = active[~active['product_id'].isin(updated_today)]
    
    return missing
