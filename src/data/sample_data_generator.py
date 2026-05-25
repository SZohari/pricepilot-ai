"""Generate deterministic sample dataset for smartwatch pricing analysis."""

import numpy as np
import pandas as pd
from pathlib import Path


def generate_smartwatch_data(seed: int = 42, n_products: int = 30) -> pd.DataFrame:
    """
    Generate a deterministic sample dataset of smartwatch products.
    
    Args:
        seed: Random seed for reproducibility
        n_products: Number of products to generate
        
    Returns:
        DataFrame with smartwatch product data
    """
    np.random.seed(seed)
    
    brands = ["Fitbit", "Garmin", "Samsung", "Apple", "Xiaomi", "Huawei", "Fossil"]
    models = ["Sport", "Pro", "Ultra", "Basic", "Elite", "Plus", "Max"]
    categories = ["Budget", "Mid-Range", "Premium"]
    
    data = {
        "product_id": [f"SW{str(i+1).zfill(3)}" for i in range(n_products)],
        "product_name": [f"{brands[i % len(brands)]} {models[i % len(models)]}" 
                         for i in range(n_products)],
        "brand": [brands[i % len(brands)] for i in range(n_products)],
        "model": [models[i % len(models)] for i in range(n_products)],
        "category": np.random.choice(categories, n_products),
        "current_price": np.random.randint(800_000, 5_000_000, n_products).astype(float),
        "cost_price": np.random.randint(400_000, 3_000_000, n_products).astype(float),
        "inventory": np.random.randint(5, 200, n_products),
        "competitor_min_price": np.random.randint(700_000, 4_800_000, n_products).astype(float),
        "competitor_median_price": np.random.randint(750_000, 5_000_000, n_products).astype(float),
        "competitor_max_price": np.random.randint(900_000, 5_500_000, n_products).astype(float),
        "usd_rate": np.random.randint(40_000, 50_000, n_products).astype(float),
        "usd_change_7d": np.random.uniform(-5, 8, n_products),
        "sales_7d": np.random.randint(0, 50, n_products),
        "sales_30d": np.random.randint(5, 150, n_products),
        "views_30d": np.random.randint(50, 1500, n_products),
        "conversion_rate": np.random.uniform(0.01, 0.15, n_products),
        "target_margin": np.random.uniform(0.15, 0.40, n_products),
        "supplier_lead_time_days": np.random.randint(3, 45, n_products),
    }
    
    df = pd.DataFrame(data)
    
    # Ensure competitor prices are reasonable
    for idx, row in df.iterrows():
        current = row["current_price"]
        df.at[idx, "competitor_min_price"] = float(min(row["competitor_min_price"], current + 100_000))
        df.at[idx, "competitor_max_price"] = float(max(row["competitor_max_price"], current + 200_000))
        df.at[idx, "competitor_median_price"] = float(
            df.at[idx, "competitor_min_price"] + 
            (df.at[idx, "competitor_max_price"] - df.at[idx, "competitor_min_price"]) / 2
        )
    
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
