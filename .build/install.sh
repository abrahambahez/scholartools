#!/usr/bin/env sh
set -e

REPO="abrahambahez/scholartools"
BIN_DIR="$HOME/.local/bin"
CONFIG_DIR="$HOME/.config/scholartools"
CONFIG_FILE="$CONFIG_DIR/config.json"

# ── helpers ────────────────────────────────────────────────────────────────────
ask() { printf "%s " "$1"; read -r REPLY; echo "$REPLY"; }
confirm() {
    printf "%s [Y/n] " "$1"
    read -r ans
    case "$ans" in [nN]*) return 1 ;; *) return 0 ;; esac
}

# ── fetch latest release ───────────────────────────────────────────────────────
echo "Fetching latest scholartools release..."
VERSION=$(curl -fsSL "https://api.github.com/repos/$REPO/releases/latest" \
    | grep '"tag_name"' | sed 's/.*"tag_name": *"\([^"]*\)".*/\1/')

if [ -z "$VERSION" ]; then
    echo "error: could not determine latest release" >&2
    exit 1
fi
echo "Installing scht $VERSION"

# ── detect arch ───────────────────────────────────────────────────────────────
ARCH=$(uname -m)
case "$ARCH" in
    x86_64)  PLATFORM="linux-x86_64" ;;
    aarch64) PLATFORM="linux-arm64" ;;
    *)       echo "error: unsupported architecture: $ARCH" >&2; exit 1 ;;
esac

# ── download & extract ────────────────────────────────────────────────────────
VERSION_NUM="${VERSION#v}"
FILENAME="scht-${VERSION_NUM}-${PLATFORM}.zip"
URL="https://github.com/$REPO/releases/download/$VERSION/$FILENAME"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

echo "Downloading $FILENAME..."
curl -fsSL -o "$TMP/$FILENAME" "$URL"
unzip -q "$TMP/$FILENAME" -d "$TMP"

mkdir -p "$BIN_DIR"
cp "$TMP/scht/scht" "$BIN_DIR/scht"
chmod +x "$BIN_DIR/scht"

# ── ensure PATH ───────────────────────────────────────────────────────────────
case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *)
        for rc in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile"; do
            [ -f "$rc" ] && printf '\nexport PATH="$HOME/.local/bin:$PATH"\n' >> "$rc"
        done
        echo "Added $BIN_DIR to PATH (restart your shell or run: export PATH=\"\$HOME/.local/bin:\$PATH\")"
        ;;
esac

echo ""
echo "scht $VERSION installed to $BIN_DIR/scht"

# ── config setup ──────────────────────────────────────────────────────────────
if [ -f "$CONFIG_FILE" ]; then
    echo ""
    echo "Config already exists at $CONFIG_FILE — skipping setup."
    exit 0
fi

echo ""
echo "── Initial setup ────────────────────────────────────────────────────────"
echo ""

# email
EMAIL=$(ask "Scholar email (used for polite API access, e.g. you@uni.edu):")

# library path
echo ""
echo "Where should your library live?"
echo "  1) $HOME/.local/share/scholartools  (default, hidden)"
echo "  2) $HOME/Documents/scholartools"
echo "  3) $HOME/Library/scholartools"
echo "  4) Custom path"
printf "Choice [1]: "
read -r choice
case "$choice" in
    2) LIBRARY_DIR="$HOME/Documents/scholartools" ;;
    3) LIBRARY_DIR="$HOME/Library/scholartools" ;;
    4)
        LIBRARY_DIR=$(ask "Enter full path:")
        ;;
    *) LIBRARY_DIR="$HOME/.local/share/scholartools" ;;
esac
echo "Library: $LIBRARY_DIR"

# sources
echo ""
echo "Enable search sources (all on by default — deselect to disable):"
SOURCES='["crossref","semantic_scholar","arxiv","openalex","doaj","google_books"]'
SOURCES_JSON=""
for src in crossref semantic_scholar arxiv openalex doaj google_books; do
    if confirm "  $src?"; then
        enabled="true"
    else
        enabled="false"
    fi
    entry="{\"name\":\"$src\",\"enabled\":$enabled}"
    SOURCES_JSON="${SOURCES_JSON:+$SOURCES_JSON,}$entry"
done

# ── write config ──────────────────────────────────────────────────────────────
mkdir -p "$CONFIG_DIR"
cat > "$CONFIG_FILE" <<EOF
{
  "backend": "local",
  "local": {
    "library_dir": "$LIBRARY_DIR"
  },
  "apis": {
    "email": "$EMAIL",
    "sources": [$SOURCES_JSON]
  },
  "llm": {
    "model": "claude-sonnet-4-6"
  }
}
EOF

echo ""
echo "Config written to $CONFIG_FILE"
echo "Run 'scht --help' to get started."
