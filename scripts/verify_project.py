#!/usr/bin/env python
"""Safe verification script for PricePilot AI project."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def main():
    """Verify project setup without modifications."""
    print("=" * 60)
    print("PricePilot AI - Project Verification")
    print("=" * 60)
    print()
    
    # Test 1: Import utilities
    print("1. Testing imports...")
    try:
        from src.utils.formatting import format_toman, format_margin
        print("   ✓ src.utils.formatting")
    except Exception as e:
        print(f"   ✗ src.utils.formatting: {e}")
        return False
    
    try:
        from src.utils.validation import validate_csv_columns
        print("   ✓ src.utils.validation")
    except Exception as e:
        print(f"   ✗ src.utils.validation: {e}")
        return False
    
    try:
        from src.data.sample_data_generator import load_sample_data
        print("   ✓ src.data.sample_data_generator")
    except Exception as e:
        print(f"   ✗ src.data.sample_data_generator: {e}")
        return False
    
    try:
        from src.pricing.recommendation import recommend_price
        print("   ✓ src.pricing.recommendation")
    except Exception as e:
        print(f"   ✗ src.pricing.recommendation: {e}")
        return False
    
    try:
        import streamlit
        print("   ✓ streamlit")
    except Exception as e:
        print(f"   ✗ streamlit: {e}")
        return False
    
    print()
    
    # Test 2: Load sample data
    print("2. Loading sample data...")
    try:
        df = load_sample_data()
        print(f"   ✓ Loaded {len(df)} products")
    except Exception as e:
        print(f"   ✗ Failed to load data: {e}")
        return False
    
    print()
    
    # Test 3: Generate recommendation
    print("3. Generating recommendation...")
    try:
        product = df.iloc[0].to_dict()
        rec = recommend_price(product, usd_shock=0.0)
        print(f"   ✓ Product: {rec['product_name']}")
        print(f"   ✓ Action: {rec['action']}")
        print(f"   ✓ Risk: {rec['risk_level']}")
    except Exception as e:
        print(f"   ✗ Failed to generate recommendation: {e}")
        return False
    
    print()
    
    # Test 4: Test formatting
    print("4. Testing formatting...")
    try:
        formatted_price = format_toman(7800000)
        formatted_margin = format_margin(0.35)
        print(f"   ✓ format_toman(7800000) = {formatted_price}")
        print(f"   ✓ format_margin(0.35) = {formatted_margin}")
    except Exception as e:
        print(f"   ✗ Formatting failed: {e}")
        return False
    
    print()
    print("=" * 60)
    print("✅ All verifications passed!")
    print("=" * 60)
    print()
    print("Dashboard is ready to run:")
    print("  streamlit run src/dashboard/app.py")
    print()
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
