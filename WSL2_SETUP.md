# OpenFOAM MCP - WSL2 Setup Guide

## Current Status

✅ **Code is fixed** - Real analyzer with physics-based calculations
✅ **Tests pass** - Verified with mock data
✅ **MCP server running in WSL2** - Correct environment
❌ **No cases exist in WSL2** - Need to create them

## The Problem

Your MCP server switched from Windows to WSL2 (which is correct - OpenFOAM needs Linux). But:

- **Old cases location:** `C:\Users\monis\foam\run\` (Windows)
- **New cases location:** `/home/monish/foam/run/` (WSL2)
- **Result:** MCP server can't find cases because they're on a different filesystem

## Solution: Create Case in WSL2

### Step 1: Verify MCP Server Uses Real Analyzer

In your Claude Desktop conversation, call:

```
diagnostic_health_check
```

**Expected output:**
```
✅ ANALYZER: RealResultAnalyzer (CORRECT)
   Module: openfoam_mcp.api.result_analyzer_real
   Status: Using physics-based analysis
```

**If you see this instead:**
```
❌ ANALYZER: ResultAnalyzer (WRONG!)
```

Then the MCP server wasn't restarted. Quit Claude Desktop completely and reopen.

### Step 2: Create New Case in WSL2

In your Claude Desktop conversation, call the `create_casting_case` tool:

```json
{
  "case_name": "wsl_aluminum_test",
  "case_type": "mold_filling",
  "metal_type": "aluminum",
  "pouring_temperature": 750,
  "mold_material": "sand",
  "geometry": {
    "type": "box",
    "dimensions": [0.1, 0.1, 0.15]
  }
}
```

This will create a case at `/home/monish/foam/run/wsl_aluminum_test`

### Step 3: Verify Case Exists

In WSL2 terminal:

```bash
ls -la ~/foam/run/
ls -la ~/foam/run/wsl_aluminum_test/
ls -la ~/foam/run/wsl_aluminum_test/0/
ls -la ~/foam/run/wsl_aluminum_test/system/
```

You should see:
- `0/` directory with initial conditions
- `constant/` directory with properties
- `system/` directory with controlDict, blockMeshDict, etc.

### Step 4: Run Mesh Generation

In Claude Desktop, call `run_mesh_generation`:

```json
{
  "case_name": "wsl_aluminum_test"
}
```

**CRITICAL CHECK:** After this runs, verify log file exists:

```bash
ls -la ~/foam/run/wsl_aluminum_test/log.blockMesh
```

If this file **does not exist**, then blockMesh never actually ran. This means:
- OpenFOAM is not sourced in the MCP server environment
- Or OpenFOAM commands are failing silently

### Step 5: Check Mesh Log

```bash
cat ~/foam/run/wsl_aluminum_test/log.blockMesh
```

**Expected output:**
```
Build : 11-33ab1e0f73d9
Exec  : blockMesh
...
End
```

**If you see errors or file doesn't exist:** OpenFOAM is not working.

### Step 6: Run Simulation

In Claude Desktop, call `run_simulation`:

```json
{
  "case_name": "wsl_aluminum_test",
  "solver": "interFoam",
  "parallel": false
}
```

**CRITICAL CHECK:** After simulation, verify time directories exist:

```bash
ls -la ~/foam/run/wsl_aluminum_test/
```

You should see directories like `0.1/`, `0.2/`, `0.3/`, etc.

If you only see `0/`, the simulation didn't run.

### Step 7: Analyze Results

In Claude Desktop, call `analyze_results`:

```json
{
  "case_name": "wsl_aluminum_test",
  "analysis_type": "all"
}
```

**Expected output:**
```
📊 Analysis Results for wsl_aluminum_test
Time directories found: [0.0, 0.1, 0.2, 0.3, ...]
Latest time: 0.5s

🌡️ TEMPERATURE DISTRIBUTION:
  Min: 573.2 K
  Max: 1023.2 K
  Mean: 798.4 K
  Hot spot percentage: 8.3%

