# CropSaathi model evaluation

The repository does not currently contain a labelled evaluation manifest.
The images in `samples/` are smoke-test assets, and `test_results.csv` contains
model outputs without ground-truth labels. Measured accuracy is therefore
unknown until the developer supplies a labelled local manifest.

## Manifest format

Create a CSV outside the application source tree or in a local evaluation
directory. Every row must include:

```csv
image_path,ground_truth_label,selected_crop,split
data/leaf_001.png,Corn___Common_Rust,corn,evaluation
```

- `image_path` is relative to the manifest file or an absolute local path.
- `ground_truth_label` must be an explicit class label from the model's
  verified class mapping.
- `selected_crop` must be one of the configured application crops:
  `rice`, `wheat`, or `corn`.
- `split` must be `train`, `validation`, `evaluation`, or `test`.
- Use `evaluation` (or explicitly choose `test`) for held-out final reporting.
  Do not tune thresholds or other settings on that split.

The evaluator rejects missing files, unsupported extensions, unsupported
crops, missing fields, invalid labels, and manifests with no rows in the
selected split. Images are then passed through the existing image validator
before inference.

## Running an evaluation

From the `CropSaathi` directory with the existing environment activated:

```powershell
python evaluate_model.py `
  --manifest path\to\manifest.csv `
  --split evaluation `
  --json results\evaluation.json `
  --csv results\evaluation_samples.csv
```

The script uses `src.model_service.ModelService`, so it may use already cached
model weights but does not download a dataset. If model weights are unavailable,
the evaluation cannot run.

The JSON summary reports total, valid, and invalid samples, top-1 accuracy,
per-class precision/recall/F1, a confusion matrix, raw score statistics,
decision-rule rejected/uncertain counts, and model/application label
compatibility. The CSV contains one row per manifest sample.

Scores are reported as raw model scores only. This tooling does not measure
probability calibration. Accuracy remains unknown until a labelled,
held-out local dataset is evaluated.