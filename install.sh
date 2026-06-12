#!/bin/bash

set -e

echo ""
echo "Installing assistant..."
echo ""

# Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt --quiet
playwright install chromium --quiet

# Launcher script aanmaken
ASSISTANT_NAME=${ASSISTANT_NAME:-assistant}
INSTALL_DIR="$HOME/.local/bin"
SCRIPT_PATH="$INSTALL_DIR/$ASSISTANT_NAME"
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

mkdir -p "$INSTALL_DIR"

cat > "$SCRIPT_PATH" << EOF
#!/bin/bash
cd "$PROJECT_DIR"
exec python main.py "\$@"
EOF

chmod +x "$SCRIPT_PATH"

# .env aanmaken als die nog niet bestaat
if [ ! -f "$PROJECT_DIR/.env" ]; then
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    echo ""
    echo "  .env aangemaakt vanuit .env.example"
    echo "  Pas je API keys en naam aan in .env voor je start."
fi

echo ""
echo "  Klaar. Type '$ASSISTANT_NAME' om te starten."
echo ""
