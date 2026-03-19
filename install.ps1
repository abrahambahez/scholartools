param([switch]$Uninstall)

$ErrorActionPreference = "Stop"

$Repo    = "abrahambahez/scholartools"
$BinDir  = "$env:LOCALAPPDATA\Programs\scht"
$CfgDir  = "$env:USERPROFILE\.config\scholartools"
$CfgFile = "$CfgDir\config.json"

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
$pathScope = if ($isAdmin) { "Machine" } else { "User" }

if ($Uninstall) {
    if (Test-Path $BinDir) {
        Remove-Item -Recurse -Force $BinDir
        Write-Host "Removed $BinDir"
    }
    Write-Host ""
    Write-Host "WARNING: $CfgDir contains your library settings (paths, API keys, sources)."
    $confirm = Read-Host "Delete config directory? This cannot be undone. Type Y to confirm"
    if ($confirm -eq "Y") {
        Remove-Item -Recurse -Force $CfgDir
        Write-Host "Removed $CfgDir"
    } else {
        Write-Host "Config directory left intact."
    }
    exit 0
}

Write-Host "Fetching latest scholartools release..."
$release = Invoke-RestMethod "https://api.github.com/repos/$Repo/releases/latest"
$version = $release.tag_name
if (-not $version) { Write-Error "Could not determine latest release."; exit 1 }
Write-Host "Installing scht $version"

$versionNum = $version.TrimStart("v")
$filename   = "scht-$versionNum-windows-x86_64.zip"
$url        = "https://github.com/$Repo/releases/download/$version/$filename"
$tmp        = Join-Path ([System.IO.Path]::GetTempPath()) ([System.IO.Path]::GetRandomFileName())
New-Item -ItemType Directory -Path $tmp | Out-Null

Write-Host "Downloading $filename..."
Invoke-WebRequest -Uri $url -OutFile "$tmp\$filename"
Expand-Archive -Path "$tmp\$filename" -DestinationPath $tmp

New-Item -ItemType Directory -Force -Path $BinDir | Out-Null
Copy-Item "$tmp\scht\scht.exe" "$BinDir\scht.exe" -Force
Remove-Item -Recurse -Force $tmp

$currentPath = [Environment]::GetEnvironmentVariable("Path", $pathScope)
if ($currentPath -notlike "*$BinDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$currentPath;$BinDir", $pathScope)
    Write-Host "Added $BinDir to $pathScope PATH (restart your terminal to apply)."
}

Write-Host ""
Write-Host "scht $version installed to $BinDir\scht.exe"

if (Test-Path $CfgFile) {
    Write-Host ""
    Write-Host "Config already exists at $CfgFile — skipping setup."
    exit 0
}

Write-Host ""
Write-Host "── Initial setup ────────────────────────────────────────────────────────"
Write-Host ""

$email = Read-Host "Scholar email (used for polite API access, e.g. you@uni.edu)"

Write-Host ""
Write-Host "Where should your library live?"
Write-Host "  1) $env:LOCALAPPDATA\scholartools  (default)"
Write-Host "  2) $env:USERPROFILE\Documents\scholartools"
Write-Host "  3) Custom path"
$choice = Read-Host "Choice [1]"
$libraryDir = switch ($choice) {
    "2"     { "$env:USERPROFILE\Documents\scholartools" }
    "3"     { Read-Host "Enter full path" }
    default { "$env:LOCALAPPDATA\scholartools" }
}
Write-Host "Library: $libraryDir"

Write-Host ""
Write-Host "Enable search sources (press Enter to keep, 'n' to disable):"
$allSources = @("crossref","semantic_scholar","arxiv","openalex","doaj","google_books")
$sourcesJson = @()
foreach ($src in $allSources) {
    $ans = Read-Host "  $src? [Y/n]"
    $enabled = if ($ans -match '^[nN]') { "false" } else { "true" }
    $sourcesJson += "{`"name`":`"$src`",`"enabled`":$enabled}"
}

New-Item -ItemType Directory -Force -Path $CfgDir | Out-Null

$libraryDirJson = $libraryDir.Replace("\", "/")

@"
{
  "backend": "local",
  "local": {
    "library_dir": "$libraryDirJson"
  },
  "apis": {
    "email": "$email",
    "sources": [$($sourcesJson -join ",")]
  },
  "llm": {
    "model": "claude-sonnet-4-6"
  }
}
"@ | Set-Content -Path $CfgFile -Encoding UTF8

Write-Host ""
Write-Host "Config written to $CfgFile"
Write-Host "Run 'scht --help' to get started."
