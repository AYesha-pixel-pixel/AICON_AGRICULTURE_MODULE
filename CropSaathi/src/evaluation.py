from __future__ import annotations

import csv
import json
import math
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any, Iterable

from src.config import ALLOWED_EXTENSIONS, SUPPORTED_CROPS
from src.decision_rules import decide
from src.image_validation import validate_image
from src.model_service import ModelService, ModelServiceError, load_model


REQUIRED_MANIFEST_COLUMNS = {
    "image_path",
    "ground_truth_label",
    "selected_crop",
    "split",
}
VALID_SPLITS = {"train", "validation", "evaluation", "test"}
APPLICATION_SUPPORTED_LABELS = {
    "Corn___Common_Rust",
    "Corn___Gray_Leaf_Spot",
    "Rice___Brown_Spot",
    "Rice___Leaf_Blast",
    "Wheat___Brown_Rust",
    "Wheat___Yellow_Rust",
}
KNOWN_MODEL_LABELS = {
    "Corn___Common_Rust",
    "Corn___Gray_Leaf_Spot",
    "Corn___Healthy",
    "Invalid",
    "Potato___Early_Blight",
    "Potato___Healthy",
    "Potato___Late_Blight",
    "Rice___Brown_Spot",
    "Rice___Healthy",
    "Rice___Leaf_Blast",
    "Wheat___Brown_Rust",
    "Wheat___Healthy",
    "Wheat___Yellow_Rust",
}


class ManifestError(ValueError):
    """Raised when an evaluation manifest is missing or invalid."""


def _normalise_crop(value: str) -> str:
    return value.strip().lower()


def _manifest_path(raw_path: str, manifest_path: Path) -> Path:
    candidate = Path(raw_path).expanduser()
    if not candidate.is_absolute():
        candidate = manifest_path.parent / candidate
    return candidate.resolve()


def _read_manifest(manifest_path: Path) -> list[dict[str, str]]:
    if not manifest_path.is_file():
        raise ManifestError(f"Manifest does not exist: {manifest_path}")
    try:
        with manifest_path.open(newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)
            fieldnames = set(reader.fieldnames or [])
            missing = REQUIRED_MANIFEST_COLUMNS - fieldnames
            if missing:
                names = ", ".join(sorted(missing))
                raise ManifestError(f"Manifest is missing columns: {names}")
            return [
                {key: (value or "").strip() for key, value in row.items()}
                for row in reader
            ]
    except UnicodeDecodeError as error:
        raise ManifestError("Manifest must be UTF-8 encoded CSV.") from error


def validate_manifest(
    manifest_path: str | Path,
    *,
    split: str = "evaluation",
    allowed_labels: Iterable[str] | None = None,
) -> list[dict[str, str]]:
    """Validate and return rows for one explicitly selected dataset split."""
    if split not in VALID_SPLITS:
        raise ManifestError(f"Unsupported split '{split}'.")

    path = Path(manifest_path).expanduser().resolve()
    rows = _read_manifest(path)
    known_labels = set(
        KNOWN_MODEL_LABELS if allowed_labels is None else allowed_labels
    )
    selected_rows = []
    for line_number, row in enumerate(rows, start=2):
        image_path = row.get("image_path", "")
        label = row.get("ground_truth_label", "")
        crop = _normalise_crop(row.get("selected_crop", ""))
        row_split = row.get("split", "").lower()
        if not image_path or not label or not crop or not row_split:
            raise ManifestError(f"Manifest row {line_number} has an empty field.")
        if row_split not in VALID_SPLITS:
            raise ManifestError(
                f"Manifest row {line_number} has invalid split '{row_split}'."
            )
        if row_split != split:
            continue
        if label not in known_labels:
            raise ManifestError(
                f"Manifest row {line_number} has unsupported label '{label}'."
            )
        if crop not in SUPPORTED_CROPS:
            raise ManifestError(
                f"Manifest row {line_number} has unsupported crop '{crop}'."
            )
        resolved_image = _manifest_path(image_path, path)
        if not resolved_image.is_file():
            raise ManifestError(
                f"Manifest row {line_number} references a missing image: "
                f"{image_path}"
            )
        if resolved_image.suffix.lower().lstrip(".") not in ALLOWED_EXTENSIONS:
            raise ManifestError(
                f"Manifest row {line_number} uses an unsupported image format: "
                f"{image_path}"
            )
        selected_rows.append(
            {
                "image_path": str(resolved_image),
                "ground_truth_label": label,
                "selected_crop": crop,
                "split": row_split,
            }
        )

    if not selected_rows:
        raise ManifestError(
            f"Manifest contains no rows for the '{split}' split."
        )
    return selected_rows


def _f1(precision: float, recall: float) -> float:
    return (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )


