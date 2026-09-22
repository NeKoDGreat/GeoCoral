# GeoCoral backend startup script.
# Run this once per new terminal session before any manage.py command.

$env:GEOCORAL_DB = "postgis"
$env:DB_NAME = "geocoral"
$env:DB_USER = "geocoral"
$env:DB_PASSWORD = "geocoral123"
$env:DB_HOST = "localhost"
$env:DB_PORT = "5432"
$env:GDAL_LIBRARY_PATH = "C:\Program Files\PostgreSQL\18\bin\libgdal-35.dll"
$env:GEOS_LIBRARY_PATH = "C:\Program Files\PostgreSQL\18\bin\libgeos_c.dll"

Write-Host "Environment variables set. GEOCORAL_DB = $env:GEOCORAL_DB" -ForegroundColor Green