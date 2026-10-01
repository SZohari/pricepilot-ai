"""Presentation helpers only; domain objects retain exact decimal amounts."""
import pandas as pd
from src.domain.models import Recommendation


def money(value) -> str:
    return "Unavailable" if value is None else f"EUR {value:,.2f}"


def decision_table(results: list[Recommendation]) -> pd.DataFrame:
    return pd.DataFrame([{
        "Product": r.product_name,
        "Current EUR": float(r.current_price_gross),
        "Proposed EUR": float(r.recommended_price_gross) if r.recommended_price_gross is not None else None,
        "Contribution margin %": float(r.expected_margin * 100) if r.expected_margin is not None else None,
        "Action": r.action.replace("_", " ").title(),
        "Data quality": r.quality.status.title(),
        "Fresh sellers": r.quality.usable_sellers,
        "Review": r.requires_review,
    } for r in results])
