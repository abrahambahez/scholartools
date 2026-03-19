$ErrorActionPreference = "Stop"

$Repo    = "abrahambahez/scholartools"
$BinDir  = "$env:LOCALAPPDATA\Programs\scht"
$CfgDir  = "$env:USERPROFILE\.config\scholartools"
$CfgFile = "$CfgDir\config.json"

# ── fetch latest release ───────────────────────────────────────────────────────
Write-Host "Fetching latest scholartools release..."
$release = Invoke-RestMethod "https://api.github.com/repos/$Repo/releases/latest"
$version = $release.tag_name
if (-not $version) { Write-Error "Could not determine latest release."; exit 1 }
Write-Host "Installing scht $version"

# ── download & extract ────────────────────────────────────────────────────────
$versionNum = $version.TrimStart("v")
$filename   = "scht-$versionNum-windows-x86_64.zip"
$url        = "https://github.com/$Repo/releases/download/$version/$filename"
$tmp        = New-TemporaryFile | ForEach-Object { $_.FullName + "_dir" }
New-Item -ItemType Directory -Path $tmp | Out-Null

Write-Host "Downloading $filename..."
Invoke-WebRequest -Uri $url -OutFile "$tmp\$filename"
Expand-Archive -Path "$tmp\$filename" -DestinationPath $tmp

New-Item -ItemType Directory -Force -Path $BinDir | Out-Null
Copy-Item "$tmp\scht\scht.exe" "$BinDir\scht.exe" -Force
Remove-Item -Recurse -Force $tmp

# ── ensure PATH ───────────────────────────────────────────────────────────────
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$BinDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$BinDir", "User")
    Write-Host "Added $BinDir to your user PATH (restart your terminal to apply)."
}

Write-Host ""
Write-Host "scht $version installed to $BinDir\scht.exe"

# ── config setup ──────────────────────────────────────────────────────────────
if (Test-Path $CfgFile) {
    Write-Host ""
    Write-Host "Config already exists at $CfgFile — skipping setup."
    exit 0
}

Write-Host ""
Write-Host "── Initial setup ────────────────────────────────────────────────────────"
Write-Host ""

# email
$email = Read-Host "Scholar email (used for polite API access, e.g. you@uni.edu)"

# library path
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

# sources
Write-Host ""
Write-Host "Enable search sources (press Enter to keep, 'n' to disable):"
$allSources = @("crossref","semantic_scholar","arxiv","openalex","doaj","google_books")
$sourcesJson = @()
foreach ($src in $allSources) {
    $ans = Read-Host "  $src? [Y/n]"
    $enabled = if ($ans -match '^[nN]') { "false" } else { "true" }
    $sourcesJson += "{`"name`":`"$src`",`"enabled`":$enabled}"
}

# ── write config ──────────────────────────────────────────────────────────────
New-Item -ItemType Directory -Force -Path $CfgDir | Out-Null

# Normalize Windows backslashes to forward slashes for JSON
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