def calculate_metrics(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate classification metrics from successful inference records."""
    if not records:
        raise ValueError("Cannot calculate metrics for an empty evaluation set.")

    labels = sorted(
        {
            str(record["ground_truth_label"])
            for record in records
        }
        | {str(record["predicted_label"]) for record in records}
    )
    actual = Counter(str(record["ground_truth_label"]) for record in records)
    predicted = Counter(str(record["predicted_label"]) for record in records)
    correct = sum(
        record["ground_truth_label"] == record["predicted_label"]
        for record in records
    )
    per_class = {}
    confusion_matrix = {label: {other: 0 for other in labels} for label in labels}
    for record in records:
        truth = str(record["ground_truth_label"])
        guess = str(record["predicted_label"])
        confusion_matrix[truth][guess] += 1

    for label in labels:
        true_positive = sum(
            record["ground_truth_label"] == label
            and record["predicted_label"] == label
            for record in records
        )
        precision = (
            true_positive / predicted[label] if predicted[label] else 0.0
        )
        recall = true_positive / actual[label] if actual[label] else 0.0
        per_class[label] = {
            "support": actual[label],
            "precision": precision,
            "recall": recall,
            "f1": _f1(precision, recall),
        }

    return {
        "sample_count": len(records),
        "top1_accuracy": correct / len(records),
        "per_class": per_class,
        "confusion_matrix": {
            "labels": labels,
            "counts": confusion_matrix,
        },
    }


def _model_labels(service: Any) -> list[str] | None:
    mapping = getattr(getattr(service, "model", None), "config", None)
    mapping = getattr(mapping, "id2label", None)
    if not isinstance(mapping, dict):
        return None
    labels = [value for value in mapping.values() if isinstance(value, str)]
    return sorted(set(labels))


def _model_compatibility(service: Any) -> dict[str, Any]:
    labels = _model_labels(service)
    if labels is None:
        return {
            "model_labels_available": False,
            "model_labels": [],
            "unsupported_model_classes": [],
            "model_classes_for_unsupported_crops": [],
            "application_labels_missing_from_model": [],
        }
    unsupported = sorted(
        label for label in labels if label not in APPLICATION_SUPPORTED_LABELS
    )
    unsupported_crops = sorted(
        label
        for label in labels
        if "___" in label
        and label.split("___", 1)[0].lower() not in SUPPORTED_CROPS
    )
    return {
        "model_labels_available": True,
        "model_labels": labels,
        "unsupported_model_classes": unsupported,
        "model_classes_for_unsupported_crops": unsupported_crops,
        "application_labels_missing_from_model": sorted(
            APPLICATION_SUPPORTED_LABELS - set(labels)
        ),
    }


def _raw_score_statistics(records: list[dict[str, Any]]) -> dict[str, Any]:
    scores = [
        float(record["model_score"])
        for record in records
        if isinstance(record.get("model_score"), (int, float))
        and not isinstance(record.get("model_score"), bool)
        and math.isfinite(record["model_score"])
    ]
    if not scores:
        return {"sample_count": 0}
    return {
        "sample_count": len(scores),
        "minimum": min(scores),
        "maximum": max(scores),
        "mean": mean(scores),
        "note": "Raw model scores only; calibration was not evaluated.",
    }


def evaluate_manifest(
    manifest_path: str | Path,
    *,
    model_service: ModelService | None = None,
    split: str = "evaluation",
) -> dict[str, Any]:
    """Evaluate a labelled local manifest without tuning model thresholds."""
    rows = validate_manifest(
        manifest_path,
        split=split,
        allowed_labels=None,
    )
    service = model_service or load_model()
    successful_records = []
    sample_records = []
    invalid_samples = 0
    rejected_count = 0
    uncertain_count = 0

    for row in rows:
        image_path = Path(row["image_path"])
        try:
            with image_path.open("rb") as image_file:
                validation = validate_image(image_file)
        except OSError as error:
            validation = {
                "ok": False,
                "reason": f"Could not read image: {error}",
                "image": None,
            }

        if not validation["ok"] or validation["image"] is None:
            invalid_samples += 1
            sample_records.append(
                {
                    **row,
                    "status": "invalid_image",
                    "reason": validation["reason"],
                }
            )
            continue

        try:
            prediction = service.predict(validation["image"])
        except ModelServiceError as error:
            invalid_samples += 1
            sample_records.append(
                {**row, "status": "inference_error", "reason": str(error)}
            )
            continue

        decision = decide(prediction, row["selected_crop"])
        decision_name = decision["decision"]
        if decision_name == "uncertain":
            uncertain_count += 1
        elif decision_name != "usable":
            rejected_count += 1
        record = {
            **row,
            "status": "evaluated",
            "predicted_label": prediction["label"],
            "predicted_crop": prediction.get("crop"),
            "model_score": prediction["model_score"],
            "decision": decision_name,
        }
        successful_records.append(record)
        sample_records.append(record)

    if not successful_records:
        raise ValueError("No valid samples were available for evaluation.")

    metrics = calculate_metrics(successful_records)
    compatibility = _model_compatibility(service)
    compatibility["predicted_unsupported_classes"] = sorted(
        {
            record["predicted_label"]
            for record in successful_records
            if record["predicted_label"] not in APPLICATION_SUPPORTED_LABELS
        }
    )
    return {
        "manifest": str(Path(manifest_path).expanduser().resolve()),
        "split": split,
        "total_samples": len(rows),
        "valid_samples": len(successful_records),
        "invalid_samples": invalid_samples,
        "rejected_by_decision_rules": rejected_count,
        "uncertain_by_decision_rules": uncertain_count,
        "metrics": metrics,
        "raw_model_score_statistics": _raw_score_statistics(successful_records),
        "model_compatibility": compatibility,
        "samples": sample_records,
    }


def write_results(
    result: dict[str, Any],
    *,
    json_path: str | Path,
    csv_path: str | Path,
) -> None:
    """Write a JSON summary and a machine-readable per-sample CSV."""
    json_target = Path(json_path)
    csv_target = Path(csv_path)
    json_target.parent.mkdir(parents=True, exist_ok=True)
    csv_target.parent.mkdir(parents=True, exist_ok=True)
    with json_target.open("w", encoding="utf-8") as file:
        json.dump(result, file, indent=2)

    fields = [
        "image_path",
        "ground_truth_label",
        "selected_crop",
        "split",
        "status",
        "predicted_label",
        "predicted_crop",
        "model_score",
        "decision",
        "reason",
    ]
    with csv_target.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for sample in result["samples"]:
            writer.writerow({field: sample.get(field, "") for field in fields})
