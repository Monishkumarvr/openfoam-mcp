# OpenFOAM MCP Server - Quick Start

Get up and running with OpenFOAM + AI in 5 minutes!

## 🚀 Installation (2 minutes)

```bash
# 1. Navigate to project
cd /home/user/openfoam-mcp

# 2. Install dependencies
pip install -e .

# 3. Verify OpenFOAM is available
which blockMesh || echo "⚠️  OpenFOAM not found - install first!"

# 4. Configure Claude Code
cat >> ~/.claude/mcp.json << 'EOF'
{
  "mcpServers": {
    "openfoam": {
      "command": "python",
      "args": ["-m", "openfoam_mcp.server"],
      "env": {
        "FOAM_INST_DIR": "/opt/openfoam11"
      }
    }
  }
}
EOF
```

## ✅ Test Installation (1 minute)

```bash
# Run tests
pytest tests/test_case_manager.py -v

# Expected output: All tests pass ✓
```

## 🎮 First Simulation (2 minutes)

Start Claude Code and paste:

```
Create a mold filling simulation named "test_aluminum" for aluminum at 750°C with sand mold.
Then set up a box geometry 0.1m x 0.1m x 0.1m with medium mesh.
Generate the mesh and run for 3 seconds.
Finally analyze the results.
```

Claude will:
1. ✅ Create case at `~/foam/run/test_aluminum`
2. ✅ Set up geometry and mesh (~5000 cells)
3. ✅ Run OpenFOAM simulation
4. ✅ Predict defects and analyze results

**Total time**: ~2 minutes

## 📊 View Results

```bash
# Export to VTK
cd ~/foam/run/test_aluminum

# View in ParaView
paraview
# File → Open → VTK/test_aluminum_*.vtk
```

## 🎯 What You Can Do Now

### Ask Claude:

**Create simulations:**
- *"Create a steel casting simulation at 1650°C"*
- *"Set up a continuous casting case for aluminum"*

**Analyze:**
- *"Predict defects in my casting"*
- *"Analyze the temperature distribution"*
- *"Find hot spots and shrinkage locations"*

**Optimize:**
- *"Optimize the gating system to minimize porosity"*
- *"What's the best riser size for this casting?"*

**Visualize:**
- *"Export results in VTK format"*
- *"Show me the filling pattern"*

## 📚 Next Steps

1. **Read examples**:
   - [Simple Mold Filling](examples/simple_mold_filling.md)
   - [Solidification Analysis](examples/solidification_analysis.md)

2. **Try your own geometry**:
   - Export STL from SolidWorks/Fusion 360
   - Tell Claude: *"Use geometry from /path/to/part.stl"*

3. **Customize materials**:
   - Edit `openfoam_mcp/builders/case_builder.py`
   - Add custom alloy properties

## 🆘 Troubleshooting

| Issue | Solution |
|-------|----------|
| `blockMesh not found` | `source /opt/openfoam11/etc/bashrc` |
| `ModuleNotFoundError: mcp` | `pip install mcp loguru` |
| Simulation diverges | Use coarser mesh or reduce velocity |
| Too slow | Run in parallel: *"Use 4 processors"* |

## 💡 Pro Tips

1. **Start coarse**: Use "coarse" mesh for testing, "fine" for production
2. **Run parallel**: Add *"in parallel with 4 processors"* for 4x speed
3. **Check quality**: Ask Claude *"Check mesh quality"* if simulation fails
4. **Iterate fast**: Use 2-5 second simulations for quick iterations

## 🎓 Learn More

- **Full Documentation**: [docs/getting_started.md](docs/getting_started.md)
- **OpenFOAM Tutorials**: https://wiki.openfoam.com/Tutorials
- **MCP Protocol**: https://modelcontextprotocol.io/

---

**Ready to cast? Ask Claude to create your first simulation! 🏭**
