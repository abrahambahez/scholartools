[CmdletBinding()]
param(
    [string]$Lang = "en",
    [switch]$Uninstall
)

$SkillsDir = if ($env:CLAUDE_SKILLS_DIR) { $env:CLAUDE_SKILLS_DIR } else { "$env:APPDATA\Claude\skills" }
$Repo = "abrahambahez/scholartools"

if ($Uninstall) {
    Get-ChildItem -Path $SkillsDir -Directory -Filter "scholartools-*" -ErrorAction SilentlyContinue |
        Remove-Item -Recurse -Force
    Write-Host "Uninstalled scholartools skills from $SkillsDir"
    exit 0
}

$Release = Invoke-RestMethod "https://api.github.com/repos/$Repo/releases/latest"
$Asset = $Release.assets | Where-Object { $_.name -like "scholartools-skills-$Lang-*.zip" } | Select-Object -First 1

if (-not $Asset) {
    Write-Error "No skills asset found for language '$Lang'"
    exit 1
}

$Tmp = New-TemporaryFile | ForEach-Object { $_.DirectoryName + "\" + $_.BaseName + "_skills" }
New-Item -ItemType Directory -Path $Tmp | Out-Null

try {
    Invoke-WebRequest -Uri $Asset.browser_download_url -OutFile "$Tmp\skills.zip"
    Expand-Archive -Path "$Tmp\skills.zip" -DestinationPath "$Tmp\extracted" -Force
    New-Item -ItemType Directory -Path $SkillsDir -Force | Out-Null

    Get-ChildItem -Path "$Tmp\extracted" -Directory | ForEach-Object {
        $dest = Join-Path $SkillsDir $_.Name
        if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
        Copy-Item $_.FullName $dest -Recurse
        Write-Host "Installed: $($_.Name)"
    }
} finally {
    Remove-Item $Tmp -Recurse -Force -ErrorAction SilentlyContinue
}
