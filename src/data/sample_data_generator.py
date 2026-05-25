"""Generate deterministic sample dataset for smartwatch pricing analysis."""

import numpy as np
import pandas as pd
from pathlib import Path


def generate_smartwatch_data(seed: int = 42, n_products: int = 30) -> pd.DataFrame:
    """
    Generate a deterministic sample dataset of smartwatch products (Phase 2 schema).
    
    Args:
        seed: Random seed for reproducibility
        n_products: Number of products to generate
    Returns:
        DataFrame with smartwatch product data (Phase 2 fields)
    """
    np.random.seed(seed)

    brands = ["Apple", "Samsung", "Xiaomi", "Haylou", "Kieslect", "Garmin", "Fitbit", "Fossil", "Amazfit"]
    models = ["Ultra", "Pro", "Sport", "Max", "Elite", "Basic", "Plus", "Active", "Lite"]
    categories = ["Budget", "Mid-Range", "Premium"]
    base_usd_price_sources = ["Amazon", "Official MSRP", "Manual Reference"]
    strategies = [
        "Trust Builder", "Balanced", "Profit Protection", "Market Penetration",
        "Premium Positioning", "Clearance / Cashflow"
    ]

    rows = []
    for i in range(n_products):
        brand = brands[i % len(brands)]
        model = models[i % len(models)]
        category = (
            "Premium" if brand == "Apple" or brand == "Garmin" else
            "Budget" if brand in ["Xiaomi", "Haylou", "Kieslect"] else
            np.random.choice(categories)
        )
        product_id = f"SW{str(i+1).zfill(3)}"
        product_name = f"{brand} {model}"
        base_usd_price = (
            np.random.uniform(350, 600) if category == "Premium" else
            np.random.uniform(100, 250) if category == "Mid-Range" else
            np.random.uniform(20, 90)
        )
        base_usd_price = round(base_usd_price, 2)
        base_usd_price_source = np.random.choice(base_usd_price_sources)
        usd_rate = float(np.random.randint(45000, 47000))
        theoretical_toman_price = round(base_usd_price * usd_rate)

        # Market price premium logic
        if brand == "Apple":
            market_premium_pct = np.random.uniform(0.25, 0.40)
            inventory = np.random.randint(5, 20)
        elif brand in ["Xiaomi", "Haylou", "Kieslect"]:
            market_premium_pct = np.random.uniform(0.05, 0.15)
            inventory = np.random.randint(40, 150)
        elif brand == "Samsung":
            market_premium_pct = np.random.uniform(0.12, 0.22)
            inventory = np.random.randint(20, 50)
        else:
            market_premium_pct = np.random.uniform(0.10, 0.20)
            inventory = np.random.randint(10, 40)

        market_median_price = int(theoretical_toman_price * (1 + market_premium_pct))
        market_min_price = int(market_median_price * np.random.uniform(0.95, 0.98))
        market_max_price = int(market_median_price * np.random.uniform(1.03, 1.08))
        market_avg_price = int((market_min_price + market_median_price + market_max_price) / 3)
        seller_count = np.random.randint(3, 12)
        available_seller_count = max(1, int(seller_count * np.random.uniform(0.7, 1.0)))
        torob_min_price = int(market_min_price * np.random.uniform(0.98, 1.01))
        torob_median_price = int(market_median_price * np.random.uniform(0.99, 1.01))
        digikala_price = int(market_median_price * np.random.uniform(0.98, 1.04))

        # Internal retailer demo fields
        our_cost_price = int(theoretical_toman_price * np.random.uniform(0.90, 0.98))
        our_target_margin = round(np.random.uniform(0.18, 0.38), 2)
        our_current_price = int(our_cost_price * (1 + our_target_margin + np.random.uniform(-0.03, 0.05)))
        our_current_price = max(our_current_price, our_cost_price + 10000)
        our_sales_7d = np.random.randint(2, 20) if inventory > 10 else np.random.randint(0, 5)
        our_sales_30d = our_sales_7d * np.random.randint(3, 6)
        our_strategy = np.random.choice(strategies)
        observed_at = pd.Timestamp("2026-05-25") + pd.Timedelta(days=i % 7)

        row = {
            "product_id": product_id,
            "product_name": product_name,
            "brand": brand,
            "model": model,
            "category": category,
            "base_usd_price": base_usd_price,
            "base_usd_price_source": base_usd_price_source,
            "usd_rate": usd_rate,
            "theoretical_toman_price": theoretical_toman_price,
            "market_min_price": market_min_price,
            "market_median_price": market_median_price,
            "market_max_price": market_max_price,
            "market_avg_price": market_avg_price,
            "seller_count": seller_count,
            "available_seller_count": available_seller_count,
            "torob_min_price": torob_min_price,
            "torob_median_price": torob_median_price,
            "digikala_price": digikala_price,
            "our_current_price": our_current_price,
            "our_cost_price": our_cost_price,
            "our_inventory": inventory,
            "our_sales_7d": our_sales_7d,
            "our_sales_30d": our_sales_30d,
            "our_target_margin": our_target_margin,
            "our_strategy": our_strategy,
            "observed_at": observed_at.strftime("%Y-%m-%d"),
        }

        # Deprecated/compatibility fields (not used in new logic)
        row["views_30d"] = 0  # Deprecated
        row["conversion_rate"] = 0.0  # Deprecated

        rows.append(row)

    df = pd.DataFrame(rows)
    return df


def save_sample_data(df: pd.DataFrame, output_path: str = None) -> Path:
    """
    Save sample data to CSV.
    
    Args:
        df: DataFrame to save
        output_path: Output file path (default: data/processed/smartwatch_sample_data.csv)
        
    Returns:
        Path to saved file
    """
    if output_path is None:
        output_path = "data/processed/smartwatch_sample_data.csv"
    
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    df.to_csv(output_file, index=False)
    return output_file


def load_sample_data(data_path: str = None) -> pd.DataFrame:
    """
    Load sample data from CSV.
    
    Args:
        data_path: Path to CSV file (default: data/processed/smartwatch_sample_data.csv)
        
    Returns:
        DataFrame with smartwatch data
    """
    if data_path is None:
        data_path = "data/processed/smartwatch_sample_data.csv"
    
    data_file = Path(data_path)
    
    if data_file.exists():
        return pd.read_csv(data_file)
    else:
        # Generate if not found
        df = generate_smartwatch_data()
        save_sample_data(df, str(data_file))
        return df


if __name__ == "__main__":
    # Generate and save sample data
    df = generate_smartwatch_data()
    save_path = save_sample_data(df)
    print(f"Sample data saved to: {save_path}")
    print(f"\nShape: {df.shape}")
    print(f"\nFirst few rows:\n{df.head()}")
    print(f"\nData types:\n{df.dtypes}")
