# Helper script to upload BattleBots Manager to GitHub
# It initializes Git, prompts for the repo URL, updates run.ps1, commits, and pushes.

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "   BATTLEBOTS MANAGER GITHUB UPLOADER        " -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

# 1. Ensure Git is installed
$gitInstalled = $false
try {
    $gitVer = & git --version 2>&1
    if ($lastExitCode -eq 0) {
        $gitInstalled = $true
    }
} catch {}

if (-not $gitInstalled) {
    Write-Host "[ERROR] Git is not installed or not in the PATH." -ForegroundColor Red
    Write-Host "Please install Git from https://git-scm.com/ and try again." -ForegroundColor Red
    Read-Host "Press Enter to exit..."
    exit 1
}

# 2. Get repository URL from the user
Write-Host "Please enter your GitHub Repository URL." -ForegroundColor Yellow
Write-Host "If you haven't created one yet, go to: https://github.com/new" -ForegroundColor Yellow
Write-Host "Create a blank repository (do NOT add README, .gitignore, or license)." -ForegroundColor Yellow
Write-Host ""
$repoUrl = Read-Host "GitHub Repository URL (e.g. https://github.com/username/repo-name)"
$repoUrl = $repoUrl.Trim()

if (-not $repoUrl) {
    Write-Host "[ERROR] Repository URL cannot be empty." -ForegroundColor Red
    Read-Host "Press Enter to exit..."
    exit 1
}

# Ensure HTTPS url is clean (strip trailing .git)
$cleanUrl = $repoUrl
if ($cleanUrl.EndsWith(".git")) {
    $cleanUrl = $cleanUrl.Substring(0, $cleanUrl.Length - 4)
}

# 3. Update the GITHUB_REPO variable in run.ps1
$runPs1Path = Join-Path $PWD.Path "run.ps1"
if (Test-Path $runPs1Path) {
    $content = Get-Content -Path $runPs1Path -Raw
    # Replace any existing $GITHUB_REPO assignment with the clean URL
    $newContent = $content -replace '\$GITHUB_REPO = ".*"', "`$GITHUB_REPO = `"$cleanUrl`""
    Set-Content -Path $runPs1Path -Value $newContent -Force
    Write-Host "Updated run.ps1 with target repository URL." -ForegroundColor Green
} else {
    Write-Host "[WARNING] run.ps1 not found in current directory. Skipping URL injection." -ForegroundColor Yellow
}

# 4. Initialize Git and commit
Write-Host "`nInitializing local git repository..." -ForegroundColor Cyan
if (-not (Test-Path ".git")) {
    & git init
}

# Configure default branch to main
& git branch -M main

Write-Host "Staging files..." -ForegroundColor Cyan
& git add .

Write-Host "Committing files..." -ForegroundColor Cyan
& git commit -m "Initial commit: BattleBots Tournament Manager"

# 5. Set up remote and push
Write-Host "Setting remote origin..." -ForegroundColor Cyan
$existingRemote = & git remote get-url origin 2>&1
if ($lastExitCode -eq 0) {
    & git remote set-url origin $repoUrl
} else {
    & git remote add origin $repoUrl
}

Write-Host "`nUploading files to GitHub. You may be prompted for authentication..." -ForegroundColor Yellow
& git push -u origin main --force

if ($lastExitCode -eq 0) {
    Write-Host "`n=======================================================" -ForegroundColor Green
    Write-Host " SUCCESS: BattleBots Tournament Manager uploaded!      " -ForegroundColor Green
    Write-Host "=======================================================" -ForegroundColor Green
    
    # Parse username and repo name for the launcher command
    if ($cleanUrl -match "github.com/([^/]+)/([^/]+)") {
        $username = $Matches[1]
        $repoName = $Matches[2]
        $rawUrlCmd = "irm https://raw.githubusercontent.com/$username/$repoName/main/run.ps1 | iex"
        
        Write-Host "To download and run this launcher on any Windows PC," -ForegroundColor Cyan
        Write-Host "copy and run the following command in your terminal:" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "  $rawUrlCmd" -ForegroundColor White -BackgroundColor DarkCyan
        Write-Host ""
    } else {
        Write-Host "Successfully pushed! You can find raw link to run.ps1 on your repository page." -ForegroundColor Cyan
    }
} else {
    Write-Host "`n[ERROR] Failed to push code to GitHub. Please check your network, credentials, and repository URL." -ForegroundColor Red
}

Read-Host "Press Enter to finish..."
