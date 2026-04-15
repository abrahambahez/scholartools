# spec: 025-skills-zip-distribution — packaged skill releases with install scripts

## findings

From docs/feats/025-skills-zip-distribution.md:

Skills (`scholartools-config`, `scholartools-references`, `scholartools-files`,
`scholartools-sync-peers`) exist in `skills/en/` and `skills/es/`. Researchers must
currently copy SKILL.md files manually into Claude Desktop. There is no versioned
artifact and no install script for skills.

**Distribution model:**
- One zip per language published as a GitHub Release asset when any `skills/` file changed
  between the current and previous version tag
- Asset names: `scholartools-skills-en-vX.Y.Z.zip`, `scholartools-skills-es-vX.Y.Z.zip`
- Zip root contains flat skill directories: `scholartools-config/SKILL.md`, etc.
- Two install scripts (`install-skills.sh`, `install-skills.ps1`) published as additional
  release assets, conditional on the same change gate
- Install scripts target `~/.claude/skills/` (macOS/Linux) or `%APPDATA%\Claude\skills\`
  (Windows)
- First-tag edge case: package unconditionally if no previous tag exists

**Changelog discipline enforced in CLAUDE.md:**
- Any version touching `skills/` must include a `### Skills` subsection in CHANGELOG.md

## objective

Add a `package-skills` CI job to `build-release.yml` that detects skill changes, packages
per-language zips, and publishes them alongside two install scripts as GitHub Release
assets. Provide `install-skills.sh` and `install-skills.ps1` that fetch the latest
skills zip, extract it to the Claude Desktop skills directory, and support `--uninstall`.
Add changelog discipline to CLAUDE.md.

## acceptance criteria (EARS format)

- when a `v*` tag is pushed and any file under `skills/` changed since the previous tag,
  the system must publish `scholartools-skills-en-<version>.zip` and
  `scholartools-skills-es-<version>.zip` as GitHub Release assets
- when a `v*` tag is pushed and no file under `skills/` changed since the previous tag,
  the system must NOT publish any `scholartools-skills-*` asset
- when no previous tag exists (first release), the system must publish skill zips
  unconditionally
- when each skills zip is extracted, it must contain exactly three directories at the root
  (`scholartools-config/`, `scholartools-references/`, `scholartools-sync-peers/`),
  each containing a `SKILL.md` file
- when skill zips are published, the system must also publish `install-skills.sh` and
  `install-skills.ps1` as release assets in the same release
- when a researcher runs `install-skills.sh` without arguments on macOS or Linux,
  the system must prompt for language (default `en`), download the latest matching skills
  zip, and extract all skill directories into `~/.claude/skills/`
- when a researcher runs `install-skills.sh --lang es`, the system must install the
  Spanish skills zip without prompting for language
- when a researcher runs `install-skills.sh --uninstall`, the system must remove all
  directories matching `scholartools-*` from `~/.claude/skills/`
- when a researcher runs `install-skills.ps1` on Windows, the system must extract into
  `$env:APPDATA\Claude\skills\`
- when `install-skills.ps1 -Uninstall` is called, the system must remove all
  `scholartools-*` directories from the Windows skills dir
- when a skills release asset is not found for the requested language, both scripts must
  exit non-zero with a clear error message
- when a release touches `skills/`, the CHANGELOG.md entry must include a `### Skills`
  subsection (enforced by CLAUDE.md convention, not CI)

## tasks

- [x] task-01: add `package-skills` job to `build-release.yml` (blocks: none)
  - Run on `ubuntu-latest`, triggered by same `v*` tag condition as existing jobs
  - Determine previous tag: `git describe --tags --abbrev=0 HEAD^` with fallback to
    empty-tree SHA when no previous tag exists
  - Run `git diff --quiet $PREV..HEAD -- skills/` to set `SKILLS_CHANGED`
  - If not changed, exit the job early (use `if: env.SKILLS_CHANGED == 'true'` on
    subsequent steps, or a conditional job-level output)
  - For each language (`en`, `es`): zip `skills/<lang>/*/SKILL.md` preserving directory
    structure from `skills/<lang>/` as root, output
    `scholartools-skills-<lang>-<version>.zip`
  - Upload both zips and `install-skills.sh` / `install-skills.ps1` via
    `softprops/action-gh-release@v2`

