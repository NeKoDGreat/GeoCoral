"""
GeoCoral — auto-generate metadata.csv rows from photo EXIF data.

Most smartphones and GPS-enabled cameras embed latitude/longitude and
capture timestamp directly in each photo's EXIF metadata. This script
reads that automatically for every image in
raw_data/local_field_images/{healthy,bleached}/ and writes/updates
metadata.csv, so you only need to type in the values that stay the same
for an entire dive session: depth, sanctuary_location, area_code, and
photographer.

Images with no embedded GPS data (common if location services were off,
or with some underwater housings) are still added to metadata.csv, but
with blank latitude/longitude — per your paper, these should be filled
in manually through the submission interface, or here directly in the
CSV, before running prepare_dataset.py.

Run once per dive-session batch of new photos, e.g.:

    python -m data_prep.extract_metadata \\
        --depth 5.2 \\
        --sanctuary "Adecor Marine Sanctuary" \\
        --area-code ADE-01 \\
        --photographer "J. Dela Cruz"

By default this appends to the existing metadata.csv without duplicating
rows for filenames (within the same label) that are already present, so
it's safe to re-run as you add new photos over time.
"""

import argparse
import csv
import os
import sys

from PIL import Image
from PIL.ExifTags import GPSTAGS, TAGS

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

VALID_EXTENSIONS = (".jpg", ".jpeg", ".png")

CSV_FIELDNAMES = [
    "filename", "label", "latitude", "longitude", "datetime",
    "depth_m", "sanctuary_location", "area_code", "photographer",
]


def _dms_to_decimal(dms, ref):
    """Convert EXIF GPS degrees/minutes/seconds to decimal degrees."""
    degrees, minutes, seconds = dms
    decimal = float(degrees) + float(minutes) / 60.0 + float(seconds) / 3600.0
    if ref in ("S", "W"):
        decimal = -decimal
    return round(decimal, 6)


def read_exif_gps_and_datetime(image_path):
    """Returns (latitude, longitude, datetime_str) — any of which may be
    None if not present in the image's EXIF data."""
    try:
        image = Image.open(image_path)
        exif_raw = image._getexif()
    except Exception:
        exif_raw = None

    if not exif_raw:
        return None, None, None

    exif = {TAGS.get(tag_id, tag_id): value for tag_id, value in exif_raw.items()}

    datetime_str = exif.get("DateTimeOriginal") or exif.get("DateTime")

    gps_info = exif.get("GPSInfo")
    if not gps_info:
        return None, None, datetime_str

    gps = {GPSTAGS.get(tag_id, tag_id): value for tag_id, value in gps_info.items()}

    lat = lon = None
    if "GPSLatitude" in gps and "GPSLatitudeRef" in gps:
        lat = _dms_to_decimal(gps["GPSLatitude"], gps["GPSLatitudeRef"])
    if "GPSLongitude" in gps and "GPSLongitudeRef" in gps:
        lon = _dms_to_decimal(gps["GPSLongitude"], gps["GPSLongitudeRef"])

    return lat, lon, datetime_str


def load_existing_rows():
    """Existing (label, filename) keys already in metadata.csv, so
    re-running this script doesn't create duplicate rows."""
    existing = {}
    if os.path.exists(config.LOCAL_METADATA_CSV):
        with open(config.LOCAL_METADATA_CSV, newline="") as f:
            for row in csv.DictReader(f):
                existing[(row["label"], row["filename"])] = row
    return existing


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--depth", type=float, default=None,
                         help="Dive depth in meters, applied to all new rows in this run.")
    parser.add_argument("--sanctuary", type=str, default=None,
                         help="Sanctuary name, applied to all new rows in this run.")
    parser.add_argument("--area-code", type=str, default=None,
                         help="Area/site code, applied to all new rows in this run.")
    parser.add_argument("--photographer", type=str, default=None,
                         help="Photographer name, applied to all new rows in this run.")
    args = parser.parse_args()

    existing_rows = load_existing_rows()
    new_rows = []
    missing_gps = []

    for class_name in config.CLASS_NAMES:
        class_dir = os.path.join(config.RAW_LOCAL_DIR, class_name)
        if not os.path.isdir(class_dir):
            continue

        for fname in sorted(os.listdir(class_dir)):
            if not fname.lower().endswith(VALID_EXTENSIONS):
                continue

            key = (class_name, fname)
            if key in existing_rows:
                continue  # already recorded, leave existing row untouched

            image_path = os.path.join(class_dir, fname)
            lat, lon, dt = read_exif_gps_and_datetime(image_path)

            if lat is None or lon is None:
                missing_gps.append(fname)

            new_rows.append({
                "filename": fname,
                "label": class_name,
                "latitude": lat if lat is not None else "",
                "longitude": lon if lon is not None else "",
                "datetime": dt or "",
                "depth_m": args.depth if args.depth is not None else "",
                "sanctuary_location": args.sanctuary or "",
                "area_code": args.area_code or "",
                "photographer": args.photographer or "",
            })

    if not new_rows:
        print("No new images found — metadata.csv is already up to date.")
        return

    all_rows = list(existing_rows.values()) + new_rows
    os.makedirs(config.RAW_LOCAL_DIR, exist_ok=True)
    with open(config.LOCAL_METADATA_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"Added {len(new_rows)} new row(s) to {config.LOCAL_METADATA_CSV}")
    print(f"Total rows in metadata.csv: {len(all_rows)}")

    if missing_gps:
        print(f"\n[action needed] {len(missing_gps)} image(s) had no embedded GPS data "
              f"and were added with blank latitude/longitude. Fill these in manually:")
        for fname in missing_gps:
            print(f"  - {fname}")


if __name__ == "__main__":
    main()
