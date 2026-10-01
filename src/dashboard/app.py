"""Default EUR workspace; historical helpers are loaded only for compatibility callers."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.dashboard.retail_app import main


def __getattr__(name):
    if name in {"prepare_demo_dataset", "processed_dataset_is_ready",
                "DEFAULT_PUBLIC_DATA_SOURCE", "PUBLIC_DATA_SOURCE_OPTIONS"}:
        from src.dashboard import legacy
        return getattr(legacy, name)
    raise AttributeError(name)


if __name__ == "__main__":
    main()
