# feat: 025-skills-zip-distribution — packaged skill releases for Claude Desktop

version: 0.1
status: current

## problem

Researchers using scholartools with Claude Desktop need to install the workflow skills
(`scholartools-config`, `scholartools-references`, `scholartools-files`,
`scholartools-sync-peers`) by manually copying SKILL.md files into their Claude config.
There is no versioned artifact they can download or that the install script can fetch
automatically.

## decision

Package skills as per-language zip files and publish them as GitHub Release assets whenever
any skill file changes between version tags.

**Format:** One zip per language (`scholartools-skills-en-vX.Y.Z.zip`,
`scholartools-skills-es-vX.Y.Z.zip`). Each zip contains flat skill directories at the root:

```
scholartools-skills-en-vX.Y.Z.zip
  scholartools-config/SKILL.md
  scholartools-references/SKILL.md
  scholartools-sync-peers/SKILL.md
```

This matches the Claude Desktop skill installation layout (each skill is a directory
containing SKILL.md, placed under `~/.claude/skills/` or equivalent).

**Conditional release:** Skills are only packaged and uploaded when `git diff` between the
current tag and the previous tag shows changes under `skills/`. If no skill file changed,
the release only contains CLI platform bundles. If any skill file changed (any language),
both language zips are released.

**CI placement:** A single new job `package-skills` in `build-release.yml`, running on
`ubuntu-latest`. No matrix needed — zipping is fast and platform-independent.

**First-tag edge case:** If no previous tag exists, always package skills.

## install-skills scripts

Two standalone scripts (`install-skills.sh`, `install-skills.ps1`) are published as release
assets alongside the skill zips — but only on releases that include skill zips.

**Behaviour:**
1. Prompt the researcher to choose a language (default: `en`)
2. Fetch the latest GitHub release JSON and find the matching skills asset
   (`scholartools-skills-<lang>-<version>.zip`)
3. Download and extract into the Claude Desktop skills directory:
   - macOS / Linux: `~/.claude/skills/`
   - Windows: `%APPDATA%\Claude\skills\`
4. Print the list of installed skill directories
5. Accept `--uninstall` flag: remove all `scholartools-*` directories from the skills dir

**Idempotency:** Re-running on the same version overwrites existing skill dirs silently.

**No interactive config setup** — skills have no per-user configuration.

The scripts are uploaded from the Linux CI runner (same as `install.sh` / `install.ps1`),
conditional on `SKILLS_CHANGED`.

## changelog discipline

Every CHANGELOG entry for a version that touches `skills/` must include a `### Skills`
subsection documenting which skills changed and what changed in them. This is the signal
users need to know whether to re-install the skill zips.

## alternatives considered

- **Bundle skills inside CLI zips:** Rejected — skills and CLI have independent update
  cadences; bloats CLI bundles unnecessarily.
- **Separate skills repo / registry:** Over-engineered for current user count.
- **Single combined zip (all languages):** Users only need one language; split keeps
  download size minimal and installation unambiguous.
