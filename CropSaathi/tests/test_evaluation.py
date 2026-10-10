from __future__ import annotations

import csv
import json
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from src.evaluation import (
    APPLICATION_SUPPORTED_LABELS,
    ManifestError,
    calculate_metrics,
    evaluate_manifest,
    validate_manifest,
    write_results,
)


def make_image(path: Path, image_format: str = "PNG") -> None:
    image = Image.new("RGB", (100, 100), color="green")
    image.save(path, format=image_format)


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "image_path",
                "ground_truth_label",
                "selected_crop",
                "split",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def valid_row(image_name: str = "leaf.png") -> dict[str, str]:
    return {
        "image_path": image_name,
        "ground_truth_label": "Corn___Common_Rust",
        "selected_crop": "corn",
        "split": "evaluation",
    }


def test_manifest_requires_explicit_columns_and_existing_files(tmp_path):
    manifest = tmp_path / "manifest.csv"
    write_manifest(manifest, [valid_row("missing.png")])

    with pytest.raises(ManifestError, match="missing image"):
        validate_manifest(manifest, allowed_labels=APPLICATION_SUPPORTED_LABELS)


def test_manifest_rejects_invalid_labels(tmp_path):
    image = tmp_path / "leaf.png"
    make_image(image)
    manifest = tmp_path / "manifest.csv"
    row = valid_row()
    row["ground_truth_label"] = "Invented___Label"
    write_manifest(manifest, [row])

    with pytest.raises(ManifestError, match="unsupported label"):
        validate_manifest(manifest, allowed_labels=APPLICATION_SUPPORTED_LABELS)


def test_manifest_rejects_unsupported_format(tmp_path):
    image = tmp_path / "leaf.gif"
    make_image(image, "GIF")
    manifest = tmp_path / "manifest.csv"
    write_manifest(manifest, [{**valid_row("leaf.gif")}])

    with pytest.raises(ManifestError, match="unsupported image format"):
        validate_manifest(manifest)


def test_manifest_rejects_empty_selected_split(tmp_path):
    image = tmp_path / "leaf.png"
    make_image(image)
    manifest = tmp_path / "manifest.csv"
    row = valid_row()
    row["split"] = "validation"
    write_manifest(manifest, [row])

    with pytest.raises(ManifestError, match="no rows"):
        validate_manifest(manifest, split="evaluation")


def test_metric_calculation_reports_accuracy_per_class_and_confusion():
    records = [
        {"ground_truth_label": "A", "predicted_label": "A"},
        {"ground_truth_label": "A", "predicted_label": "B"},
        {"ground_truth_label": "B", "predicted_label": "B"},
    ]

    result = calculate_metrics(records)

    assert result["sample_count"] == 3
    assert result["top1_accuracy"] == pytest.approx(2 / 3)
    assert result["per_class"]["A"]["recall"] == pytest.approx(0.5)
    assert result["per_class"]["B"]["precision"] == pytest.approx(0.5)
    assert result["confusion_matrix"]["counts"]["A"]["B"] == 1


def test_empty_metrics_are_rejected():
    with pytest.raises(ValueError, match="empty"):
        calculate_metrics([])


class FakeService:
    model = None

    def __init__(self, predictions):
        self.predictions = iter(predictions)

    def predict(self, image):
        return next(self.predictions)


def test_evaluation_uses_validator_and_reports_invalid_samples(tmp_path):
    good = tmp_path / "good.png"
    bad = tmp_path / "bad.png"
    make_image(good)
    bad.write_bytes(b"not an image")
    manifest = tmp_path / "manifest.csv"
    write_manifest(
        manifest,
        [valid_row("good.png"), valid_row("bad.png")],
    )
    service = FakeService(
        [
            {
                "label": "Corn___Common_Rust",
                "crop": "corn",
                "model_score": 0.9,
            }
        ]
    )

    result = evaluate_manifest(manifest, model_service=service)

    assert result["total_samples"] == 2
    assert result["valid_samples"] == 1
    assert result["invalid_samples"] == 1
    assert result["metrics"]["top1_accuracy"] == 1.0


def test_evaluation_rejects_empty_valid_set(tmp_path):
    image = tmp_path / "bad.png"
    image.write_bytes(b"not an image")
    manifest = tmp_path / "manifest.csv"
    write_manifest(manifest, [valid_row("bad.png")])

    with pytest.raises(ValueError, match="No valid samples"):
        evaluate_manifest(manifest, model_service=FakeService([]))


def test_results_export_to_json_and_csv(tmp_path):
    result = {
        "total_samples": 1,
        "samples": [{"image_path": "x.png", "status": "evaluated"}],
    }
    json_path = tmp_path / "out" / "summary.json"
    csv_path = tmp_path / "out" / "samples.csv"

    write_results(result, json_path=json_path, csv_path=csv_path)

    assert json.loads(json_path.read_text(encoding="utf-8")) == result
    assert "image_path" in csv_path.read_text(encoding="utf-8")
