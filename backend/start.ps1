# GeoCoral backend startup script.
# Run this once per new terminal session before any manage.py command.

$env:GEOCORAL_DB = "postgis"
$env:DB_NAME = "geocoral"
$env:DB_USER = "geocoral"
$securePassword = Read-Host "PostgreSQL password for geocoral" -AsSecureString
$env:DB_PASSWORD = [System.Net.NetworkCredential]::new("", $securePassword).Password
$env:DB_HOST = "localhost"
$env:DB_PORT = "5432"
$postgresBin = "C:\Program Files\PostgreSQL\18\bin"
$env:GDAL_LIBRARY_PATH = Join-Path $postgresBin "libgdal-35.dll"
$env:GEOS_LIBRARY_PATH = Join-Path $postgresBin "libgeos_c.dll"
if (($env:PATH -split ";") -notcontains $postgresBin) {
    $env:PATH = "$postgresBin;$env:PATH"
}

Write-Host "Environment variables set. GEOCORAL_DB = $env:GEOCORAL_DB" -ForegroundColor Green