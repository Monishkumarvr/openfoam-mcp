#!/bin/bash
# Simplified verification for WSL2 setup
# This version handles OpenFOAM bashrc warnings gracefully

echo "=================================="
echo "OpenFOAM MCP WSL2 Quick Check"
echo "=================================="
echo ""

# Source OpenFOAM (suppress the harmless warning)
if [ -f "/opt/openfoam11/etc/bashrc" ]; then
    source /opt/openfoam11/etc/bashrc 2>&1 | grep -v "pop_var_context" || true
    echo "✅ OpenFOAM 11 environment sourced"
elif [ -f "/opt/openfoam10/etc/bashrc" ]; then
    source /opt/openfoam10/etc/bashrc 2>&1 | grep -v "pop_var_context" || true
    echo "✅ OpenFOAM 10 environment sourced"
else
    echo "❌ OpenFOAM not found"
    exit 1
fi

echo ""

# Check commands
echo "Checking OpenFOAM commands..."
for cmd in blockMesh interFoam simpleFoam; do
    if command -v $cmd &> /dev/null; then
        echo "  ✅ $cmd"
    else
        echo "  ❌ $cmd NOT FOUND"
    fi
done

echo ""

# Check Python
echo "Checking Python environment..."
python3 --version
pip list | grep -E "(numpy|loguru|mcp)" || echo "  ⚠️ Some packages may be missing"

echo ""

# Check repository
REPO="/mnt/d/Projects/NP/openfoam-mcp/openfoam-mcp"
if [ -d "$REPO" ]; then
    echo "✅ Repository found: $REPO"
    cd "$REPO"

    # Check git status
    echo ""
    echo "Repository status:"
    git log --oneline -1

    echo ""

    # Check which analyzer is active
    echo "Checking analyzer..."
    python3 << 'PYEOF'
import sys
sys.path.insert(0, '/mnt/d/Projects/NP/openfoam-mcp/openfoam-mcp')
try:
    from openfoam_mcp.server import result_analyzer
    analyzer_name = type(result_analyzer).__name__
    if analyzer_name == "RealResultAnalyzer":
        print(f"✅ Using {analyzer_name} (CORRECT)")
    else:
        print(f"❌ Using {analyzer_name} (WRONG - should be RealResultAnalyzer)")
except Exception as e:
    print(f"❌ Error: {e}")
PYEOF

    echo ""

    # Check if fake analyzer exists
    if [ -f "$REPO/openfoam_mcp/api/result_analyzer.py" ]; then
        echo "❌ WARNING: Fake result_analyzer.py still exists"
    else
        echo "✅ Fake analyzer deleted (as expected)"
    fi

    if [ -f "$REPO/openfoam_mcp/api/result_analyzer_real.py" ]; then
        echo "✅ Real analyzer exists"
    else
        echo "❌ ERROR: Real analyzer missing"
    fi
else
    echo "❌ Repository not found at $REPO"
    exit 1
fi

echo ""

# Check foam/run directory
FOAM_RUN="$HOME/foam/run"
echo "Checking cases directory..."
if [ -d "$FOAM_RUN" ]; then
    CASE_COUNT=$(find "$FOAM_RUN" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l)
    echo "✅ Cases directory: $FOAM_RUN"
    echo "   Cases found: $CASE_COUNT"

    if [ $CASE_COUNT -gt 0 ]; then
        echo ""
        echo "   Existing cases:"
        ls -1 "$FOAM_RUN" | head -5
    fi
else
    echo "⚠️ No cases directory yet: $FOAM_RUN"
    echo "   Will be created when first case is made"
fi

echo ""
echo "=================================="
echo "✅ VERIFICATION COMPLETE"
echo "=================================="
echo ""
echo "If all checks passed, you're ready to:"
echo "1. Create a new case in Claude Desktop"
echo "2. Run the simulation"
echo "3. Verify you get real, parameter-dependent results"
echo ""
