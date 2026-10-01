"""Write reproducible benchmark evidence, including failure and multiple seeds."""
import argparse
import json
from pathlib import Path
from src.application.demand_demo import synthetic_history
from src.domain.demand import evaluate


def report():
    results = []
    for seed in (11, 29, 47, 73, 101):
        for shock in (False, True):
            result = evaluate(synthetic_history(seed=seed, shock=shock))
            results.append({"seed": seed, "shock": shock, **result})
    return {"purpose": "Synthetic method benchmark; not evidence of merchant ROI",
            "protocol": "Fixed seeds, no random split; train/validation/calibration/test in time order",
            "results": results}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='docs/demand-evaluation.json')
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report(), indent=2, allow_nan=False)+'\n', encoding='utf-8')
    print(output)
