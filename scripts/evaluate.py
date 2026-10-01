"""Reproducible policy evaluation; these diagnostics are not causal business uplift."""
import argparse
from decimal import Decimal
import json
from pathlib import Path
from src.application.service import demo_service, load_demo
from src.domain.models import Scenario, Strategy


def evaluate() -> dict:
    service = demo_service()
    dataset = load_demo()
    products = {p.product_id: p for p in dataset.products}
    rows = []
    for strategy in Strategy:
        for shock in [0, 10, 30]:
            results = service.recommendations(Scenario(as_of=dataset.as_of, strategy=strategy, cost_change_pct=shock))
            priced = [r for r in results if r.recommended_price_gross is not None]
            rows.append({
                "strategy": strategy.value, "cost_change_pct": shock,
                "products": len(results), "priced_products": len(priced),
                "blocked_products": len(results) - len(priced),
                "review_required": sum(r.requires_review for r in results),
                "current_price_floor_breaches": sum(r.current_price_gross < r.floor_price_gross for r in results),
                "proposed_price_floor_breaches": sum(r.recommended_price_gross < r.floor_price_gross for r in priced),
                "mean_expected_contribution_margin": round(float(sum(r.expected_margin for r in priced) / len(priced)), 4),
                "target_margin_achieved": sum(r.expected_margin >= products[r.product_id].target_margin for r in priced),
                "mean_absolute_price_change_pct": round(float(sum(abs(r.recommended_price_gross / r.current_price_gross - 1)
                                                               for r in priced) / len(priced) * 100), 2),
            })
    service.repository.close()
    assert all(row["proposed_price_floor_breaches"] == 0 for row in rows)
    return {
        "dataset": dataset.name, "as_of": str(dataset.as_of), "policy_version": "eur-retail-1",
        "evidence": "Synthetic scenario; no measured demand, revenue or profit uplift.",
        "limitations": ["No elasticity model", "No causal experiment", "No live German market feed"],
        "results": rows,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = json.dumps(evaluate(), indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result + "\n", encoding="utf-8")
    else:
        print(result)


if __name__ == "__main__":
    main()