- [x] task-02: write `install-skills.sh` (blocks: task-01)
  - Place at `.build/install-skills.sh` (published as release asset, not bundled in zips)
  - Parse `--lang <en|es>` (default `en`) and `--uninstall` flags
  - If `--uninstall`: remove `$HOME/.claude/skills/scholartools-*/` and exit
  - Otherwise: fetch `https://api.github.com/repos/abrahambahez/scholartools/releases/latest`,
    find asset matching `scholartools-skills-<lang>-*.zip`
  - Download to temp dir, extract to `~/.claude/skills/`, print installed dirs, clean up
  - Exit non-zero with message if asset not found or download fails
  - No interactive prompts beyond the language choice when `--lang` is not supplied

- [x] task-03: write `install-skills.ps1` (blocks: task-01)
  - Place at `.build/install-skills.ps1`
  - Params: `-Lang <en|es>` (default `en`), `-Uninstall` switch
  - If `-Uninstall`: remove `$env:APPDATA\Claude\skills\scholartools-*` and exit
  - Otherwise: `Invoke-RestMethod` latest release, find matching asset, download,
    `Expand-Archive` to `$env:APPDATA\Claude\skills\`, print installed dirs
  - Exit non-zero with `Write-Error` if asset not found

- [x] task-04: update `build-release.yml` upload step for install scripts (blocks: task-02, task-03)
  - The existing Linux job uploads `install.sh` and `install.ps1`
  - The new `package-skills` job uploads `install-skills.sh` and `install-skills.ps1`
    (gated on `SKILLS_CHANGED`)
  - Verify no duplicate uploads conflict; both jobs upload to the same release via
    `softprops/action-gh-release@v2` which handles concurrent asset uploads safely

- [x] task-05: update CLAUDE.md with changelog discipline (blocks: none)
  - Add a `## skills` section (or extend `## CI/CD`) documenting that any version touching
    `skills/` must include a `### Skills` subsection in CHANGELOG.md
  - One sentence per skill that changed, describing what was updated

- [ ] task-06: smoke test (blocks: task-01, task-02, task-03, task-04)
  - Push a test tag that includes a trivial skill change (e.g. trailing whitespace)
  - Verify CI publishes both language zips and both install scripts
  - Run `install-skills.sh` locally; confirm skill dirs appear in `~/.claude/skills/`
  - Run `install-skills.sh --uninstall`; confirm dirs are removed
  - Push a second test tag with no skill changes; verify no skill assets are published
  - Clean up both test tags

## ADR required?

No. The packaging and scripting approach mirrors the existing CLI release pipeline exactly.

## risks

1. **Concurrent release uploads.** Both the build matrix jobs and `package-skills` upload
   to the same release. `softprops/action-gh-release@v2` handles this via upsert, but if
   two jobs try to create the release simultaneously the first write wins and the second
   may fail. Mitigation: existing behavior already handles this with the matrix build;
   `package-skills` runs independently and uploads distinct asset names.

2. **Claude Desktop skills path varies by version.** If Anthropic changes the skills
   directory location, the install scripts will target the wrong path. Mitigation: document
   the path and accept `CLAUDE_SKILLS_DIR` env var override in both scripts.

3. **First-tag fallback.** `git describe --tags --abbrev=0 HEAD^` fails with no output
   when there is exactly one tag. Mitigation: test with `|| echo ""` and treat empty
   PREV as "package unconditionally".

4. **Zip root structure.** If the CI zip command includes the `skills/<lang>/` prefix,
   Claude Desktop won't find the skill dirs. Mitigation: `cd skills/<lang> && zip -r`
   to ensure dirs are at the archive root.
