# OpenFOAM MCP Diagnostic Guide

## Current Status

✅ **Fake analyzer deleted** (commit 798e1fa)
✅ **Real analyzer integrated** into server.py
✅ **Parametric study engine** uses RealResultAnalyzer
✅ **Test suite passes** with mock data

## Why You Might Still See Identical Results

### Problem 1: MCP Server Not Restarted
**Symptom:** Still seeing "95% Niyama criterion satisfied"

**Solution:**
```bash
# Kill any running MCP server
pkill -f "openfoam.*mcp" || pkill -f "python.*server.py"

# If using Claude Desktop, restart it completely
# The MCP server runs as a subprocess and needs full restart

# Verify no MCP processes running
ps aux | grep -i mcp
```

### Problem 2: OpenFOAM Simulations Not Running
**Symptom:** Errors like "No time directories found"

**Diagnosis:**
```bash
# Check if OpenFOAM commands are available
which blockMesh
which interFoam

# Check if any cases exist
ls -la ~/foam/run/

# Try creating a case manually
cd /home/user/openfoam-mcp
python3 << 'EOF'
import asyncio
from pathlib import Path
from openfoam_mcp.api.case_manager import CaseManager

async def test():
    mgr = CaseManager()
    result = await mgr.create_case(
        case_name="diagnostic_test",
        case_type="mold_filling",
        metal_type="steel",
        pouring_temperature=1600,
        mold_material="sand"
    )
    print(f"Case created: {result}")

asyncio.run(test())
EOF
```

### Problem 3: Using Old Cached Code
**Symptom:** Still seeing old behavior after updates

**Solution:**
```bash
cd /home/user/openfoam-mcp

# Clear all Python cache
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete

# Pull latest changes
git pull origin main

# Verify fake analyzer is gone
ls -la openfoam_mcp/api/result_analyzer.py  # Should not exist

# Verify real analyzer exists
ls -la openfoam_mcp/api/result_analyzer_real.py  # Should exist
```

## Verification Steps

### Step 1: Verify Code is Updated
```bash
cd /home/user/openfoam-mcp
git log --oneline -5
# Should show:
# 798e1fa Delete fake result_analyzer.py with hardcoded responses
# 2d50632 Add comprehensive implementation documentation
# 2b22e45 Fix field parser time formatting and add comprehensive tests
```

### Step 2: Test the Real Analyzer
```bash
cd /home/user/openfoam-mcp
python3 tests/test_real_analyzer.py
# Should output: "🎉 ALL TESTS PASSED!"
```

### Step 3: Check MCP Server Configuration
If using Claude Desktop, check `~/.config/Claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "openfoam": {
      "command": "python",
      "args": [
        "-m",
        "openfoam_mcp.server"
      ],
      "cwd": "/home/user/openfoam-mcp",
      "env": {
        "PYTHONPATH": "/home/user/openfoam-mcp"
      }
    }
  }
}
```

**Critical:** The `cwd` must point to `/home/user/openfoam-mcp`, not somewhere else!

### Step 4: Run a Single Case Test
```python
# Create this as test_single_case.py
import asyncio
from pathlib import Path
from openfoam_mcp.api.result_analyzer_real import RealResultAnalyzer

async def test():
    # First, check if any cases exist
    run_dir = Path.home() / "foam" / "run"
    print(f"Checking {run_dir}")

    if not run_dir.exists():
        print(f"❌ No cases directory exists at {run_dir}")
        print(f"   OpenFOAM simulations have not created any cases")
        return

    cases = list(run_dir.glob("*"))
    print(f"Found {len(cases)} cases:")
    for case in cases:
        print(f"  - {case.name}")

    if not cases:
        print("❌ No cases found - create one first")
        return

    # Try to analyze first case
    analyzer = RealResultAnalyzer()
    result = await analyzer.analyze(
        case_name=cases[0].name,
        analysis_type="all"
    )

    print(f"\n📊 Analysis Result:")
    print(f"Time directories: {result.get('time_directories', 'N/A')}")

    if "error" in result:
        print(f"❌ Error: {result['error']}")
    else:
        print(f"✅ Analysis successful")

        # Check if we got real data or errors
        if "defects" in result:
            defects = result["defects"]
            if "porosity" in defects and "error" not in defects["porosity"]:
                por = defects["porosity"]
                print(f"   Porosity risk: {por.get('high_risk_percentage', 0):.1f}%")
                print(f"   Niyama mean: {por.get('niyama_stats', {}).get('mean', 0):.2f}")
                print(f"✅ REAL ANALYZER IS WORKING!")
            else:
                print(f"⚠️ No field data found")

asyncio.run(test())
```

Run it:
```bash
python3 test_single_case.py
```

## Expected Behavior

### If Everything Works:
```
✅ REAL ANALYZER IS WORKING!
   Porosity risk: 12.3%
   Niyama mean: 0.88
```

### If Simulations Haven't Run:
```
❌ Error: No time directories found - simulation may not have run
```
This means OpenFOAM hasn't created output files. Cases need to run `blockMesh` and `interFoam`.

### If Still Seeing "95% Niyama":
```
❌ FAKE ANALYZER STILL ACTIVE
```
This means:
1. MCP server wasn't restarted, OR
2. You're running code from a different location, OR
3. The MCP client is caching responses

## Common Issues

### Issue: "ModuleNotFoundError: No module named 'mcp'"
**Fix:**
```bash
pip install mcp
```

### Issue: "No module named 'openfoam_mcp'"
**Fix:**
```bash
cd /home/user/openfoam-mcp
pip install -e .
```

### Issue: Parametric study returns identical results
**Root Cause:** One of these:
1. OpenFOAM simulations are failing silently
2. Field files aren't being generated
3. All cases are producing errors (filtered out as "invalid")
4. MCP server is running old code

**Debug:**
```bash
# Check if simulations are actually running
ls -la ~/foam/run/*/0/
ls -la ~/foam/run/*/[0-9]*/T  # Temperature field files

# If no field files exist, simulations didn't complete
```

## Next Steps

1. **Restart MCP server** (most important!)
2. **Clear Python cache**
3. **Verify git is up to date**
4. **Run diagnostic tests above**
5. **Check if simulations produce field files**

If you're still seeing identical "95%" results after all this, the MCP client is not connecting to this repository's code.
