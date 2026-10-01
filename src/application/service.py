"""Application boundary: adapters supply storage; the domain supplies decisions."""
from collections import defaultdict
from datetime import date
from pathlib import Path
from src.domain.models import Dataset, Recommendation, Scenario
from src.domain.pricing import recommend
from src.infrastructure.repository import Repository, SQLiteRepository

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEMO_PATH = PROJECT_ROOT / "data/scenarios/germany_wearables/demo.json"


class PricingService:
    def __init__(self, repository: Repository):
        self.repository = repository

    def recommendations(self, scenario: Scenario) -> list[Recommendation]:
        products, observations = self.repository.snapshot()
        by_product = defaultdict(list)
        for observation in observations:
            by_product[observation.product_id].append(observation)
        return [recommend(entry.product, by_product[entry.product.product_id], scenario) for entry in products]

    def export_dataset(self, as_of: date) -> Dataset:
        products, observations = self.repository.snapshot()
        return Dataset(name="PricePilot workspace export", as_of=as_of,
                       products=[entry.product for entry in products], observations=observations)


def load_demo() -> Dataset:
    return Dataset.model_validate_json(DEMO_PATH.read_text(encoding="utf-8"))


def demo_service() -> PricingService:
    """Fresh isolated demo; never reads or overwrites a user's workspace."""
    repository = SQLiteRepository()
    repository.import_dataset(load_demo())
    return PricingService(repository)