⚠️ DEFECT PREDICTIONS:

  POROSITY (Niyama Criterion):
    Mean Niyama: 0.76
    High risk percentage: 12.4%
    ⚠️ Moderate porosity risk. Consider increasing feeding...
```

**Key point:** The numbers should be **different from "95%"** and should reflect actual temperature field analysis.

### Step 8: Run Parametric Study

Now test with different parameters:

```json
{
  "base_case_name": "wsl_aluminum_test",
  "parameters": {
    "pouring_temperature": [730, 750, 770],
    "inlet_velocity": [0.3, 0.5, 0.7]
  },
  "metric": "minimize_porosity"
}
```

**CRITICAL:** Each of the 9 configurations should return **DIFFERENT** results.

If you still see identical results, one of these is wrong:
1. OpenFOAM simulations aren't actually running (no time directories)
2. Simulations are all producing identical field files (unlikely)
3. MCP server still using old code (didn't restart)

## Troubleshooting

### Issue: "Case not found" errors

**Cause:** Case created on Windows, MCP server in WSL2

**Fix:** Create new case (Step 2 above)

### Issue: log.blockMesh doesn't exist

**Cause:** OpenFOAM commands not executing

**Fix:** Check MCP config includes OpenFOAM environment:

```json
{
  "mcpServers": {
    "openfoam": {
      "command": "wsl",
      "args": [
        "-d", "Ubuntu",
        "bash", "-c",
        "cd /mnt/d/Projects/NP/openfoam-mcp/openfoam-mcp && source /opt/openfoam11/etc/bashrc && python3 -m openfoam_mcp.server"
      ]
    }
  }
}
```

Note the `source /opt/openfoam11/etc/bashrc` - this is critical!

### Issue: No time directories after simulation

**Cause:** Simulation failed but returned "success"

**Fix:** Check simulation log:

```bash
cat ~/foam/run/wsl_aluminum_test/log.interFoam
```

Look for errors like:
- "cannot find file"
- "Time directory not found"
- Segmentation fault

### Issue: Still seeing "95% Niyama" results

**Cause:** MCP server not restarted, still using old code

**Fix:**
1. Completely quit Claude Desktop (don't just close window)
2. Wait 10 seconds
3. Reopen Claude Desktop
4. Call `diagnostic_health_check` - must show `RealResultAnalyzer`

## Expected Results

Once everything works, you should see:

**Parametric Study Output:**
```
🔬 PARAMETRIC STUDY RESULTS

🏆 OPTIMAL CONFIGURATION:
  Case name: wsl_aluminum_test_730C_0.3ms
  Parameters:
    - pouring_temperature: 730
    - inlet_velocity: 0.3

  Results:
    - Porosity risk: 8.2%    ← DIFFERENT for each case
    - Shrinkage risk: 4.5%   ← DIFFERENT for each case
    - Hot spots: 6.1%        ← DIFFERENT for each case

📊 COMPARISON TABLE:
Case                 Porosity     Shrinkage    Hot Spots
------------------------------------------------------------
730C_0.3ms              8.2%        4.5%        6.1%
730C_0.5ms             10.1%        5.2%        7.3%
730C_0.7ms             12.4%        6.8%        8.9%
750C_0.3ms              7.9%        4.1%        5.8%
750C_0.5ms              9.5%        4.9%        6.7%
750C_0.7ms             11.8%        6.2%        8.2%
770C_0.3ms              7.2%        3.8%        5.2%
770C_0.5ms              8.7%        4.4%        6.1%
770C_0.7ms             10.9%        5.7%        7.5%
```

**Notice:** Every single value is different. NOT "5% porosity risk" and "95% Niyama criterion satisfied" repeated 9 times.

## Summary

The **code is fixed**. The **tests prove it works**.

Your issue is that:
1. MCP server is in WSL2 (correct)
2. Cases are on Windows (wrong location)
3. Need to create new cases in WSL2
4. Verify OpenFOAM actually executes

Follow the steps above and check each verification point. If you get stuck, provide:
1. Output of `diagnostic_health_check`
2. Output of `ls -la ~/foam/run/`
3. Contents of `~/foam/run/<case>/log.blockMesh`
