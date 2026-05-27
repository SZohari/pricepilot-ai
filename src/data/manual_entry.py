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
import math
import re
import unicodedata

from src.utils.formatting import parse_price_input


VALID_PRODUCT_STRATEGIES = {
    'trust_builder',
    'balanced',
    'profit_protection',
    'market_penetration',
    'premium_positioning',
    'clearance_cashflow',
}


def generate_product_id(brand: str, model: str) -> str:
    """Create a stable uppercase hyphenated identifier from brand and model."""
    text = f"{brand or ''} {model or ''}"
    ascii_text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    normalized = re.sub(r'[^A-Za-z0-9]+', '-', ascii_text).strip('-')
    return normalized.upper()


def product_id_exists(
    product_id: str,
    products_df: pd.DataFrame,
    retailer_df: pd.DataFrame,
    usd_df: pd.DataFrame,
) -> bool:
    """Check whether an identifier is already used in any product source file."""
    for df in (products_df, retailer_df, usd_df):
        if 'product_id' in df.columns and product_id in set(df['product_id'].astype(str)):
            return True
    return False


def validate_new_product_payload(payload: Dict) -> Tuple[bool, List[str]]:
    """Validate form values before a product is appended to raw data files."""
    issues = []
    for field in ['brand', 'model', 'product_name', 'product_query']:
        if not str(payload.get(field, '')).strip():
            issues.append(f"{field} is required")

    if not str(payload.get('product_id', '')).strip():
        issues.append("product_id could not be generated from brand and model")

    current_price = parse_price_input(payload.get('our_current_price'))
    cost_price = parse_price_input(payload.get('our_cost_price'))
    usd_rate = parse_price_input(payload.get('usd_rate'))
    if current_price is None or current_price <= 0:
        issues.append("our_current_price must be positive")
    if cost_price is None or cost_price <= 0:
        issues.append("our_cost_price must be positive")
    if current_price is not None and cost_price is not None and current_price <= cost_price:
        issues.append("our_current_price must be greater than our_cost_price")
    if usd_rate is None or usd_rate <= 0:
        issues.append("usd_rate must be positive")

    try:
        if int(payload.get('our_inventory')) < 0:
            issues.append("our_inventory must be >= 0")
    except (TypeError, ValueError):
        issues.append("our_inventory must be >= 0")

    try:
        margin = float(payload.get('our_target_margin'))
        if not math.isfinite(margin) or not 0 <= margin <= 1:
            issues.append("our_target_margin must be between 0 and 1")
    except (TypeError, ValueError):
        issues.append("our_target_margin must be between 0 and 1")

    if payload.get('our_strategy') not in VALID_PRODUCT_STRATEGIES:
        issues.append("our_strategy is invalid")

    try:
        base_usd_price = float(payload.get('base_usd_price'))
        if not math.isfinite(base_usd_price) or base_usd_price <= 0:
            issues.append("base_usd_price must be positive")
    except (TypeError, ValueError):
        issues.append("base_usd_price must be positive")

    return (len(issues) == 0, issues)


def append_new_product(
    products_path: str,
    retailer_path: str,
    usd_path: str,
    payload: Dict,
) -> str:
    """Append a validated new product across catalog, retailer, and USD sources."""
    is_valid, issues = validate_new_product_payload(payload)
    if not is_valid:
        raise ValueError("New product validation failed:\n" + "\n".join(issues))

    products_df = pd.read_csv(products_path)
    retailer_df = pd.read_csv(retailer_path)
    usd_df = pd.read_csv(usd_path)
    product_id = payload['product_id']
    if product_id_exists(product_id, products_df, retailer_df, usd_df):
        raise ValueError(f"product_id already exists: {product_id}")

    products_row = {
        'product_id': product_id,
        'brand': payload['brand'].strip(),
        'model': payload['model'].strip(),
        'product_name': payload['product_name'].strip(),
        'product_query': payload['product_query'].strip(),
        'torob_url': payload.get('torob_url', ''),
        'digikala_url': payload.get('digikala_url', ''),
        'global_reference_url': payload.get('global_reference_url', ''),
        'priority': payload.get('priority', 'medium'),
        'active': bool(payload.get('active', True)),
        'notes': payload.get('catalog_notes', ''),
    }
    retailer_row = {
        'product_id': product_id,
        'our_current_price': parse_price_input(payload['our_current_price']),
        'our_cost_price': parse_price_input(payload['our_cost_price']),
        'our_inventory': int(payload['our_inventory']),
        'our_sales_7d': int(payload.get('our_sales_7d', 0)),
        'our_sales_30d': int(payload.get('our_sales_30d', 0)),
        'our_target_margin': float(payload['our_target_margin']),
        'our_strategy': payload['our_strategy'],
    }
    usd_row = {
        'product_id': product_id,
        'brand': payload['brand'].strip(),
        'model': payload['model'].strip(),
        'base_usd_price': float(payload['base_usd_price']),
        'base_usd_price_source': payload.get('base_usd_price_source', ''),
        'usd_rate': parse_price_input(payload['usd_rate']),
        'source_url': payload.get('source_url', ''),
        'observed_at': payload.get('observed_at', datetime.now().strftime('%Y-%m-%d')),
        'notes': payload.get('usd_notes', ''),
    }

    products_df = pd.concat([products_df, pd.DataFrame([products_row])], ignore_index=True)
    retailer_df = pd.concat([retailer_df, pd.DataFrame([retailer_row])], ignore_index=True)
    usd_df = pd.concat([usd_df, pd.DataFrame([usd_row])], ignore_index=True)
    products_df.to_csv(products_path, index=False)
    retailer_df.to_csv(retailer_path, index=False)
    usd_df.to_csv(usd_path, index=False)
    return product_id


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
    
    # rate_toman is required and must parse to a positive integer toman value.
    parsed_rate = parse_price_input(fx_dict.get('rate_toman'))
    if parsed_rate is None:
        issues.append("rate_toman is required")
    elif parsed_rate <= 0:
        issues.append("rate_toman must be positive")
    
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
    parsed_rate = parse_price_input(fx_dict.get('rate_toman'))

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
        'rate_toman': parsed_rate,
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
    
    ordered = product_updates.copy()
    ordered['_row_order'] = range(len(ordered))
    ordered['_observed_at'] = pd.to_datetime(ordered['observed_at'], errors='coerce')
    ordered = ordered.sort_values(
        ['_observed_at', '_row_order'],
        kind='stable',
        na_position='first',
    )
    latest = ordered.iloc[-1].drop(labels=['_row_order', '_observed_at'])
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
