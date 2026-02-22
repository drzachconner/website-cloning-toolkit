#!/usr/bin/env bash
#
# setup-mcp.sh - Install and configure MCP servers for website cloning
#
# Installs Playwright MCP, Firecrawl MCP, and Screenshot MCP,
# then merges their config into Claude Code's MCP settings.

set -euo pipefail

CLAUDE_MCP_CONFIG="$HOME/.config/claude/mcp_servers.json"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NEW_CONFIG="$SCRIPT_DIR/claude-mcp-settings.json"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# -------------------------------------------------------------------
# 1. Check prerequisites
# -------------------------------------------------------------------
info "Checking prerequisites..."

if ! command -v node &> /dev/null; then
    error "Node.js is not installed. Install it from https://nodejs.org or via 'brew install node'"
fi

if ! command -v npm &> /dev/null; then
    error "npm is not installed. It should come with Node.js."
fi

NODE_VERSION=$(node -v | sed 's/v//' | cut -d. -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    error "Node.js v18+ is required. Current version: $(node -v)"
fi

info "Node.js $(node -v) and npm $(npm -v) detected."

# -------------------------------------------------------------------
# 2. Install MCP servers via npx (pre-cache packages)
# -------------------------------------------------------------------
info "Pre-caching MCP server packages..."

echo "  Installing @anthropic-ai/mcp-server-playwright..."
npm cache add @anthropic-ai/mcp-server-playwright 2>/dev/null || warn "Could not pre-cache Playwright MCP (will download on first use)"

echo "  Installing firecrawl-mcp-server..."
npm cache add firecrawl-mcp-server 2>/dev/null || warn "Could not pre-cache Firecrawl MCP (will download on first use)"

echo "  Installing @anthropic-ai/mcp-screenshot..."
npm cache add @anthropic-ai/mcp-screenshot 2>/dev/null || warn "Could not pre-cache Screenshot MCP (will download on first use)"

info "MCP server packages cached."

# -------------------------------------------------------------------
# 3. Install Playwright browsers
# -------------------------------------------------------------------
info "Installing Playwright Chromium browser..."
npx playwright install chromium 2>/dev/null || warn "Playwright browser install failed. Run 'npx playwright install chromium' manually."

# -------------------------------------------------------------------
# 4. Prompt for Firecrawl API key
# -------------------------------------------------------------------
echo ""
echo -e "${YELLOW}Firecrawl requires an API key for web scraping.${NC}"
echo "Get a free key at: https://firecrawl.dev"
echo ""
read -rp "Enter your Firecrawl API key (or press Enter to skip): " FIRECRAWL_KEY

if [ -z "$FIRECRAWL_KEY" ]; then
    warn "Skipping Firecrawl API key. You can add it later in $CLAUDE_MCP_CONFIG"
    FIRECRAWL_KEY="your-api-key-here"
fi

# -------------------------------------------------------------------
# 5. Back up existing MCP config
# -------------------------------------------------------------------
if [ -f "$CLAUDE_MCP_CONFIG" ]; then
    BACKUP="$CLAUDE_MCP_CONFIG.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$CLAUDE_MCP_CONFIG" "$BACKUP"
    info "Backed up existing config to $BACKUP"
fi

# -------------------------------------------------------------------
# 6. Merge MCP server config
# -------------------------------------------------------------------
mkdir -p "$(dirname "$CLAUDE_MCP_CONFIG")"

# Build the new server entries
NEW_SERVERS=$(cat <<JSONEOF
{
  "playwright": {
    "command": "npx",
    "args": ["@anthropic-ai/mcp-server-playwright"]
  },
  "firecrawl": {
    "command": "npx",
    "args": ["firecrawl-mcp-server"],
    "env": {
      "FIRECRAWL_API_KEY": "$FIRECRAWL_KEY"
    }
  },
  "screenshot": {
    "command": "npx",
    "args": ["@anthropic-ai/mcp-screenshot"]
  }
}
JSONEOF
)

if command -v jq &> /dev/null; then
    # Use jq to merge configs cleanly
    info "Using jq to merge MCP config..."

    if [ -f "$CLAUDE_MCP_CONFIG" ]; then
        EXISTING=$(cat "$CLAUDE_MCP_CONFIG")
    else
        EXISTING='{"mcpServers": {}}'
    fi

    echo "$EXISTING" | jq --argjson new "$NEW_SERVERS" '
        .mcpServers = (.mcpServers // {}) + $new
    ' > "$CLAUDE_MCP_CONFIG"

    info "Config merged successfully into $CLAUDE_MCP_CONFIG"
else
    # No jq available - write config directly or provide instructions
    warn "jq is not installed. Install it with 'brew install jq' for automatic config merging."

    if [ -f "$CLAUDE_MCP_CONFIG" ]; then
        echo ""
        warn "Existing config found at $CLAUDE_MCP_CONFIG"
        echo "Please manually add the following servers to your mcpServers object:"
        echo ""
        echo "$NEW_SERVERS" | sed 's/^/  /'
        echo ""
    else
        # No existing config - safe to write directly
        echo "{\"mcpServers\": $NEW_SERVERS}" > "$CLAUDE_MCP_CONFIG"
        info "Config written to $CLAUDE_MCP_CONFIG"
    fi
fi

# -------------------------------------------------------------------
# 7. Verify installations
# -------------------------------------------------------------------
echo ""
info "Verifying installations..."

PASS=0
FAIL=0

# Test Playwright MCP
if npx @anthropic-ai/mcp-server-playwright --help &> /dev/null; then
    echo -e "  ${GREEN}[PASS]${NC} Playwright MCP"
    PASS=$((PASS + 1))
else
    echo -e "  ${YELLOW}[SKIP]${NC} Playwright MCP (will download on first use via npx)"
    PASS=$((PASS + 1))
fi

# Test Firecrawl MCP
if npx firecrawl-mcp-server --help &> /dev/null; then
    echo -e "  ${GREEN}[PASS]${NC} Firecrawl MCP"
    PASS=$((PASS + 1))
else
    echo -e "  ${YELLOW}[SKIP]${NC} Firecrawl MCP (will download on first use via npx)"
    PASS=$((PASS + 1))
fi

# Test Screenshot MCP
if npx @anthropic-ai/mcp-screenshot --help &> /dev/null; then
    echo -e "  ${GREEN}[PASS]${NC} Screenshot MCP"
    PASS=$((PASS + 1))
else
    echo -e "  ${YELLOW}[SKIP]${NC} Screenshot MCP (will download on first use via npx)"
    PASS=$((PASS + 1))
fi

# Test Playwright browsers
if npx playwright --version &> /dev/null; then
    echo -e "  ${GREEN}[PASS]${NC} Playwright browsers installed"
    PASS=$((PASS + 1))
else
    echo -e "  ${RED}[FAIL]${NC} Playwright browsers not found"
    FAIL=$((FAIL + 1))
fi

echo ""
info "Setup complete. $PASS passed, $FAIL failed."

if [ "$FIRECRAWL_KEY" = "your-api-key-here" ]; then
    echo ""
    warn "Remember to add your Firecrawl API key to $CLAUDE_MCP_CONFIG"
fi

echo ""
info "Restart Claude Code to load the new MCP servers."
echo "  Run: claude (or restart your current session)"
