# feat 014: CLI build — standalone executables for Claude Desktop distribution

version: 0.1
status: current

## what it is

A build and distribution layer that packages the `scht` CLI as a standalone executable for each supported platform — no Python or uv required at the user's site. Researchers download a single directory bundle, run an install script, and `scht` is on their PATH.

## who it's for

Researchers using scholartools via Claude Desktop skills, who should not need to install Python, manage virtual environments, or understand package managers. The install experience is: download, run script, done.

## the distribution model

Each GitHub release publishes three platform zip assets and two standalone install scripts:

- `scht-<version>-macos-arm64.zip`
- `scht-<version>-linux-x86_64.zip`
- `scht-<version>-windows-x86_64.zip`

macOS x86_64 is not built — GitHub's `macos-12` (Intel) runner was removed and `macos-13` is available but deferred until a user requests it.
- `install.sh` (macOS/Linux bootstrapper)
- `install.ps1` (Windows bootstrapper)

Each archive contains a directory bundle (not a single fat binary) — faster startup than onefile packaging. The top-level binary is named `scht` on macOS/Linux and `scht.exe` on Windows.

**Install scripts are not bundled inside the zips.** They are standalone bootstrappers uploaded as separate release assets. A researcher runs the script once (like installing Homebrew or winget) — it downloads the correct platform zip, extracts the binary to a PATH location, persists the PATH entry, and interactively creates an initial `~/.config/scholartools/config.json` (email, library path, enabled sources).

## build pipeline

GitHub Actions matrix build — one runner per OS (macOS arm64, Linux x86_64, Windows x86_64), triggered on version tags (`v*`). Each runner produces its platform zip and uploads it as a release asset. The Linux runner additionally uploads `install.sh` and `install.ps1` as release assets. The version string is stamped into the binary from `pyproject.toml` at build time, surfaced via `scht --version`.

PyInstaller is used to produce the bundles. Hidden imports for `pdfplumber` are declared explicitly in the build spec. The previous references to `cryptography` and `minio` hidden imports are removed — those dependencies were stripped from core in v0.13.0 (spec 027) and will not reappear until plugin zips are introduced.

Environment variables (API keys, config paths) are entirely the user's responsibility at runtime — nothing is baked into the build.

## success criteria

- A researcher on macOS, Linux, or Windows can run the install script and have `scht` on their PATH without Python installed
- `scht refs list` works correctly in the installed bundle
- `scht --version` reports the correct release version
- GitHub Actions publishes all three platform zips plus both install scripts on every version tag push
