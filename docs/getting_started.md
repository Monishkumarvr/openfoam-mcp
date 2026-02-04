# Getting Started with OpenFOAM MCP Server

This guide will walk you through setting up and using the OpenFOAM MCP server for foundry simulations.

## Prerequisites Check

Before starting, verify you have:

```bash
# Check Python version (need 3.10+)
python --version

# Check OpenFOAM installation
which blockMesh
which interFoam

# Source OpenFOAM if needed
source /opt/openfoam11/etc/bashrc
```

## Installation

### 1. Install OpenFOAM MCP Server

```bash
cd /path/to/openfoam-mcp
pip install -e .
```

### 2. Verify Installation

```bash
# Test import
python -c "from openfoam_mcp.server import app; print('✓ Import successful')"

# Run tests
pytest tests/ -v
```

### 3. Configure Claude Code

Edit `~/.claude/mcp.json`:

```json
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
```

### 4. Test the Server

```bash
# Run server manually (for testing)
python run_mcp_server.py
```

The server should start and wait for MCP connections.

## Your First Simulation

### Using Claude Code

1. **Start Claude Code**:
```bash
claude-code
```

2. **Create a simple case**:
```
Create a mold filling simulation for aluminum at 750°C named "my_first_casting"
```

3. **Set up geometry**:
```
Set up a box geometry for my_first_casting: 0.1m x 0.1m x 0.1m with medium mesh
```

4. **Generate mesh**:
```
Generate mesh for my_first_casting
```

5. **Run simulation**:
```
Run simulation for my_first_casting for 5 seconds
```

6. **Analyze results**:
```
Analyze results for my_first_casting
```

### Expected Output

You should see:
- Case created at `~/foam/run/my_first_casting`
- Mesh with ~8000 cells
- Simulation completes in 1-2 minutes
- Analysis showing filling pattern and defect predictions

## Understanding the Workflow

### 1. Case Creation

When you create a case, the server:
- Creates directory structure (0/, constant/, system/)
- Populates with template files
- Configures material properties from database
- Saves metadata for tracking

### 2. Geometry Setup

Two options:

**Option A: Parametric (blockMesh)**
- Simple geometries (boxes, channels)
- Fast mesh generation
- Good for learning and testing

**Option B: STL Import (snappyHexMesh)**
- Complex geometries from CAD
- Requires more mesh tuning
- Production-quality meshes

### 3. Simulation Execution

The server:
- Sources OpenFOAM environment
- Runs selected solver (interFoam, interPhaseChangeFoam, etc.)
- Monitors progress
- Captures output

### 4. Result Analysis

The analyzer:
- Reads OpenFOAM field files
- Calculates metrics (Niyama, solidification time, etc.)
- Predicts defects
- Generates summaries

## Common Tasks

### List All Cases

```
List all my OpenFOAM cases
```

### Get Case Status

```
What is the status of my_first_casting?
```

### Export Results

```
Export my_first_casting results in VTK format
```

Then visualize:
```bash
paraview ~/foam/run/my_first_casting/VTK/
```

### Run in Parallel

```
Run my_first_casting in parallel with 4 processors
```

## Troubleshooting

### Server Won't Start

**Error**: `ModuleNotFoundError: No module named 'mcp'`

**Solution**:
```bash
pip install mcp loguru
```

### OpenFOAM Commands Not Found

**Error**: `blockMesh: command not found`

**Solution**:
```bash
# Add to ~/.bashrc
source /opt/openfoam11/etc/bashrc

# Reload
source ~/.bashrc
```

### Case Already Exists

**Error**: `Case my_first_casting already exists`

**Solution**: Either delete the old case or use a new name:
```bash
rm -rf ~/foam/run/my_first_casting
```

### Simulation Diverges

**Symptoms**: Simulation stops with "FOAM FATAL ERROR"

**Solutions**:
1. Check mesh quality: `cd ~/foam/run/my_first_casting && checkMesh`
2. Reduce inlet velocity
3. Decrease time step in `system/controlDict`
4. Use finer mesh

### Slow Simulations

**If simulations are too slow**:

1. Use coarser mesh:
```
Regenerate mesh for my_first_casting with coarse refinement
```

2. Run in parallel:
```
Run my_first_casting in parallel with 8 processors
```

3. Reduce simulation time:
```
Run my_first_casting for 2 seconds instead
```

## Next Steps

1. **Try the examples**:
   - [Simple Mold Filling](../examples/simple_mold_filling.md)
   - [Solidification Analysis](../examples/solidification_analysis.md)

2. **Import your own geometry**:
   - Export STL from CAD software
   - Use `setup_geometry` with STL path

3. **Customize materials**:
   - Edit `openfoam_mcp/builders/case_builder.py`
   - Add your alloy properties

4. **Run parametric studies**:
   - Vary pouring temperature
   - Optimize gating system
   - Compare mold materials

## Learning Resources

### OpenFOAM Basics
- [OpenFOAM User Guide](https://www.openfoam.com/documentation/user-guide)
- [OpenFOAM Tutorials](https://wiki.openfoam.com/Tutorials)
- [blockMesh Documentation](https://www.openfoam.com/documentation/user-guide/4-mesh-generation-and-conversion/4.3-mesh-generation-with-the-blockmesh-utility)

### Casting Simulation
- [interFoam Tutorial](https://wiki.openfoam.com/Dambreak_with_interFoam)
- [VOF Method](https://en.wikipedia.org/wiki/Volume_of_fluid_method)
- [Casting Defects](https://en.wikipedia.org/wiki/Casting_defect)

### MCP Development
- [MCP Documentation](https://modelcontextprotocol.io/)
- [MCP Python SDK](https://github.com/anthropics/mcp-python-sdk)

## Tips for Success

1. **Start simple**: Begin with small, simple geometries
2. **Check quality**: Always run `checkMesh` before simulation
3. **Monitor progress**: Watch log files during long runs
4. **Iterate**: Use coarse meshes for initial testing
5. **Validate**: Compare results with analytical solutions when possible

## Getting Help

If you encounter issues:

1. Check the [examples](../examples/)
2. Review OpenFOAM log files in case directory
3. Run `checkMesh` to diagnose mesh problems
4. Open an issue on GitHub with:
   - Error message
   - Case setup details
   - OpenFOAM version

Happy simulating! 🎉
