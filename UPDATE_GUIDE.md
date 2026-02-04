# 🔄 OpenFOAM MCP Update Guide

**IMPORTANT:** If you're getting `KeyError: 'metal_nu'` or other errors, you need to update your installation!

## 🐛 Bug Fixes in Latest Version

### ✅ Fixed (Commit 94ca64d)
- **Critical:** Added `metal_nu` (kinematic viscosity) calculation
- **Issue:** Template expected `metal_nu` but it wasn't calculated
- **Impact:** Prevented ANY case from being created
- **Fix:** Added `metal_nu = viscosity / density` calculation

### ✅ Verified Working
- All 5 metals build successfully (steel, aluminum, iron, copper, bronze)
- All case types work (mold_filling, solidification)
- All template syntax validated
- Material properties physically realistic

## 🚀 How to Update

### **Step 1: Pull Latest Code**

```bash
cd ~/openfoam-mcp

# Save any local changes
git stash

# Pull latest fixes
git pull origin main

# Show what changed
git log --oneline -5
```

**Expected output:**
```
94ca64d Fix: Calculate kinematic viscosity for OpenFOAM templates
33d0d7c Add GitHub push helper scripts and documentation
4d2c1ae Initial commit: OpenFOAM MCP Server...
```

If you see commit `94ca64d`, you have the fix! ✅

---

### **Step 2: Reinstall Package**

#### **If using virtual environment (recommended):**

```bash
cd ~/openfoam-mcp

# Activate venv
source venv/bin/activate

# Reinstall
pip install --upgrade pip
pip install -e .

# Verify installation
python -c "from openfoam_mcp.builders.case_builder import CaseBuilder; print('✅ Updated!')"
```

#### **If using system Python:**

```bash
cd ~/openfoam-mcp

# Reinstall
pip3 install -e .

# Verify installation
python3 -c "from openfoam_mcp.builders.case_builder import CaseBuilder; print('✅ Updated!')"
```

---

### **Step 3: Restart Claude Code (if using MCP)**

```bash
# Restart Claude Code to reload the updated module
# The MCP server will now use the fixed code
```

---

## 🧪 Test the Fix

Run the comprehensive test suite:

```bash
cd ~/openfoam-mcp

# Install test dependencies
pip install loguru

# Run tests
python3 tests/test_comprehensive.py
```

**Expected output:**
```
🔬 OPENFOAM MCP COMPREHENSIVE TEST SUITE
======================================================================
TEST 1: CaseBuilder
  ✅ steel      + mold_filling         → 8 files
  ✅ aluminum   + mold_filling         → 8 files
  ... (10 tests pass)

TEST 2: Material Properties
  ✅ steel: All properties valid
  ✅ aluminum: All properties valid
  ... (all valid)

🎉 ALL TESTS PASSED! OpenFOAM MCP is working correctly.
```

---

## 🔍 Verify Kinematic Viscosity

Test that `metal_nu` is now calculated correctly:

```bash
python3 << 'TEST'
from openfoam_mcp.builders.case_builder import CaseBuilder

builder = CaseBuilder('mold_filling')
builder.set_metal_type('aluminum')
builder.set_pouring_temperature(750)
builder.set_mold_material('sand')

files = builder.build()

# Check transportProperties
if 'constant/transportProperties' in files:
    content = files['constant/transportProperties']
    print("✅ transportProperties generated")

    # Show nu line
    for line in content.split('\n'):
        if 'nu' in line and 'Newtonian' not in line:
            print(f"   {line.strip()}")

    # Expected: nu  4.814815e-07; (for aluminum)
    print("\n📊 Expected: nu ≈ 4.8e-07 m²/s for aluminum")
else:
    print("❌ transportProperties not generated")
TEST
```

**Expected output:**
```
✅ transportProperties generated
   nu              4.814814814814815e-07;
   nu              1.48e-05;

📊 Expected: nu ≈ 4.8e-07 m²/s for aluminum
```

---

## 🆘 Troubleshooting

### **Problem: Still getting KeyError: 'metal_nu'**

