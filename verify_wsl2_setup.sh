#!/bin/bash
# Verification script for OpenFOAM MCP in WSL2
# Run this inside WSL2 to verify everything is configured correctly

set -e

echo "=================================="
echo "OpenFOAM MCP WSL2 Verification"
echo "=================================="
echo ""

# Check 1: Are we in WSL2?
if grep -qi microsoft /proc/version; then
    echo "✅ Running in WSL2"
else
    echo "❌ Not running in WSL2"
    echo "   This script should be run inside WSL2"
    exit 1
fi

echo ""

# Check 2: Is OpenFOAM installed?
echo "Checking OpenFOAM installation..."
if [ -d "/opt/openfoam11" ]; then
    echo "✅ OpenFOAM 11 found at /opt/openfoam11"
elif [ -d "/opt/openfoam10" ]; then
    echo "✅ OpenFOAM 10 found at /opt/openfoam10"
else
    echo "❌ OpenFOAM not found in /opt/"
    echo "   Please install OpenFOAM first"
    exit 1
fi

echo ""

# Check 3: Can we source OpenFOAM?
echo "Checking OpenFOAM environment..."
if [ -f "/opt/openfoam11/etc/bashrc" ]; then
    source /opt/openfoam11/etc/bashrc
    echo "✅ Sourced OpenFOAM 11 environment"
elif [ -f "/opt/openfoam10/etc/bashrc" ]; then
    source /opt/openfoam10/etc/bashrc
    echo "✅ Sourced OpenFOAM 10 environment"
else
    echo "❌ Cannot find OpenFOAM bashrc"
    exit 1
fi

echo ""

# Check 4: Are OpenFOAM commands available?
echo "Checking OpenFOAM commands..."
MISSING=0

for cmd in blockMesh interFoam simpleFoam; do
    if command -v $cmd &> /dev/null; then
        echo "  ✅ $cmd found"
    else
        echo "  ❌ $cmd not found"
        MISSING=1
    fi
done

if [ $MISSING -eq 1 ]; then
    echo ""
    echo "❌ Some OpenFOAM commands are missing"
    echo "   Make sure OpenFOAM environment is properly sourced"
    exit 1
fi

echo ""

# Check 5: Does foam/run directory exist?
echo "Checking case directory..."
FOAM_RUN="$HOME/foam/run"
if [ -d "$FOAM_RUN" ]; then
    CASE_COUNT=$(find "$FOAM_RUN" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l)
    echo "✅ Cases directory exists: $FOAM_RUN"
    echo "   Cases found: $CASE_COUNT"

    if [ $CASE_COUNT -gt 0 ]; then
        echo ""
        echo "   Existing cases:"
        ls -1 "$FOAM_RUN" | head -10 | sed 's/^/     - /'

        if [ $CASE_COUNT -gt 10 ]; then
            echo "     ... and $((CASE_COUNT - 10)) more"
        fi
    fi
else
    echo "⚠️ Cases directory doesn't exist: $FOAM_RUN"
    echo "   Will be created automatically when first case is created"
fi

echo ""

# Check 6: Check Python environment
echo "Checking Python environment..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo "✅ $PYTHON_VERSION"
else
    echo "❌ python3 not found"
    exit 1
fi

echo ""

# Check 7: Check Python packages
echo "Checking Python packages..."
MISSING_PKG=0

for pkg in numpy loguru; do
    if python3 -c "import $pkg" 2>/dev/null; then
        VERSION=$(python3 -c "import $pkg; print($pkg.__version__)" 2>/dev/null || echo "unknown")
        echo "  ✅ $pkg ($VERSION)"
    else
        echo "  ❌ $pkg not installed"
        MISSING_PKG=1
    fi
done

# Check MCP package separately (different check)
if python3 -c "import mcp" 2>/dev/null; then
    echo "  ✅ mcp"
else
    echo "  ❌ mcp not installed"
    MISSING_PKG=1
fi

if [ $MISSING_PKG -eq 1 ]; then
    echo ""
    echo "⚠️ Some Python packages are missing"
    echo "   Install with: pip install numpy loguru mcp"
fi

echo ""

# Check 8: Check openfoam-mcp installation
echo "Checking openfoam-mcp installation..."
REPO_DIR="/mnt/d/Projects/NP/openfoam-mcp/openfoam-mcp"

if [ ! -d "$REPO_DIR" ]; then
    echo "❌ Repository not found at $REPO_DIR"
    echo "   Update REPO_DIR in this script to match your installation"
    exit 1
fi

echo "✅ Repository found at $REPO_DIR"

# Check if we can import the module
cd "$REPO_DIR"
if python3 -c "import openfoam_mcp.server" 2>/dev/null; then
    echo "✅ openfoam_mcp module can be imported"
else
    echo "❌ Cannot import openfoam_mcp module"
    echo "   Run: pip install -e $REPO_DIR"
    exit 1
fi

# Check which analyzer is being used
ANALYZER_CHECK=$(python3 << 'PYEOF'
import sys
sys.path.insert(0, '/mnt/d/Projects/NP/openfoam-mcp/openfoam-mcp')
from openfoam_mcp.server import result_analyzer
print(type(result_analyzer).__name__)
PYEOF
)

if [ "$ANALYZER_CHECK" = "RealResultAnalyzer" ]; then
    echo "✅ Server uses RealResultAnalyzer (CORRECT)"
else
    echo "❌ Server uses $ANALYZER_CHECK (WRONG)"
    echo "   Expected: RealResultAnalyzer"
    echo "   Actual: $ANALYZER_CHECK"
    exit 1
fi

# Check if fake analyzer was deleted
if [ -f "$REPO_DIR/openfoam_mcp/api/result_analyzer.py" ]; then
    echo "❌ WARNING: Fake result_analyzer.py still exists!"
    echo "   It should have been deleted in commit 798e1fa"
else
    echo "✅ Fake analyzer properly deleted"
fi

# Check if real analyzer exists
if [ -f "$REPO_DIR/openfoam_mcp/api/result_analyzer_real.py" ]; then
    echo "✅ Real analyzer exists"
else
    echo "❌ ERROR: Real analyzer missing!"
    exit 1
fi

echo ""

# Check 9: Git status
echo "Checking repository status..."
cd "$REPO_DIR"
GIT_BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
GIT_HASH=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
GIT_COMMIT=$(git log --oneline -1 2>/dev/null || echo "unknown")

echo "  Branch: $GIT_BRANCH"
echo "  Commit: $GIT_HASH"
echo "  Latest: $GIT_COMMIT"

echo ""
echo "=================================="
echo "✅ ALL CHECKS PASSED"
echo "=================================="
echo ""
echo "Your WSL2 environment is configured correctly."
echo ""
echo "Next steps:"
echo "1. Make sure your MCP client is configured to run in WSL2"
echo "2. Create a new case using create_casting_case tool"
echo "3. Run simulation and verify it generates time directories"
echo "4. Analyze results and verify they're parameter-dependent"
echo ""
echo "See WSL2_SETUP.md for detailed instructions."
echo ""
