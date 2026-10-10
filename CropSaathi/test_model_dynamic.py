
import argparse
import csv
from pathlib import Path

from PIL import Image
from transformers import pipeline

MODEL_ID = "wambugu71/crop_leaf_diseases_vit"
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def get_images(path: Path):
    if path.is_file():
        return [path] if path.suffix.lower() in SUPPORTED_EXTENSIONS else []

    if path.is_dir():
        return sorted(
            p for p in path.rglob("*")
            if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
        )

    return []


def main():
    parser = argparse.ArgumentParser(
        description="Test CropSaathi's pretrained leaf classifier."
    )
    parser.add_argument(
        "--input",
        default="samples",
        help="Image file or folder; defaults to samples/"
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="Number of predictions to display"
    )
    parser.add_argument(
        "--csv",
        default="test_results.csv",
        help="CSV output path; use an empty string to skip saving"
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    images = get_images(input_path)

    if not images:
        raise SystemExit(f"No supported images found at: {input_path}")

    print(f"Loading model: {MODEL_ID}")
    classifier = pipeline(
        "image-classification",
        model=MODEL_ID,
        device=-1,
    )

    rows = []

    for image_path in images:
        print(f"\nImage: {image_path}")

        try:
            with Image.open(image_path) as image:
                image = image.convert("RGB")
                predictions = classifier(
                    image,
                    top_k=max(1, args.top_k)
                )

            for rank, result in enumerate(predictions, start=1):
                label = result["label"]
                score = result["score"]

                print(
                    f"  {rank}. {label} "
                    f"(model score: {score:.4f})"
                )

                rows.append({
                    "image": str(image_path),
                    "rank": rank,
                    "label": label,
                    "model_score": score,
                })

        except Exception as error:
            print(f"  ERROR: {error}")
            rows.append({
                "image": str(image_path),
                "rank": "",
                "label": "ERROR",
                "model_score": "",
            })

    if args.csv:
        output_path = Path(args.csv)
        with output_path.open(
            "w", newline="", encoding="utf-8-sig"
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "image", "rank", "label", "model_score"
                ],
            )
            writer.writeheader()
            writer.writerows(rows)

        print(f"\nResults saved to: {output_path.resolve()}")


if __name__ == "__main__":
    main()
