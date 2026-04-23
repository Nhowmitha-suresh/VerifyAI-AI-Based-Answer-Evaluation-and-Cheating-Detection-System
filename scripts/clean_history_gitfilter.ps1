<#
PowerShell helper to clean repository history using git-filter-repo.
Run this from a directory outside your working repo. It will create a mirror clone, remove listed paths, and force-push the cleaned history.

WARNING: This rewrites history. All collaborators must re-clone after the force-push.
#>

param(
  [string]$repoUrl = 'https://github.com/Nhowmitha-suresh/VerifyAI-AI-Based-Answer-Evaluation-and-Cheating-Detection-System.git',
  [string]$pathsFile = 'scripts/paths-to-remove.txt'
)

if(-not (Get-Command git -ErrorAction SilentlyContinue)){
  Write-Error 'git is not installed or not in PATH.'; exit 1
}

Write-Host 'Ensure you have a backup of your repository before proceeding.' -ForegroundColor Yellow
Read-Host 'Press Enter to continue (or Ctrl+C to abort)'

# Ensure git-filter-repo is available
try{
  git filter-repo --help > $null 2>&1
}catch{
  Write-Host 'git-filter-repo not found. Install via: pip install git-filter-repo' -ForegroundColor Yellow
  exit 1
}

$mirrorDir = 'repo-mirror.git'
if(Test-Path $mirrorDir){ Remove-Item -Recurse -Force $mirrorDir }

Write-Host "Cloning mirror of $repoUrl ..."
git clone --mirror $repoUrl $mirrorDir
if($LASTEXITCODE -ne 0){ Write-Error 'git clone --mirror failed'; exit 1 }

Set-Location $mirrorDir

Write-Host "Running git-filter-repo to remove paths listed in ../$pathsFile ..."
git filter-repo --invert-paths --paths-from-file ../$pathsFile
if($LASTEXITCODE -ne 0){ Write-Error 'git filter-repo failed'; exit 1 }

Write-Host 'Cleaning up reflogs and running garbage collection...'
git reflog expire --expire=now --all
git gc --prune=now --aggressive

Write-Host 'Force-pushing cleaned history to origin. This will overwrite remote history.' -ForegroundColor Red
Read-Host 'Press Enter to force-push (or Ctrl+C to abort)'
git push --force
if($LASTEXITCODE -ne 0){ Write-Error 'git push --force failed'; exit 1 }

Write-Host 'Done. Repository history cleaned and pushed.' -ForegroundColor Green
Write-Host 'Remember to ask collaborators to re-clone the repository.'
