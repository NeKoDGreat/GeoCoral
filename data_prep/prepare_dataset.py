"""
GeoCoral — dataset preparation.

Combines two sources described in the Methodology chapter:

  1. Local field images captured by authorized divers in the three
     selected Samal Island marine sanctuaries. Expected layout:

         raw_data/local_field_images/
             healthy/*.jpg
             bleached/*.jpg
             metadata.csv   <- one row per image filename with GPS and
                                field metadata (see METADATA_COLUMNS below)

  2. The supplementary "Bleached and Unbleached Corals Classification"
     Kaggle dataset (342 balanced images), used only to grow the
     training set. Expected layout:

         raw_data/kaggle_bleached_corals/
             healthy/*.jpg (or .png)
             bleached/*.jpg (or .png)

For each image this script:
  - Applies CLAHE to correct underwater haze / low contrast
  - Resizes to 224x224 (ResNet50 input size)
  - Writes the processed image into processed_data/{train,val,test}/{label}/
  - Logs GPS + field metadata (local images only) alongside the split
    assignment in processed_data/split_metadata.csv, which the GeoCoral
    web/mobile app later reads to plot classification results on the
    geomapping interface.

Run:
    python -m data_prep.prepare_dataset
"""

import csv
import os
import sys

import cv2
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# Columns expected in raw_data/local_field_images/metadata.csv.
# "filename" must match the image's filename within its class subfolder.
METADATA_COLUMNS = [
    "filename",
    "label",             # "healthy" or "bleached"
    "latitude",
    "longitude",
    "datetime",
    "depth_m",
    "sanctuary_location",
    "area_code",
    "photographer",
]

VALID_EXTENSIONS = (".jpg", ".jpeg", ".png")


def _list_images(class_dir):
    if not os.path.isdir(class_dir):
        return []
    return sorted(
        f for f in os.listdir(class_dir) if f.lower().endswith(VALID_EXTENSIONS)
    )


def gather_local_images():
    """Return a list of record dicts for locally captured field images,
    joined with their GPS/field metadata."""
    records = []

    if not os.path.exists(config.LOCAL_METADATA_CSV):
        print(f"[warn] No local metadata CSV found at {config.LOCAL_METADATA_CSV}; "
              f"skipping local field images.")
        return records

    meta = pd.read_csv(config.LOCAL_METADATA_CSV)
    missing_cols = set(METADATA_COLUMNS) - set(meta.columns)
    if missing_cols:
        raise ValueError(
            f"metadata.csv is missing required columns: {sorted(missing_cols)}"
        )
    # Index by (label, filename), not filename alone — the same filename
    # (e.g. IMG_0001.jpg) can legitimately appear in both the healthy/
    # and bleached/ subfolders since cameras reuse filename sequences.
    meta = meta.set_index(["label", "filename"])

    for class_name in config.CLASS_NAMES:
        class_dir = os.path.join(config.RAW_LOCAL_DIR, class_name)
        for fname in _list_images(class_dir):
            key = (class_name, fname)
            if key not in meta.index:
                print(f"[warn] {fname} ({class_name}) has no metadata row; skipping.")
                continue
            row = meta.loc[key]
            records.append({
                "path": os.path.join(class_dir, fname),
                "filename": fname,
                "label": class_name,
                "source": "local_field",
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "datetime": row["datetime"],
                "depth_m": row["depth_m"],
                "sanctuary_location": row["sanctuary_location"],
                "area_code": row["area_code"],
                "photographer": row["photographer"],
            })
    return records


def gather_kaggle_images():
    """Return record dicts for the supplementary Kaggle dataset.
    These carry no field GPS data and are never plotted on the geomap."""
    records = []
    for class_name in config.CLASS_NAMES:
        class_dir = os.path.join(config.RAW_KAGGLE_DIR, class_name)
        for fname in _list_images(class_dir):
            records.append({
                "path": os.path.join(class_dir, fname),
                "filename": fname,
                "label": class_name,
                "source": "kaggle_supplementary",
                "latitude": None,
                "longitude": None,
                "datetime": None,
                "depth_m": None,
                "sanctuary_location": None,
                "area_code": None,
                "photographer": None,
            })
    return records


