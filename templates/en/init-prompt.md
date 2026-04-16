# loretools setup prompt

Copy everything below the line and paste it into your Claude Co-Work session after uploading the `lore` binary file.

---

Set up loretools in this collection folder. The binary has been uploaded to this session.

**Step 1 — Install the binary**

```bash
chmod +x lore
./lore --version
```

**Step 2 — Initialize the collection**

```bash
./lore refs list
```

This creates `.lore/config.json` with default settings. The command should return `{"ok": true, "references": []}`.

**Step 3 — Write CLAUDE.md**

Create a file named `CLAUDE.md` in this folder with the following content exactly:

```
# loretools collection

This folder is a loretools collection. `lore` is the CLI binary — always run it as `./lore` from this directory. Never install it to PATH.

## Session start

Run these automatically at the start of every session before the researcher asks anything:

./lore --version
./lore refs list

If `lore` is not found, the collection folder is not mounted. Ask the researcher to verify the folder is connected to this session.

## Collection layout

<collection>/
  lore                    # binary — run as ./lore
  .lore/config.json       # settings (auto-created on first run)
  library.json            # production reference library
  files/                  # archived PDFs and documents
  staging.json            # staged references
  staging/                # staged files

## Core workflow

# Extract metadata from a PDF
./lore extract <path/to/file.pdf>

# Stage a reference (JSON from extract or manual)
./lore staging stage '<json>' [--file <path>]

# Review staged references
./lore staging list-staged

# Merge staged into library
./lore staging merge

# Search the library
./lore refs filter --query "<text>" [--author "<surname>"] [--year YYYY]

# Get a full record
./lore refs get <citekey>

## Skills

If the researcher asks for a complex workflow (bulk operations, file management, disambiguation), load the `loretools-references` skill — it has complete CLI reference, all flags, and model field details.
```

**Step 4 — Verify**

```bash
./lore refs list
./lore staging list-staged
```

Both should return `{"ok": true, ...}`. Tell me when setup is complete or if any step fails.
