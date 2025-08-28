#!/usr/bin/env pwsh

# TerraVision Installation Script
# This script installs all prerequisites for the TerraVision project

Write-Host "=== TerraVision Installation Script ===" -ForegroundColor Cyan
Write-Host "Setting up prerequisites..." -ForegroundColor Yellow

# Function to check if command exists
function Test-Command {
    param($Command)
    try {
        Get-Command $Command -ErrorAction Stop | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

# Check Python installation and version
Write-Host "`nChecking Python installation..." -ForegroundColor Yellow

if (-not (Test-Command "python")) {
    Write-Host "ERROR: Python is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Python 3.9-3.11 from https://python.org" -ForegroundColor Red
    exit 1
}

# Get Python version
$pythonVersion = python --version 2>&1
Write-Host "Found: $pythonVersion" -ForegroundColor Green

# Parse version number
$versionMatch = $pythonVersion -match "Python (\d+)\.(\d+)\.(\d+)"
if ($versionMatch) {
    $majorVersion = [int]$matches[1]
    $minorVersion = [int]$matches[2]
    
    # Check version requirements (>=3.9, <3.12)
    if ($majorVersion -lt 3 -or ($majorVersion -eq 3 -and $minorVersion -lt 9)) {
        Write-Host "ERROR: Python version must be >= 3.9" -ForegroundColor Red
        Write-Host "Current version: $pythonVersion" -ForegroundColor Red
        Write-Host "Please install a compatible Python version from https://python.org" -ForegroundColor Red
        exit 1
    }
    
    if ($majorVersion -gt 3 -or ($majorVersion -eq 3 -and $minorVersion -ge 12)) {
        Write-Host "ERROR: Python version must be < 3.12 for compatibility with project dependencies" -ForegroundColor Red
        Write-Host "Current version: $pythonVersion" -ForegroundColor Red
        Write-Host "Please install Python 3.9, 3.10, or 3.11 from https://python.org" -ForegroundColor Red
        Write-Host "You can install multiple Python versions side by side." -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Host "WARNING: Could not parse Python version" -ForegroundColor Yellow
}

# Check if pip is available
Write-Host "`nChecking pip availability..." -ForegroundColor Yellow
$pipAvailable = $false
try {
    python -m pip --version | Out-Null
    $pipAvailable = $true
    Write-Host "pip is available" -ForegroundColor Green
}
catch {
    Write-Host "pip is not available, attempting to install..." -ForegroundColor Yellow
    try {
        python -m ensurepip --upgrade
        $pipAvailable = $true
        Write-Host "pip installed successfully" -ForegroundColor Green
    }
    catch {
        Write-Host "WARNING: Could not install pip" -ForegroundColor Yellow
    }
}

# Check if Poetry is installed
Write-Host "`nChecking Poetry installation..." -ForegroundColor Yellow

if (-not (Test-Command "poetry")) {
    Write-Host "Poetry not found. Installing Poetry..." -ForegroundColor Yellow
    
    $poetryInstalled = $false
    
    # Try official Poetry installer first
    try {
        Write-Host "Trying official Poetry installer..." -ForegroundColor Yellow
        $installScript = Invoke-WebRequest -Uri "https://install.python-poetry.org" -UseBasicParsing
        $installScript.Content | python -
        
        # Refresh PATH to include Poetry (try multiple common locations)
        $env:PATH = "$env:APPDATA\Python\Scripts;$env:USERPROFILE\.local\bin;$env:PATH"
        
        # Give a moment for PATH to refresh
        Start-Sleep -Seconds 3
        
        if (Test-Command "poetry") {
            Write-Host "Poetry installed successfully using official installer" -ForegroundColor Green
            $poetryInstalled = $true
        } else {
            # Try to find poetry executable manually
            $poetryPaths = @(
                "$env:APPDATA\Python\Scripts\poetry.exe",
                "$env:USERPROFILE\.local\bin\poetry.exe",
                "$env:USERPROFILE\AppData\Roaming\Python\Scripts\poetry.exe"
            )
            
            foreach ($path in $poetryPaths) {
                if (Test-Path $path) {
                    Write-Host "Found Poetry at: $path" -ForegroundColor Yellow
                    Write-Host "Poetry installed but not in PATH. You may need to restart your terminal." -ForegroundColor Yellow
                    $poetryInstalled = $true
                    break
                }
            }
        }
    }
    catch {
        Write-Host "Official installer failed: $($_.Exception.Message)" -ForegroundColor Yellow
    }
    
    # Fallback to pip method if official installer failed and pip is available
    if (-not $poetryInstalled -and $pipAvailable) {
        try {
            Write-Host "Trying pip installation method..." -ForegroundColor Yellow
            python -m pip install poetry
            
            # Refresh PATH
            $env:PATH = "$env:APPDATA\Python\Scripts;$env:PATH"
            Start-Sleep -Seconds 2
            
            if (Test-Command "poetry") {
                Write-Host "Poetry installed successfully using pip" -ForegroundColor Green
                $poetryInstalled = $true
            }
        }
        catch {
            Write-Host "pip installation failed: $($_.Exception.Message)" -ForegroundColor Yellow
        }
    }
    
    if (-not $poetryInstalled) {
        Write-Host "ERROR: Failed to install Poetry using all methods" -ForegroundColor Red
        Write-Host "Please install Poetry manually using one of these methods:" -ForegroundColor Red
        Write-Host "1. Download installer from: https://python-poetry.org/docs/#installation" -ForegroundColor Yellow
        Write-Host "2. Use pip: pip install poetry" -ForegroundColor Yellow
        Write-Host "3. Use pipx: pipx install poetry" -ForegroundColor Yellow
        exit 1
    }
} else {
    $poetryVersion = poetry --version
    Write-Host "Found: $poetryVersion" -ForegroundColor Green
}

# Verify we're in the correct directory
if (-not (Test-Path "pyproject.toml")) {
    Write-Host "ERROR: pyproject.toml not found" -ForegroundColor Red
    Write-Host "Please run this script from the TerraVision project root directory" -ForegroundColor Red
    exit 1
}

# Install dependencies
Write-Host "`nInstalling project dependencies..." -ForegroundColor Yellow

try {
    if (Test-Command "poetry") {
        poetry install
        Write-Host "Dependencies installed successfully" -ForegroundColor Green
    } else {
        Write-Host "Poetry command not found. Trying direct execution..." -ForegroundColor Yellow
        # Try to find and execute poetry directly
        $poetryPaths = @(
            "$env:APPDATA\Python\Scripts\poetry.exe",
            "$env:USERPROFILE\.local\bin\poetry.exe",
            "$env:USERPROFILE\AppData\Roaming\Python\Scripts\poetry.exe"
        )
        
        $poetryExecuted = $false
        foreach ($path in $poetryPaths) {
            if (Test-Path $path) {
                & $path install
                Write-Host "Dependencies installed successfully using direct poetry execution" -ForegroundColor Green
                $poetryExecuted = $true
                break
            }
        }
        
        if (-not $poetryExecuted) {
            throw "Could not find or execute poetry"
        }
    }
}
catch {
    Write-Host "ERROR: Failed to install dependencies: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "You may need to:" -ForegroundColor Yellow
    Write-Host "1. Restart your terminal to refresh PATH" -ForegroundColor Yellow
    Write-Host "2. Run 'poetry install' manually after restarting" -ForegroundColor Yellow
    exit 1
}

# Ask user if they want to install test dependencies
$installTests = Read-Host "`nDo you want to install test dependencies (pytest, black, isort)? (y/N)"
if ($installTests -match "^[Yy]") {
    Write-Host "Installing test dependencies..." -ForegroundColor Yellow
    try {
        if (Test-Command "poetry") {
            poetry install --with test
        } else {
            # Try direct execution
            $poetryPaths = @(
                "$env:APPDATA\Python\Scripts\poetry.exe",
                "$env:USERPROFILE\.local\bin\poetry.exe",
                "$env:USERPROFILE\AppData\Roaming\Python\Scripts\poetry.exe"
            )
            
            foreach ($path in $poetryPaths) {
                if (Test-Path $path) {
                    & $path install --with test
                    break
                }
            }
        }
        Write-Host "Test dependencies installed successfully" -ForegroundColor Green
    }
    catch {
        Write-Host "WARNING: Failed to install test dependencies: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

# Check if Graphviz is available (required for diagram generation)
Write-Host "`nChecking Graphviz installation..." -ForegroundColor Yellow

if (-not (Test-Command "dot")) {
    Write-Host "WARNING: Graphviz 'dot' command not found in PATH" -ForegroundColor Yellow
    Write-Host "TerraVision requires Graphviz for diagram generation" -ForegroundColor Yellow
    Write-Host "Please install Graphviz:" -ForegroundColor Yellow
    Write-Host "  - Windows: Download from https://graphviz.org/download/" -ForegroundColor Yellow
    Write-Host "  - Or use: winget install graphviz" -ForegroundColor Yellow
    Write-Host "  - Or use: choco install graphviz" -ForegroundColor Yellow
} else {
    $graphvizVersion = dot -V 2>&1
    Write-Host "Found: $graphvizVersion" -ForegroundColor Green
}

# Installation complete
Write-Host "`n=== Installation Complete ===" -ForegroundColor Cyan
Write-Host "TerraVision prerequisites have been installed!" -ForegroundColor Green
Write-Host "`nTo get started:" -ForegroundColor White
Write-Host "  1. Restart your terminal (recommended)" -ForegroundColor White
Write-Host "  2. Activate the virtual environment: poetry shell" -ForegroundColor White
Write-Host "  3. Run TerraVision: python terravision --help" -ForegroundColor White
Write-Host "  4. See README.md for usage examples" -ForegroundColor White

if (-not (Test-Command "dot")) {
    Write-Host "`nREMEMBER: Install Graphviz for diagram generation!" -ForegroundColor Yellow
}

Write-Host "`nFor more information, visit: https://github.com/j00x/terraform-autodiagram" -ForegroundColor Cyan
