
from transformers import pipeline
from pathlib import Path
from PIL import Image

MODEL_ID = "wambugu71/crop_leaf_diseases_vit"
IMAGE_PATH = Path("samples/test_leaf.png")

def main():
    print("Loading CropSaathi's candidate model...")
    classifier = pipeline(
        "image-classification",
        model=MODEL_ID,
        device=-1,  # CPU inference
    )
    print("Model loaded successfully.")

    print("\nModel labels:")
    print(classifier.model.config.id2label)

    if not IMAGE_PATH.exists():
        print(f"\nPlace a leaf image at: {IMAGE_PATH}")
        print("Then run this script again.")
        return

    with Image.open(IMAGE_PATH) as image:
        image = image.convert("RGB")
        predictions = classifier(image, top_k=3)

    print("\nTop predictions:")
    for item in predictions:
        print(
            f"- {item['label']}: "
            f"model score = {item['score']:.4f}"
        )

if __name__ == "__main__":
    main()
