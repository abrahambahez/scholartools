# spec: 014-cli-build — PyInstaller bundles for standalone distribution

## findings

From docs/feats/014-cli-build.md:

The `scht` CLI (completed in spec 012-cli) currently requires Python, uv, and a virtual environment at the user's site. The goal is to package it as standalone executables for distribution alongside Claude Desktop skills.

**Distribution model:**
- Four platform bundles (macOS arm64, macOS x86_64, Linux x86_64, Windows x86_64)
- Each published as a `.zip` containing a directory bundle (not a single fat binary)
- Faster startup and reduced friction compared to onefile PyInstaller approach
- Top-level binary: `scht` (macOS/Linux) or `scht.exe` (Windows)

**Build pipeline:**
- GitHub Actions matrix build triggered on version tags (`v*`)
- One runner per OS platform
- PyInstaller used to bundle the CLI with hidden imports for `pdfplumber`, `cryptography`, `minio`
- Version string stamped from `pyproject.toml` into the binary
- Exposed via `scht --version`

**User expectations:**
- Unzip bundle, run install script, `scht` on PATH
- No Python or uv dependency at user's site
- `scht --version` reports correct release version
- `scht refs list` works correctly
- All four platform zips published on every version tag

## objective

Build and release a PyInstaller-based distribution pipeline that packages the `scht` CLI as standalone, zero-dependency executables for macOS, Linux, and Windows. Researchers download a platform-specific zip, run an install script, and use `scht` without managing Python or virtual environments. GitHub Actions handles multi-platform builds triggered by version tags; each build includes hidden imports for dependencies (pdfplumber, cryptography, boto3/botocore) and stamps the version from `pyproject.toml` into the binary.

## acceptance criteria (EARS format)

- when a version tag `v*` is pushed, the system must trigger a GitHub Actions matrix build
- when the GitHub Actions build completes, the system must publish exactly four `.zip` assets to the release: `scht-<version>-macos-arm64.zip`, `scht-<version>-macos-x86_64.zip`, `scht-<version>-linux-x86_64.zip`, `scht-<version>-windows-x86_64.zip`
- when a researcher on macOS downloads and unzips `scht-<version>-macos-arm64.zip`, the system must contain a top-level `scht` binary executable on that platform
- when a researcher on Linux downloads and unzips `scht-<version>-linux-x86_64.zip`, the system must contain a top-level `scht` binary executable
- when a researcher on Windows downloads and unzips `scht-<version>-windows-x86_64.zip`, the system must contain a top-level `scht.exe` binary executable
- when the researcher runs `./scht --version` from the unzipped bundle (without Python installed), the system must exit 0 and print the correct release version
- when the researcher runs `./scht refs list` from the unzipped bundle, the system must execute successfully and return library references in JSON format
- when a PyInstaller bundle is built, the system must include pdfplumber, cryptography, and minio as hidden imports regardless of direct imports at the CLI entry point
- when `scht --version` is called, the system must report the version string from `pyproject.toml` (not a stale hardcoded value)
- when a researcher unpacks the bundle and adds the directory to their PATH, the system must allow them to call `scht` from any working directory

## tasks

- [x] task-01: create PyInstaller spec file and build configuration (blocks: none)
  - Create `.build/pyinstaller.spec` (or similar) with entry point, hidden imports, and bundle layout
  - Include `pdfplumber`, `cryptography`, `minio` as hidden imports
  - Configure bundle output structure: `dist/scht/` for each platform
  - Document platform-specific overrides (exe name, signed binary paths, etc.)

- [x] task-02: add version stamping to the CLI binary (blocks: task-01)
  - Read version from `pyproject.toml` at build time (PyInstaller hook or pre-build step)
  - Inject version string into a module or environment variable before bundling
  - Verify `scht --version` reports the correct version from the bundle
  - Unit test: mock `pyproject.toml`, confirm version in `--version` output

- [x] task-03: create GitHub Actions matrix build workflow (blocks: task-02)
  - Create `.github/workflows/build-release.yml` (or similar)
  - Matrix: macOS (arm64, x86_64), Linux (x86_64), Windows (x86_64)
  - Trigger: on version tags (`v*`)
  - Each runner: install uv, sync deps, run PyInstaller, zip bundle, upload to release
  - Ensure version is passed to PyInstaller and stamped into binary

- [x] task-04: create install script and distribution layout (blocks: task-03)
  - Create install script (shell for macOS/Linux, batch/ps1 for Windows) in each bundle
  - Script copies `scht` binary to a system PATH location or user bin directory
  - Verify script is included in all four zips

- [ ] task-05: smoke test the release pipeline (blocks: task-04)
  - Tag a test version locally (e.g., `v0.1.0-test`)
  - Verify GitHub Actions builds all four platforms
  - Download and unzip each bundle; run `./scht --version` and `./scht refs list`
  - Confirm exit codes are correct and output is valid JSON
  - Clean up test tag

## ADR required?

No. PyInstaller is a standard tool for Python CLI distribution; no architectural decisions needed.

## risks

1. **Hidden import incomplete.** If `minio`, `pdfplumber`, or `cryptography` have transitive imports not listed, the binary may fail at runtime. Mitigation: test each platform; add missing imports iteratively.

2. **Platform-specific failures.** macOS arm64/x86_64 and Linux paths may differ (glibc versions, library paths). Mitigation: CI runs on GitHub's native runners; test before committing.

3. **Version stamping fragility.** If version injection uses dynamic imports or runtime exec, the bundled binary may report stale versions. Mitigation: encode version at build time as a constant.

4. **Binary bloat.** PyInstaller bundles entire interpreter and dependencies (100+ MB). Accept trade-off for convenience; document in release notes.

5. **macOS signing/notarization.** macOS may require code signing for smooth UX. Mitigation: defer to follow-on; document workaround for now.
