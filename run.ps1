# BattleBots Tournament Manager Bootstrap Installer & Launcher
# This script will check for Python, install it if needed, download the manager files, and launch the application.

$GITHUB_REPO = "https://github.com/NathLara/Battle-Bot-Repo"

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "     BATTLEBOTS TOURNAMENT MANAGER LAUNCHER  " -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

# 1. Check if we are running in a directory that already contains the app files
if ((Test-Path "launcher.py") -and (Test-Path "server.py")) {
    $installDir = $PWD.Path
    Write-Host "Running from existing local directory: $installDir" -ForegroundColor Green
} else {
    $installDir = Join-Path $env:USERPROFILE "BattleBotsManager"
    Write-Host "App files not found locally. Installation directory: $installDir" -ForegroundColor Yellow
}

# 2. Check for Python 3 installation
$pythonInstalled = $false
try {
    # Try running python --version
    $pythonVersion = & python --version 2>&1
    if ($lastExitCode -eq 0 -or $pythonVersion -match "Python 3") {
        $pythonInstalled = $true
    }
} catch {}

if (-not $pythonInstalled) {
    # Try py launcher
    try {
        $pyVersion = & py -3 --version 2>&1
        if ($lastExitCode -eq 0) {
            $pythonInstalled = $true
            function python { & py -3 $args }
        }
    } catch {}
}

if (-not $pythonInstalled) {
    Write-Host "Python 3 was not found on your system." -ForegroundColor Yellow
    Write-Host "Attempting to install Python via Windows Package Manager (winget)..." -ForegroundColor Cyan
    
    # Try using winget to install python
    try {
        & winget install --id Python.Python.3 --silent --accept-source-agreements --accept-package-agreements
        Write-Host "Python installation triggered. Refreshing path variables..." -ForegroundColor Green
        
        # Refresh environment variables
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        
        # Verify installation
        $pythonVersion = & python --version 2>&1
        if ($lastExitCode -eq 0 -or $pythonVersion -match "Python 3") {
            $pythonInstalled = $true
            Write-Host "Python 3 successfully installed!" -ForegroundColor Green
        } else {
            throw "Python check failed after installation"
        }
    } catch {
        Write-Host "`n[ERROR] Automated Python installation failed or requires a system reboot." -ForegroundColor Red
        Write-Host "Please download and install Python manually from: https://www.python.org/downloads/" -ForegroundColor Red
        Write-Host "Make sure to check 'Add Python to PATH' during installation, then re-run this command." -ForegroundColor Red
        Read-Host "Press Enter to exit..."
        exit 1
    }
}

# 3. Create install dir and download files if needed
if ($installDir -eq (Join-Path $env:USERPROFILE "BattleBotsManager")) {
    if (-not (Test-Path $installDir)) {
        New-Item -ItemType Directory -Path $installDir | Out-Null
    }
    
    # Check if download is necessary
    if (-not ((Test-Path (Join-Path $installDir "launcher.py")) -and (Test-Path (Join-Path $installDir "server.py")))) {
        if ($GITHUB_REPO -eq "PLACEHOLDER_GITHUB_REPO") {
            Write-Host "[ERROR] This bootstrap script has placeholders and is not configured with a GitHub repository yet." -ForegroundColor Red
            Write-Host "Please run upload_to_github.ps1 first to publish your project and initialize this script." -ForegroundColor Red
            Read-Host "Press Enter to exit..."
            exit 1
        }
        
        $tempZip = Join-Path $env:TEMP "battlebots_temp.zip"
        if (Test-Path $tempZip) { Remove-Item $tempZip -Force }
        
        $zipUrl = "$GITHUB_REPO/archive/refs/heads/main.zip"
        Write-Host "Downloading BattleBots Manager source files from $zipUrl..." -ForegroundColor Cyan
        try {
            Invoke-WebRequest -Uri $zipUrl -OutFile $tempZip -ErrorAction Stop
        } catch {
            Write-Host "Could not download main branch. Trying master branch..." -ForegroundColor Yellow
            $zipUrl = "$GITHUB_REPO/archive/refs/heads/master.zip"
            try {
                Invoke-WebRequest -Uri $zipUrl -OutFile $tempZip -ErrorAction Stop
            } catch {
                Write-Host "[ERROR] Failed to download repository ZIP from GitHub. URL tried: $zipUrl" -ForegroundColor Red
                Write-Host $_.Exception.Message -ForegroundColor Red
                Read-Host "Press Enter to exit..."
                exit 1
            }
        }
        
        Write-Host "Extracting files..." -ForegroundColor Cyan
        $tempExtractDir = Join-Path $env:TEMP "battlebots_extract"
        if (Test-Path $tempExtractDir) { Remove-Item $tempExtractDir -Recurse -Force }
        New-Item -ItemType Directory -Path $tempExtractDir | Out-Null
        
        Expand-Archive -Path $tempZip -DestinationPath $tempExtractDir -Force
        
        # Find the extracted folder (usually repository-main or repository-master)
        $extractedSubDir = Get-ChildItem -Path $tempExtractDir -Directory | Select-Object -First 1
        if ($extractedSubDir) {
            Get-ChildItem -Path $extractedSubDir.FullName | ForEach-Object {
                Copy-Item -Path $_.FullName -Destination $installDir -Recurse -Force
            }
            Write-Host "Files successfully downloaded and placed in: $installDir" -ForegroundColor Green
        } else {
            Write-Host "[ERROR] Extracted ZIP archive was empty or invalid." -ForegroundColor Red
            Read-Host "Press Enter to exit..."
            exit 1
        }
        
        # Clean up temp files
        Remove-Item $tempZip -Force
        Remove-Item $tempExtractDir -Recurse -Force
    }
}

# Change location to the install directory
Set-Location -Path $installDir

# 4. Set up virtual environment
$venvDir = Join-Path $installDir ".venv"
$pipExe = Join-Path $venvDir "Scripts\pip.exe"
$pythonExe = Join-Path $venvDir "Scripts\python.exe"

if (-not (Test-Path $venvDir)) {
    Write-Host "Creating Python virtual environment..." -ForegroundColor Cyan
    & python -m venv $venvDir
    if (-not (Test-Path $pythonExe)) {
        Write-Host "[ERROR] Failed to create virtual environment." -ForegroundColor Red
        Read-Host "Press Enter to exit..."
        exit 1
    }
}

# 5. Install / Update dependencies
Write-Host "Installing/Verifying Python dependencies..." -ForegroundColor Cyan
& $pipExe install -r requirements.txt --quiet
if ($lastExitCode -ne 0) {
    Write-Host "[WARNING] Installing dependencies failed. Retrying..." -ForegroundColor Yellow
    & $pipExe install fastapi uvicorn[standard] pydantic websockets --quiet
}

# 6. Launch the application
Write-Host "Launching BattleBots Tournament Manager..." -ForegroundColor Green
Start-Process -FilePath $pythonExe -ArgumentList "launcher.py" -WorkingDirectory $installDir
