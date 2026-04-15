# spec: 020-install-scripts — canonical install scripts at repo root

## objective

Replace the current `.build/install.sh` and `.build/install.ps1` with two canonical scripts at the repo root: `install.sh` (macOS + Linux) and `install.ps1` (Windows). These scripts are the official installation method for end users. They are maintained in the repo, versioned with the code, and have no relation to the CI/CD build pipeline. The README exposes them as one-liner commands.

## context

- `scht` binaries are published as GitHub release assets (built by spec 018-cli-build)
- Scripts fetch the latest release from the GitHub API and download the correct platform zip
- Scripts are standalone — they are not generated, bundled, or uploaded by CI; they live and are updated directly in the repo
- Existing `.build/install.sh` and `.build/install.ps1` must be deleted

## acceptance criteria (EARS format)

- when a macOS or Linux user runs `curl -fsSL https://raw.githubusercontent.com/abrahambahez/scholartools/main/install.sh | bash`, the system must detect the OS and architecture, download the correct binary zip from the latest GitHub release, install the binary to a directory on PATH, and make it permanently accessible in new shell sessions
- when a Windows user runs `irm https://raw.githubusercontent.com/abrahambahez/scholartools/main/install.ps1 | iex` in an elevated PowerShell session, the system must download the correct binary zip, install the binary to `%LOCALAPPDATA%\Programs\scht`, and add that directory to the user's permanent PATH via the registry
- when `install.sh` is run on macOS (arm64), the system must select the `scht-<version>-macos-arm64.zip` asset
- when `install.sh` is run on Linux (x86_64), the system must select the `scht-<version>-linux-x86_64.zip` asset
- when `install.sh` is run on an unsupported OS or architecture, the system must print a clear error and exit non-zero
- when either script is run and an existing installation is detected, the system must update the binary in place without re-running the config setup
- when either script is run for the first time (no config file present), the system must interactively create a config file in the OS-appropriate location: `~/.config/scholartools/config.json` on macOS/Linux, `%USERPROFILE%\.config\scholartools\config.json` on Windows
- when the config setup runs, the system must prompt for: scholar email, library directory (with OS-appropriate defaults), and search source toggles
- when either script is invoked with `--uninstall`, the system must remove the binary, then print a warning that the config directory contains library settings and ask for explicit confirmation before deleting it; if the user declines, the config directory must be left intact
- when installation completes, the user must be able to run `scht --help` and `scht refs list` in a new shell session
- when the README install section is viewed, the user must see exactly two commands — one for macOS/Linux and one for Windows — with no other installation method listed as primary

## tasks

- [x] task-01: write `install.sh` at repo root (blocks: none)
  - detect OS via `uname -s` (Darwin vs Linux) and arch via `uname -m` (arm64/aarch64 vs x86_64)
  - map to correct asset name: `scht-<version>-macos-arm64.zip` or `scht-<version>-linux-x86_64.zip`
  - fetch latest version from GitHub API (`/repos/abrahambahez/scholartools/releases/latest`)
  - download zip to tmp dir, extract binary, copy to `~/.local/bin/scht`, chmod +x
  - add `~/.local/bin` to PATH in `.bashrc`, `.zshrc`, `.profile` if not already present
  - skip config setup if `~/.config/scholartools/config.json` already exists (update path)
  - run interactive config setup on first install
  - support `--uninstall`: remove binary, print a warning that config contains library settings, then prompt for explicit confirmation before deleting `~/.config/scholartools/`; abort config deletion if user declines
  - delete `.build/install.sh`

- [x] task-02: write `install.ps1` at repo root (blocks: none)
  - fetch latest version from GitHub API
  - download `scht-<version>-windows-x86_64.zip` to temp dir
  - extract to `%LOCALAPPDATA%\Programs\scht\`
  - add install dir to user PATH via `[Environment]::SetEnvironmentVariable` (Machine scope if admin, User scope otherwise)
  - skip config setup if `%USERPROFILE%\.config\scholartools\config.json` already exists (update path)
  - run interactive config setup on first install
  - support `-Uninstall` switch: remove binary dir, print a warning that config contains library settings, then prompt for explicit confirmation before deleting `%USERPROFILE%\.config\scholartools\`; abort config deletion if user declines
  - delete `.build/install.ps1`

- [x] task-03: update README (blocks: task-01, task-02)
  - replace current `## install` section with the two one-liner commands as primary method
  - keep `## dev` section for contributors (uv sync approach stays there, not in install)
  - add brief note that re-running the script updates the binary

- [x] task-04: smoke test (blocks: task-01, task-02, task-03)
  - run `install.sh` locally (Linux or macOS) against a real release tag
  - verify `scht --version` and `scht refs list` work in a new shell
  - verify re-run detects existing install and updates without config prompt
  - verify `--uninstall` removes the binary
  - manually verify `install.ps1` on Windows or document as manual QA step

## risks

1. **macOS Gatekeeper.** Downloaded binaries may be quarantined. Mitigation: add `xattr -dr com.apple.quarantine` call after extraction, or document the workaround.
2. **GitHub API rate limit.** Unauthenticated calls to the releases API are limited to 60/hour per IP. Mitigation: acceptable for an install script; document the error message.
3. **Windows execution policy.** `irm | iex` may be blocked by restrictive policies. Mitigation: README notes that an elevated session is required.
4. **PATH persistence.** On macOS/Linux, PATH changes only take effect in new shells. Mitigation: print explicit `export PATH=...` command for the current session.
