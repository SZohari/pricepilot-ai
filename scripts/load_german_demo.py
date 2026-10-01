"""Explicitly initialize a local workspace; importing twice is a conflict, never a reset."""
import argparse
from src.application.service import load_demo
from src.infrastructure.repository import SQLiteRepository


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", default="data/workspaces/pricepilot.sqlite3")
    args = parser.parse_args()
    repository = SQLiteRepository(args.database)
    try:
        repository.import_dataset(load_demo())
        print(f"Imported 20 synthetic products into {args.database}")
    finally:
        repository.close()


if __name__ == "__main__":
    main()