def stratified_split(records):
    """70/15/15 stratified split by class label, per the Data Collection
    and Dataset Preparation section."""
    labels = [r["label"] for r in records]

    train_records, temp_records, train_labels, temp_labels = train_test_split(
        records,
        labels,
        train_size=config.TRAIN_SPLIT,
        stratify=labels,
        random_state=config.RANDOM_SEED,
    )

    # temp_records = val + test (15% + 15% = 30% of the total);
    # split that remainder evenly in half.
    val_fraction_of_temp = config.VAL_SPLIT / (config.VAL_SPLIT + config.TEST_SPLIT)
    val_records, test_records = train_test_split(
        temp_records,
        train_size=val_fraction_of_temp,
        stratify=temp_labels,
        random_state=config.RANDOM_SEED,
    )

    return {"train": train_records, "val": val_records, "test": test_records}


def apply_clahe(bgr_image):
    """Contrast-limited adaptive histogram equalization on the L channel
    of LAB color space, to correct underwater haze/low contrast."""
    lab = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)

    clahe = cv2.createCLAHE(
        clipLimit=config.CLAHE_CLIP_LIMIT,
        tileGridSize=config.CLAHE_TILE_GRID_SIZE,
    )
    l_channel = clahe.apply(l_channel)

    lab = cv2.merge((l_channel, a_channel, b_channel))
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def preprocess_and_save(record, split_name):
    """CLAHE -> resize 224x224 -> save into processed_data/{split}/{label}/."""
    image = cv2.imread(record["path"])
    if image is None:
        print(f"[warn] Could not read {record['path']}; skipping.")
        return None

    image = apply_clahe(image)
    image = cv2.resize(
        image, (config.IMG_SIZE, config.IMG_SIZE), interpolation=cv2.INTER_AREA
    )

    out_dir = os.path.join(config.SPLIT_DIRS[split_name], record["label"])
    os.makedirs(out_dir, exist_ok=True)

    # Disambiguate filenames across sources to avoid collisions.
    out_name = f"{record['source']}_{record['filename']}"
    out_path = os.path.join(out_dir, out_name)
    cv2.imwrite(out_path, image)

    return {
        "filename": out_name,
        "split": split_name,
        "label": record["label"],
        "source": record["source"],
        "latitude": record["latitude"],
        "longitude": record["longitude"],
        "datetime": record["datetime"],
        "depth_m": record["depth_m"],
        "sanctuary_location": record["sanctuary_location"],
        "area_code": record["area_code"],
        "photographer": record["photographer"],
    }


def main():
    local_records = gather_local_images()
    kaggle_records = gather_kaggle_images()
    all_records = local_records + kaggle_records

    if not all_records:
        raise SystemExit(
            "No images found. Populate raw_data/local_field_images/ and/or "
            "raw_data/kaggle_bleached_corals/ before running this script."
        )

    print(f"Local field images:  {len(local_records)}")
    print(f"Kaggle supplementary images: {len(kaggle_records)}")
    print(f"Total images: {len(all_records)}")

    for label in config.CLASS_NAMES:
        count = sum(1 for r in all_records if r["label"] == label)
        print(f"  {label}: {count}")

    splits = stratified_split(all_records)

    os.makedirs(config.PROCESSED_DIR, exist_ok=True)
    output_rows = []
    for split_name, records in splits.items():
        print(f"\nProcessing {split_name} split ({len(records)} images)...")
        for record in records:
            row = preprocess_and_save(record, split_name)
            if row is not None:
                output_rows.append(row)

    with open(config.SPLIT_METADATA_CSV, "w", newline="") as f:
        fieldnames = [
            "filename", "split", "label", "source", "latitude", "longitude",
            "datetime", "depth_m", "sanctuary_location", "area_code", "photographer",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"\nDone. Processed images written to {config.PROCESSED_DIR}")
    print(f"Split metadata written to {config.SPLIT_METADATA_CSV}")

    for split_name, records in splits.items():
        healthy = sum(1 for r in records if r["label"] == "healthy")
        bleached = sum(1 for r in records if r["label"] == "bleached")
        print(f"  {split_name}: {healthy} healthy, {bleached} bleached")


if __name__ == "__main__":
    main()
