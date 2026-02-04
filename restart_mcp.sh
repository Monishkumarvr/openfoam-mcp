#!/bin/bash
# Script to update and restart OpenFOAM MCP server

set -e

echo "🔄 OpenFOAM MCP Update & Restart Script"
echo "========================================"
echo ""

# Check if we're in the right directory
if [ ! -f "openfoam_mcp/server.py" ]; then
    echo "❌ Error: Must run from openfoam-mcp repository root"
    echo "   Current directory: $(pwd)"
    echo "   Expected: /home/user/openfoam-mcp"
    exit 1
fi

echo "📍 Working directory: $(pwd)"
echo ""

# Pull latest changes
echo "📥 Pulling latest changes from GitHub..."
git fetch origin
git pull origin main
echo "✅ Repository updated"
echo ""

# Clear Python cache
echo "🧹 Clearing Python cache..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
echo "✅ Cache cleared"
echo ""

# Show current commit
echo "📂 Current commit:"
git log --oneline -1
echo ""

# Verify fake analyzer is deleted
if [ -f "openfoam_mcp/api/result_analyzer.py" ]; then
    echo "❌ WARNING: Fake result_analyzer.py still exists!"
    echo "   Deleting it now..."
    rm openfoam_mcp/api/result_analyzer.py
    git add -u
    git commit -m "Remove fake analyzer"
else
    echo "✅ Fake analyzer properly deleted"
fi

# Verify real analyzer exists
if [ -f "openfoam_mcp/api/result_analyzer_real.py" ]; then
    echo "✅ Real analyzer exists"
else
    echo "❌ ERROR: Real analyzer missing!"
    exit 1
fi

echo ""

# Kill existing MCP server processes
echo "🔪 Stopping existing MCP server processes..."
pkill -f "openfoam.*mcp" 2>/dev/null && echo "   Killed openfoam-mcp processes" || echo "   No processes found"
pkill -f "python.*server.py" 2>/dev/null && echo "   Killed server.py processes" || echo "   No processes found"

sleep 1

# Check if any still running
if pgrep -f "openfoam.*mcp\|python.*server.py" > /dev/null; then
    echo "⚠️ WARNING: Some MCP processes still running"
    echo "   Run: pkill -9 -f 'openfoam.*mcp'"
else
    echo "✅ All MCP server processes stopped"
fi

echo ""
echo "="*60
echo ""
echo "✅ UPDATE COMPLETE"
echo ""
echo "Next steps:"
echo "1. If using Claude Desktop, restart it completely"
echo "2. Verify with diagnostic_health_check tool"
echo "3. Expected output:"
echo "   ✅ ANALYZER: RealResultAnalyzer (CORRECT)"
echo "   ✅ Old fake analyzer properly removed"
echo ""
echo "If still seeing '95% Niyama' responses:"
echo "- Your MCP client isn't using this repository"
echo "- Check MCP configuration file"
echo "- Ensure 'cwd' points to: $(pwd)"
echo ""
