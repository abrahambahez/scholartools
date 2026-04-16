# Getting started with loretools

This guide is for researchers using **Claude Co-Work** (Claude Projects with file access). No terminal experience required — your AI agent handles all shell operations.

---

## What is a collection?

A **collection** is a single folder that contains everything loretools needs:

- `lore` — the binary the agent runs
- `.lore/config.json` — your preferences and settings
- `library.json` — your reference library
- `files/` — PDF and document files linked to references
- `staging/` — references waiting to be reviewed and merged

Create one collection per research project (or one shared collection across projects).

---

## First session: setting up your collection

### 1. Download the binary

Go to the [Releases page](https://github.com/abrahambahez/loretools/releases) and download the binary for your platform:

- **macOS (Apple Silicon):** `lore-macos-arm64`
- **Linux:** `lore-linux-x86_64`
- **Windows:** `lore-windows-x86_64.exe`

Rename the file to `lore` and place it inside your collection folder.

### 2. Copy the setup prompt

Go to the [loretools landing page](https://github.com/abrahambahez/loretools) and copy the setup prompt.

### 3. Open Claude Co-Work and mount your collection folder

Open Claude Projects and connect your collection folder so the agent can read and write files there.

### 4. Upload the binary and paste the setup prompt

Upload the `lore` binary to your Co-Work session, then paste the setup prompt. The agent will:

1. Make the binary executable
2. Run it once to auto-create `.lore/config.json`
3. Write a `CLAUDE.md` to your collection folder so future sessions start automatically
4. Verify the collection is operational

### 5. Verify everything works

The agent will confirm setup by running:

```
./lore refs list
./lore staging list-staged
```

Both should return `{"ok": true, ...}`. Your collection is ready.

---

## Subsequent sessions

Each time you open a new Co-Work session:

1. Mount your collection folder
2. The agent reads `CLAUDE.md` and runs verification automatically — no prompting needed

---

## Collection directory layout

After setup your collection folder looks like this:

```
<your-collection>/
  lore                          # the loretools binary
  CLAUDE.md                     # agent instructions (auto-created during setup)
  .lore/
    config.json                 # settings (auto-created on first run)
  library.json                  # your reference library
  files/                        # archived PDFs and documents
  staging.json                  # staged references
  staging/                      # staged files
```

---

## Config reference

`.lore/config.json` is created automatically with sensible defaults. You only need to edit it if you want to change something.

| Field | Default | What it controls |
|-------|---------|-----------------|
| `local.library_dir` | Collection folder (CWD) | Where `library.json`, `files/`, and `staging/` are stored. |
| `citekey.pattern` | `"{author[2]}{year}"` | Pattern for generated citekeys. Tokens: `{author[N]}` (first N surnames), `{year}`. |
| `citekey.separator` | `"_"` | Separator between author tokens. |
| `citekey.etal` | `"_etal"` | Suffix when authors exceed the pattern limit. |
| `citekey.disambiguation_suffix` | `"letters"` | How to disambiguate duplicate keys: `"letters"` (a/b/c) or `"title[1-9]"` (first N title words). |

---

## Skills

For complex workflows — bulk operations, file management, reference disambiguation — install the `loretools-references` skill. Download the skill zip from the Releases page and ask the agent to install it.

---

## Troubleshooting

**`lore` not found**
Confirm the collection folder is mounted and `lore` is present. Ask the agent: "List files in the collection folder."

**Permission denied when running `lore`**
Ask the agent: "Make lore executable with chmod +x."

**Config not found**
Run `./lore refs list` once — this auto-creates `.lore/config.json` if missing.

**Empty library on first use**
`library.json` and `staging.json` are created on first write. Empty results before that are normal.
