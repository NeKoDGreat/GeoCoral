## Trained model

`saved_models/geocoral_resnet50_best.keras` (~205MB) is not included in
this repository — it exceeds GitHub's file size limit. To run inference
or the backend's photo classification:

1. Download it from: **[add your Google Drive / cloud link here]**
2. Place it in `saved_models/geocoral_resnet50_best.keras` at the
   project root (create the `saved_models/` folder if it doesn't exist)

Alternatively, retrain it yourself by following the steps in this
README (`prepare_dataset.py` then `train.py`), which regenerates this
file from scratch.