**Cause:** Your Python is still using the old cached module.

**Solution:**
```bash
# Find and remove all cached files
find ~/openfoam-mcp -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# Deactivate and reactivate venv
deactivate
source ~/openfoam-mcp/venv/bin/activate

# Reinstall
pip install -e ~/openfoam-mcp

# Test again
python -c "from openfoam_mcp.builders.case_builder import CaseBuilder; print('OK')"
```

---

### **Problem: git pull says "Already up to date"**

**Cause:** You might not have the remote configured correctly.

**Solution:**
```bash
cd ~/openfoam-mcp

# Check remote
git remote -v

# Should show:
# origin  https://github.com/Monishkumarvr/openfoam-mcp.git (fetch)
# origin  https://github.com/Monishkumarvr/openfoam-mcp.git (push)

# If not, add it:
git remote add origin https://github.com/Monishkumarvr/openfoam-mcp.git

# Then pull
git fetch origin
git merge origin/main
```

---

### **Problem: ImportError: No module named 'mcp'**

**Cause:** Missing dependencies.

**Solution:**
```bash
pip install mcp loguru httpx
```

---

### **Problem: Tests fail with "No module named 'loguru'"**

**Cause:** Missing optional dependency.

**Solution:**
```bash
pip install loguru
```

---

## 📊 What Changed?

### Before (Broken):
```python
# case_builder.py
content = content_template.format(
    metal_density=metal_props["density"],
    metal_viscosity=metal_props["viscosity"],
    # metal_nu was MISSING! ❌
    ...
)
```

### After (Fixed):
```python
# case_builder.py
# Calculate kinematic viscosity (nu = mu / rho)
metal_nu = metal_props["viscosity"] / metal_props["density"]

content = content_template.format(
    metal_density=metal_props["density"],
    metal_viscosity=metal_props["viscosity"],
    metal_nu=metal_nu,  # ✅ Now included!
    ...
)
```

---

## ✅ Verification Checklist

After updating, verify:

- [ ] `git log` shows commit `94ca64d`
- [ ] `pip show openfoam-mcp` or `pip list | grep openfoam` shows package installed
- [ ] Test import works: `python -c "from openfoam_mcp.server import app"`
- [ ] Test case builder works: Run test script above
- [ ] MCP server starts without errors
- [ ] Can create cases through Claude Code

---

## 🎯 Quick Update Script

Save this as `update.sh`:

```bash
#!/bin/bash

echo "🔄 Updating OpenFOAM MCP..."

cd ~/openfoam-mcp || exit 1

# Pull latest
git pull origin main

# Activate venv if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Clear cache
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# Reinstall
pip install -e .

# Test
python -c "from openfoam_mcp.builders.case_builder import CaseBuilder; print('✅ Updated successfully!')"

echo ""
echo "🎉 Update complete! Restart Claude Code to use the updated server."
```

Run it:
```bash
chmod +x update.sh
./update.sh
```

---

## 📝 Commit History

```
94ca64d (Latest) - Fix: Calculate kinematic viscosity
33d0d7c - Add GitHub push helper scripts
4d2c1ae - Initial commit
```

**You need commit `94ca64d` or later!**

---

## 🆘 Still Having Issues?

1. **Check which version you're running:**
   ```bash
   cd ~/openfoam-mcp
   git rev-parse HEAD
   # Should output: 94ca64d... or later
   ```

2. **Completely reinstall:**
   ```bash
   cd ~
   rm -rf openfoam-mcp
   git clone https://github.com/Monishkumarvr/openfoam-mcp.git
   cd openfoam-mcp
   python3 -m venv venv
   source venv/bin/activate
   pip install -e .
   ```

3. **Run tests:**
   ```bash
   python3 tests/test_comprehensive.py
   ```

4. **Check GitHub for latest:**
   - Visit: https://github.com/Monishkumarvr/openfoam-mcp
   - Latest commit should be `94ca64d` or newer
   - Check "commits" to see full history

---

**After updating, you should be able to create casting cases successfully!** 🎉
