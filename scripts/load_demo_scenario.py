"""Load the Iranian smartwatch demo scenario into data/raw."""

from argparse import ArgumentParser
from pathlib import Path
import shutil
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.build_pricing_dataset import (
    build_dashboard_pricing_dataset,
    load_global_usd_reference,
    load_market_observations,
    load_retailer_internal_data,
    save_dashboard_pricing_dataset,
)
from src.data.manual_entry import (
    load_daily_market_updates,
    load_fx_rate_snapshots,
    load_products_master,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SCENARIO_DIR = PROJECT_ROOT / "data" / "scenarios" / "iran_smartwatch_demo_20"
DEFAULT_RAW_DIR = PROJECT_ROOT / "data" / "raw"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "dashboard_pricing_data.csv"

SCENARIO_FILES = [
    "products_master.csv",
    "retailer_internal_demo_template.csv",
    "global_usd_reference_template.csv",
    "market_observations_template.csv",
    "fx_rate_snapshots.csv",
]

DAILY_UPDATES_HEADER = (
    "update_id,observed_at,product_id,torob_min_price,torob_median_price,"
    "digikala_price,market_max_price,availability_note,notes\n"
)


def copy_demo_scenario(
    scenario_dir: Path = DEFAULT_SCENARIO_DIR,
    raw_dir: Path = DEFAULT_RAW_DIR,
) -> dict[str, Path]:
    """Copy scenario CSV files into a raw data directory."""
    scenario_dir = Path(scenario_dir)
    raw_dir = Path(raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)

    copied = {}
    for file_name in SCENARIO_FILES:
        source = scenario_dir / file_name
        if not source.exists():
            raise FileNotFoundError(f"Scenario file not found: {source}")
        destination = raw_dir / file_name
        shutil.copyfile(source, destination)
        copied[file_name] = destination

    daily_updates_path = raw_dir / "daily_market_updates.csv"
    daily_updates_path.write_text(DAILY_UPDATES_HEADER, encoding="utf-8")
    copied["daily_market_updates.csv"] = daily_updates_path
    return copied


def build_from_raw_dir(raw_dir: Path, output_path: Path) -> pd.DataFrame:
    """Build the processed dataset from a raw data directory."""
    raw_dir = Path(raw_dir)
    output_path = Path(output_path)

    market = load_market_observations(str(raw_dir / "market_observations_template.csv"))
    retailer = load_retailer_internal_data(str(raw_dir / "retailer_internal_demo_template.csv"))
    usd = load_global_usd_reference(str(raw_dir / "global_usd_reference_template.csv"))
    daily_updates = load_daily_market_updates(str(raw_dir / "daily_market_updates.csv"))
    fx_snapshots = load_fx_rate_snapshots(str(raw_dir / "fx_rate_snapshots.csv"))
    products = load_products_master(str(raw_dir / "products_master.csv"))

    result = build_dashboard_pricing_dataset(
        market,
        retailer,
        usd,
        daily_updates_df=daily_updates,
        fx_snapshots_df=fx_snapshots,
        products_df=products,
    )
    save_dashboard_pricing_dataset(result, str(output_path))
    return result


def parse_args() -> ArgumentParser:
    """Build the command-line parser."""
    parser = ArgumentParser(description="Load the PricePilot AI demo scenario.")
    parser.add_argument("--scenario-dir", type=Path, default=DEFAULT_SCENARIO_DIR)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--output-path", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--no-build", action="store_true", help="Copy raw files without rebuilding processed data.")
    return parser


def main() -> int:
    """Copy scenario data and optionally build the processed dataset."""
    args = parse_args().parse_args()
    copy_demo_scenario(args.scenario_dir, args.raw_dir)

    products = pd.read_csv(args.raw_dir / "products_master.csv")
    market = pd.read_csv(args.raw_dir / "market_observations_template.csv")
    output_path = args.output_path

    if not args.no_build:
        build_from_raw_dir(args.raw_dir, output_path)

    print("scenario loaded")
    print(f"number of products: {len(products)}")
    print(f"number of market observations: {len(market)}")
    print(f"output path: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
