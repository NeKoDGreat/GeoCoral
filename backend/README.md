# GeoCoral Backend (Django + GeoDjango + DRF)

Stores GPS-tagged coral classification results and serves them to the
geomapping frontend. Sits alongside the ML training project — one
directory up — and calls its `training/predict.py` directly for
inference (see `monitoring/ml_service.py`).

## 1. Choose your local database: PostgreSQL/PostGIS (recommended) or SpatiaLite

**On Windows, use PostgreSQL/PostGIS for local dev too** — GeoDjango's
SpatiaLite path needs GDAL set up via OSGeo4W, which involves manual
PATH/environment variable edits and is a common source of setup pain.
Installing PostgreSQL locally is simpler, better documented, and
matches your production database exactly.

### Option A — PostgreSQL + PostGIS (recommended)

1. Download PostgreSQL from https://www.postgresql.org/download/windows/
   and run the installer. When it offers **Stack Builder** at the end,
   use it to install the **PostGIS** extension (under
   "Spatial Extensions").
2. Open **SQL Shell (psql)** (installed alongside PostgreSQL) and run:
   ```sql
   CREATE USER geocoral WITH PASSWORD 'choose_a_password' CREATEDB;
   CREATE DATABASE geocoral OWNER geocoral;
   \c geocoral
   CREATE EXTENSION postgis;
   ```
3. Set environment variables before running any `manage.py` command
   (PowerShell):
   ```powershell
   $env:GEOCORAL_DB="postgis"
   $env:DB_NAME="geocoral"
   $env:DB_USER="geocoral"
   $env:DB_PASSWORD="choose_a_password"
   $env:DB_HOST="localhost"
   $env:DB_PORT="5432"
   ```
   (Setting these every terminal session gets old fast — consider a
   `.env` file with `django-environ`, or a small `activate.ps1` script
   that sets them, once you're comfortable with the basics.)

### Option B — SpatiaLite (if you already have GDAL/OSGeo4W working)

1. Install GDAL via the OSGeo4W installer:
   https://docs.djangoproject.com/en/stable/ref/contrib/gis/install/#windows
2. Find `mod_spatialite.dll` in your OSGeo4W `bin` folder and set:
   ```powershell
   $env:SPATIALITE_LIBRARY_PATH="C:\OSGeo4W\bin\mod_spatialite"
   ```
3. Leave `GEOCORAL_DB` unset (SpatiaLite is the default).

## 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

(This is separate from the ML project's `requirements.txt` one level
up — that one has TensorFlow, this one has Django. Both live in the
same virtual environment if you're using the one you already set up.)

## 3. Run migrations and create an admin login

```bash
python manage.py migrate
python manage.py createsuperuser
```

For local project testing, create the four shared profile accounts after
migrations:

```powershell
python manage.py seed_users
```

This command is blocked when `DEBUG=False`. It creates or refreshes the
following local-only accounts; rerunning it resets their passwords to
these documented values:

| Role | Username | Password |
|---|---|---|
| CENRO Staff | `cenro_staff` | `geocoralcenrostaff` |
| Sanctuary Manager | `sanctuary_manager` | `geocoralsanctuarymanager` |
| Authorized Diver | `diver` | `geocoraldiver` |
| Administrator | `admin` | `geocoraladmin` |

The Administrator profile can view, add, and edit GeoCoral records in
Django admin, but is not a superuser and cannot delete records. These
shared credentials are intentionally for local development only; do not
enable or use them in production. The accounts use non-deliverable
`example.invalid` email addresses.

## 4. Seed placeholder sanctuaries

```bash
python manage.py seed_sanctuaries
```

Creates three placeholder sanctuary records so the app has something
to work with immediately. **Edit
`monitoring/management/commands/seed_sanctuaries.py`** with your real
sanctuary names, area codes, and coordinates once you have them —
or add/edit them through the admin site instead (step 6).

## 5. Run the dev server

```bash
python manage.py runserver
```

## 6. Try it out

- **Admin site:** http://127.0.0.1:8000/admin/ — log in with your
  superuser account. `CoralRecord` and `Sanctuary` both show an
  interactive map widget for editing location fields, since they're
  registered with `GISModelAdmin`.
- **Browsable API:** http://127.0.0.1:8000/api/coral-records/ and
  http://127.0.0.1:8000/api/sanctuaries/ — DRF's browsable API lets
  you test the upload endpoint (`POST /api/coral-records/`) right from
  the browser once logged in via http://127.0.0.1:8000/api-auth/login/.

## API summary

| Endpoint | Method | Auth | Purpose |
|---|---|---|---|
| `/api/sanctuaries/` | GET | none | List sanctuaries (for map + filters) |
| `/api/coral-records/` | GET | none | List classification results, filterable by `?sanctuary=`, `?label=healthy\|bleached`, `?since=<ISO datetime>` |
| `/api/coral-records/` | POST | required | Upload a photo + GPS + field metadata → runs the classifier → returns the result |
| `/api/coral-records/<id>/` | GET/PATCH/DELETE | none/required | Detail, update (e.g. expert verification), delete |

The upload endpoint expects `multipart/form-data` with: `image`,
`latitude`, `longitude`, `captured_at` (ISO datetime), `depth_m`,
`sanctuary` (ID), `area_code`, `gps_source` (`device` or `manual`).

## Connecting the trained model

`monitoring/ml_service.py` loads the checkpoint at
`saved_models/geocoral_resnet50_best.keras` in the ML project (one
directory up) by default. Once you've trained a better model with real
field data, either overwrite that same file, or point at a different
one:

```powershell
$env:GEOCORAL_MODEL_PATH="C:\path\to\your\model.keras"
```

## Next steps not yet built here

- Sanctuary **boundary polygons** (currently just a center point per
  sanctuary) — draw these in the admin's map widget once you have
  survey data, to enable "is this point inside sanctuary X" queries.
- The actual **frontend** (Leaflet.js map, upload form) — this backend
  is API-only right now.
- **Deployment** settings (allowed hosts, static file serving,
  HTTPS) — current settings are dev-oriented.
