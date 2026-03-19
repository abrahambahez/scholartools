#!/usr/bin/env sh
set -e

REPO="abrahambahez/scholartools"
BIN_DIR="$HOME/.local/bin"
BIN="$BIN_DIR/scht"
CONFIG_DIR="$HOME/.config/scholartools"
CONFIG_FILE="$CONFIG_DIR/config.json"

ask() { printf "%s " "$1"; read -r REPLY; echo "$REPLY"; }
confirm() {
    printf "%s [Y/n] " "$1"
    read -r ans
    case "$ans" in [nN]*) return 1 ;; *) return 0 ;; esac
}

detect_platform() {
    OS=$(uname -s)
    ARCH=$(uname -m)
    case "$OS" in
        Darwin)
            case "$ARCH" in
                arm64) echo "macos-arm64" ;;
                *) echo "error: unsupported macOS architecture: $ARCH" >&2; exit 1 ;;
            esac
            ;;
        Linux)
            case "$ARCH" in
                x86_64) echo "linux-x86_64" ;;
                *) echo "error: unsupported Linux architecture: $ARCH" >&2; exit 1 ;;
            esac
            ;;
        *) echo "error: unsupported OS: $OS" >&2; exit 1 ;;
    esac
}

ensure_path() {
    case ":$PATH:" in
        *":$BIN_DIR:"*) ;;
        *)
            for rc in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile"; do
                [ -f "$rc" ] && printf '\nexport PATH="$HOME/.local/bin:$PATH"\n' >> "$rc"
            done
            echo "Added $BIN_DIR to PATH (restart your shell or run: export PATH=\"\$HOME/.local/bin:\$PATH\")"
            ;;
    esac
}

run_config_setup() {
    echo ""
    echo "── Initial setup ────────────────────────────────────────────────────────"
    echo ""

    EMAIL=$(ask "Scholar email (used for polite API access, e.g. you@uni.edu):")

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
        4) LIBRARY_DIR=$(ask "Enter full path:") ;;
        *) LIBRARY_DIR="$HOME/.local/share/scholartools" ;;
    esac
    echo "Library: $LIBRARY_DIR"

    echo ""
    echo "Enable search sources (all on by default — deselect to disable):"
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
}

uninstall() {
    if [ -f "$BIN" ]; then
        rm "$BIN"
        echo "Removed $BIN"
    else
        echo "scht binary not found at $BIN — nothing to remove"
    fi

    if [ -d "$CONFIG_DIR" ]; then
        echo ""
        echo "WARNING: $CONFIG_DIR contains your library settings and data paths."
        if confirm "Permanently delete $CONFIG_DIR?"; then
            rm -rf "$CONFIG_DIR"
            echo "Removed $CONFIG_DIR"
        else
            echo "Config directory left intact."
        fi
    fi
    exit 0
}

if [ "${1:-}" = "--uninstall" ]; then
    uninstall
fi

PLATFORM=$(detect_platform)

echo "Fetching latest scholartools release..."
VERSION=$(curl -fsSL "https://api.github.com/repos/$REPO/releases/latest" \
    | grep '"tag_name"' | sed 's/.*"tag_name": *"\([^"]*\)".*/\1/')

if [ -z "$VERSION" ]; then
    echo "error: could not determine latest release" >&2
    exit 1
fi
echo "Installing scht $VERSION"

VERSION_NUM="${VERSION#v}"
FILENAME="scht-${VERSION_NUM}-${PLATFORM}.zip"
URL="https://github.com/$REPO/releases/download/$VERSION/$FILENAME"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

echo "Downloading $FILENAME..."
curl -fsSL -o "$TMP/$FILENAME" "$URL"
unzip -q "$TMP/$FILENAME" -d "$TMP"

case "$PLATFORM" in
    macos-*) xattr -dr com.apple.quarantine "$TMP/scht" 2>/dev/null || true ;;
esac

mkdir -p "$BIN_DIR"
cp "$TMP/scht/scht" "$BIN"
chmod +x "$BIN"

ensure_path

echo ""
echo "scht $VERSION installed to $BIN"

if [ -f "$CONFIG_FILE" ]; then
    echo ""
    echo "Config already exists at $CONFIG_FILE — skipping setup."
    echo "Run 'scht --help' to get started."
    exit 0
fi

run_config_setup

echo "Run 'scht --help' to get started."
