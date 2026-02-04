# Example: Simple Mold Filling Simulation

This example demonstrates how to use the OpenFOAM MCP server to create and run a simple mold filling simulation.

## Scenario

We want to simulate pouring molten aluminum into a sand mold to create a simple rectangular casting.

## Specifications

- **Metal**: Aluminum
- **Pouring Temperature**: 750°C
- **Mold Material**: Sand
- **Geometry**: 200mm x 150mm x 100mm rectangular box
- **Pouring Velocity**: 0.5 m/s

## Step-by-Step Workflow

### Step 1: Create the Case

Ask Claude:
```
Create a mold filling simulation case named "aluminum_box" for aluminum at 750°C with a sand mold
```

Claude will execute:
- `create_casting_case` with appropriate parameters
- Case created at `~/foam/run/aluminum_box`

### Step 2: Set Up Geometry

Ask Claude:
```
Set up a box geometry for aluminum_box with dimensions 0.2m x 0.15m x 0.1m using medium mesh refinement
```

Claude will execute:
- `setup_geometry` with blockMesh parametric geometry
- Creates `blockMeshDict` with specified dimensions
- Configures mesh with ~20 cells per dimension

### Step 3: Configure Material Properties (Optional)

The default aluminum and sand properties are already set, but you can customize:

```
Update aluminum_box material properties: set aluminum density to 2650 kg/m³ and viscosity to 0.0012 Pa·s
```

### Step 4: Set Boundary Conditions

Ask Claude:
```
Configure boundary conditions for aluminum_box: inlet velocity 0.5 m/s, inlet temperature 1023 K, mold wall temperature 300 K
```

Claude will execute:
- `setup_boundary_conditions`
- Updates `0/U`, `0/alpha.metal`, `0/p_rgh` files

### Step 5: Generate Mesh

Ask Claude:
```
Generate the mesh for aluminum_box
```

Claude will execute:
- `run_mesh_generation`
- Runs `blockMesh`
- Reports mesh statistics (cells, points, quality)

### Step 6: Run Simulation

Ask Claude:
```
Run the simulation for aluminum_box using interFoam solver for 10 seconds with 0.5 second write intervals
```

Claude will execute:
- `run_simulation`
- Executes OpenFOAM `interFoam` solver
- Outputs results every 0.5 seconds

**Expected Runtime**: 2-5 minutes on a modern CPU

### Step 7: Analyze Results

Ask Claude:
```
Analyze the results for aluminum_box and predict all defects
```

Claude will execute:
- `analyze_results` with analysis_type="all"
- Provides:
  - Filling pattern analysis
  - Temperature distribution
  - Solidification time
  - Defect predictions (porosity, shrinkage, etc.)

### Step 8: Visualize (Optional)

Ask Claude:
```
Export the results for aluminum_box in VTK format
```

Claude will execute:
- `export_results`
- Converts OpenFOAM results to VTK
- Open in ParaView: `paraview ~/foam/run/aluminum_box/VTK/`

## Expected Results

### Filling Pattern
- Metal enters from bottom inlet at 0.5 m/s
- Fills mold in approximately 8 seconds
- Minimal air entrapment due to bottom-up filling

### Temperature Distribution
- Initial pouring temperature: 1023 K (750°C)
- Mold wall cooling effect visible at boundaries
- Temperature gradients: ~10-15 K/cm near walls

### Defects
- **Porosity**: Low risk (proper feeding)
- **Shrinkage**: Low to moderate risk in center
- **Hot Spots**: Identified at center of thick sections
- **Cold Shuts**: Low risk (adequate pouring temperature)
- **Misruns**: No misruns (complete filling)

## Optimization Ideas

Ask Claude to optimize:

```
Optimize the gating system for aluminum_box to minimize porosity
```

This will run parametric studies varying gate positions and sizes to find the optimal configuration.

## Variations

### High-Pressure Pour
```
Update inlet velocity to 2.0 m/s for aluminum_box
```

### Different Metal
```
Create a new case "steel_box" for steel at 1650°C with the same geometry
```

### Parallel Execution
```
Run aluminum_box simulation in parallel with 4 processors
```

## Troubleshooting

### Mesh Quality Issues
If mesh quality is poor:
```
Regenerate mesh for aluminum_box with fine refinement
```

### Simulation Divergence
If simulation diverges:
- Reduce inlet velocity
- Decrease time step in `system/controlDict`
- Check mesh quality with `checkMesh`

### Long Runtime
For faster results:
- Use coarser mesh
- Enable parallel execution
- Reduce simulation end time

## Next Steps

After mastering this example, try:
1. [Solidification Analysis Example](solidification_analysis.md)
2. Import custom STL geometry
3. Add risers and gating systems
4. Multi-material simulations
