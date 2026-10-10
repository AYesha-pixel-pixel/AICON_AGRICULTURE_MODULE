from __future__ import annotations

import argparse
from pathlib import Path

from src.evaluation import (
    ManifestError,
    evaluate_manifest,
    write_results,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate CropSaathi on a labelled local image manifest."
    )
    parser.add_argument(
        "--manifest",
        required=True,
        help="CSV manifest with image_path, ground_truth_label, selected_crop, split.",
    )
    parser.add_argument(
        "--split",
        default="evaluation",
        choices=("train", "validation", "evaluation", "test"),
        help="Explicit manifest split to evaluate; defaults to held-out evaluation.",
    )
    parser.add_argument(
        "--json",
        default="evaluation_results.json",
        help="Machine-readable JSON summary output.",
    )
    parser.add_argument(
        "--csv",
        default="evaluation_samples.csv",
        help="Machine-readable per-sample CSV output.",
    )
    args = parser.parse_args()

    try:
        result = evaluate_manifest(args.manifest, split=args.split)
        write_results(result, json_path=args.json, csv_path=args.csv)
    except (ManifestError, ValueError) as error:
        parser.error(str(error))

    print(f"Manifest: {Path(args.manifest).resolve()}")
    print(f"Split: {result['split']}")
    print(f"Total samples: {result['total_samples']}")
    print(f"Valid samples: {result['valid_samples']}")
    print(f"Invalid samples: {result['invalid_samples']}")
    print(f"Top-1 accuracy: {result['metrics']['top1_accuracy']:.4f}")
    print(
        "Decision-rule counts: "
        f"rejected={result['rejected_by_decision_rules']}, "
        f"uncertain={result['uncertain_by_decision_rules']}"
    )
    print(f"JSON summary: {Path(args.json).resolve()}")
    print(f"Sample CSV: {Path(args.csv).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
