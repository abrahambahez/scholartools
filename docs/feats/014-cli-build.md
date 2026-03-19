# feat 014: CLI build — standalone executables for Claude Desktop distribution

## v0.1

## what it is

A build and distribution layer that packages the `scht` CLI as a standalone executable for each supported platform — no Python or uv required at the user's site. Researchers download a single directory bundle, run an install script, and `scht` is on their PATH.

## who it's for

Researchers using scholartools via Claude Desktop skills, who should not need to install Python, manage virtual environments, or understand package managers. The install experience is: download, run script, done.

## the distribution model

Each GitHub release publishes three platform assets as zip archives:

- `scht-<version>-macos-arm64.zip`
- `scht-<version>-macos-x86_64.zip`
- `scht-<version>-linux-x86_64.zip`
- `scht-<version>-windows-x86_64.zip`

Each archive contains a directory bundle (not a single fat binary) — faster startup than onefile packaging, with the same user-facing simplicity. The top-level binary is named `scht` on macOS/Linux and `scht.exe` on Windows.

## build pipeline

GitHub Actions matrix build — one runner per OS, triggered on version tags (`v*`). Each runner produces its platform bundle and uploads it as a release asset. The version string is stamped into the binary from `pyproject.toml` at build time, surfaced via `scht --version`.

PyInstaller is used to produce the bundles. Hidden imports for `pdfplumber`, `cryptography`, and the optional `minio` sync stack are declared explicitly in the build spec so they are included even when not directly imported at the entry point.

Environment variables (API keys, config paths) are entirely the user's responsibility at runtime — nothing is baked into the build.

## success criteria

- A researcher on macOS, Linux, or Windows can unzip the bundle and call `scht --version` without having Python installed
- `scht refs list` works correctly in the installed bundle
- `scht --version` reports the correct release version
- GitHub Actions publishes all four platform zips on every version tag push
