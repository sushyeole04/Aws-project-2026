# deploy.ps1
# This script prepares the environment and executes the Python deployment script

Write-Host "Checking for Python installation..." -ForegroundColor Cyan
if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
    Write-Host "Python is not installed or not in PATH. Please install Python and try again." -ForegroundColor Red
    exit 1
}

Write-Host "Installing required Python packages (boto3)..." -ForegroundColor Cyan
python -m pip install --upgrade pip
python -m pip install boto3 botocore

Write-Host "Starting AWS 3-Tier Architecture Deployment..." -ForegroundColor Green
Write-Host "--------------------------------------------------------" -ForegroundColor Green

# Execute the deployment script
python deploy.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "--------------------------------------------------------" -ForegroundColor Green
    Write-Host "Deployment script finished successfully." -ForegroundColor Green
} else {
    Write-Host "--------------------------------------------------------" -ForegroundColor Red
    Write-Host "Deployment script failed with exit code $LASTEXITCODE." -ForegroundColor Red
}
