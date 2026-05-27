"""
Script to build dashboard-ready pricing dataset from raw market observations.

Reads:
- data/raw/market_observations_template.csv
- data/raw/retailer_internal_demo_template.csv
- data/raw/global_usd_reference_template.csv

Outputs:
- data/processed/dashboard_pricing_data.csv
"""

from pathlib import Path
import sys

# Add parent directory to path so we can import src
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.build_pricing_dataset import (
    load_market_observations,
    load_retailer_internal_data,
    load_global_usd_reference,
    build_dashboard_pricing_dataset,
    save_dashboard_pricing_dataset,
)
from src.data.manual_entry import load_products_master, load_daily_market_updates, load_fx_rate_snapshots


def main():
    """Build and save the dashboard pricing dataset."""
    
    print("=" * 70)
    print("Building Dashboard Pricing Dataset")
    print("=" * 70)
    print()
    
    try:
        # Load raw data
        print("📥 Loading raw data...")
        market_obs = load_market_observations('data/raw/market_observations_template.csv')
        print(f"   ✓ Market observations: {len(market_obs)} rows")
        
        retailer_data = load_retailer_internal_data('data/raw/retailer_internal_demo_template.csv')
        print(f"   ✓ Retailer internal data: {len(retailer_data)} rows")
        
        usd_ref = load_global_usd_reference('data/raw/global_usd_reference_template.csv')
        print(f"   ✓ USD reference: {len(usd_ref)} rows")

        daily_updates = load_daily_market_updates('data/raw/daily_market_updates.csv')
        print(f"   ✓ Daily market updates: {len(daily_updates)} rows")

        fx_snapshots = load_fx_rate_snapshots('data/raw/fx_rate_snapshots.csv')
        print(f"   ✓ FX snapshots: {len(fx_snapshots)} rows")

        products = load_products_master('data/raw/products_master.csv')
        print(f"   ✓ Product catalog: {len(products)} rows")
        
        print()
        
        # Build dataset
        print("🔨 Building dashboard dataset...")
        dashboard_data = build_dashboard_pricing_dataset(
            market_obs,
            retailer_data,
            usd_ref,
            daily_updates_df=daily_updates,
            fx_snapshots_df=fx_snapshots,
            products_df=products,
        )
        print(f"   ✓ Products aggregated: {len(dashboard_data)}")
        
        print()
        
        # Save dataset
        print("💾 Saving dataset...")
        output_path = save_dashboard_pricing_dataset(dashboard_data)
        print(f"   ✓ Saved to: {output_path}")
        
        print()
        
        # Summary
        print("📊 Dataset Summary")
        print(f"   Products: {len(dashboard_data)}")
        print(f"   Columns: {len(dashboard_data.columns)}")
        print(f"   Output file: {output_path}")
        
        print()
        print("Column List:")
        for i, col in enumerate(dashboard_data.columns, 1):
            print(f"   {i:2d}. {col}")
        
        print()
        print("✅ Build successful!")
        print("=" * 70)
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {str(e)}", flush=True)
        print("=" * 70)
        return 1


if __name__ == "__main__":
    exit(main())
