# ERP Builder Startup Script for PowerShell

Write-Host "====================================" -ForegroundColor Cyan
Write-Host "  ERP Builder - Local AI System" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment exists
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
    Write-Host ""
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Green
& .\venv\Scripts\Activate.ps1

# Check if .env exists
if (-not (Test-Path ".env")) {
    Write-Host "WARNING: .env file not found!" -ForegroundColor Red
    Write-Host "Creating .env from template..." -ForegroundColor Yellow
    Copy-Item .env.example .env
    Write-Host ""
    Write-Host "IMPORTANT: Please edit .env and add your API keys!" -ForegroundColor Yellow
    Write-Host "Opening .env file..." -ForegroundColor Green
    Start-Process notepad.exe .env
    Write-Host ""
    Write-Host "Press any key after saving .env to continue..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}

# Install/upgrade dependencies
Write-Host "Checking dependencies..." -ForegroundColor Green
pip install -q --upgrade pip
pip install -q -r requirements.txt

Write-Host ""
Write-Host "====================================" -ForegroundColor Cyan
Write-Host "  Starting ERP Builder..." -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Application will be available at:" -ForegroundColor Green
Write-Host "  http://localhost:8000" -ForegroundColor Yellow
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Gray
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

# Start the application
python main.py
