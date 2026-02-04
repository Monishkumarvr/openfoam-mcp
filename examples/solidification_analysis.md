# Example: Solidification Analysis with Heat Transfer

This example demonstrates how to simulate the complete casting process including mold filling and solidification with heat transfer.

## Scenario

Casting a steel component with focus on solidification behavior and defect prediction.

## Specifications

- **Metal**: Steel
- **Pouring Temperature**: 1650°C
- **Mold Material**: Sand
- **Analysis Focus**: Solidification time, temperature distribution, shrinkage prediction

## Workflow

### Step 1: Create Solidification Case

Ask Claude:
```
Create a solidification simulation case named "steel_solidification" for steel at 1650°C in a sand mold
```

This creates a case configured for `interPhaseChangeFoam` solver with heat transfer.

### Step 2: Import Complex Geometry

Ask Claude:
```
Set up geometry for steel_solidification using STL file at /path/to/your/casting.stl with fine mesh refinement
```

The server will:
- Copy STL to `constant/triSurface/`
- Configure `snappyHexMeshDict`
- Set refinement levels for surface capture

### Step 3: Generate Mesh

Ask Claude:
```
Generate mesh for steel_solidification in parallel with 4 processors
```

This runs:
- `blockMesh` for background mesh
- `decomposePar` for domain decomposition
- `snappyHexMesh -parallel` for surface refinement
- `reconstructParMesh` to merge results

### Step 4: Run Coupled Simulation

Ask Claude:
```
Run steel_solidification simulation using interPhaseChangeFoam for 100 seconds, write every 5 seconds, in parallel with 4 processors
```

This simulates:
- Mold filling with gravity
- Heat transfer to mold
- Phase change (liquid → solid)
- Solidification front progression

**Expected Runtime**: 30-60 minutes depending on mesh size

### Step 5: Comprehensive Analysis

Ask Claude:
```
Perform complete analysis on steel_solidification: filling pattern, temperature distribution, solidification time, and predict all defects
```

Results include:

#### Filling Pattern
- Flow velocity vectors
- Filling time analysis
- Turbulence indicators

#### Temperature Distribution
- Temperature contours over time
- Cooling curves at critical points
- Thermal gradients

#### Solidification Analysis
- Solidification front progression
- Local solidification time (LST)
- Last regions to solidify

#### Defect Predictions

**Porosity**:
- Niyama criterion evaluation
- Pressure gradients during solidification
- Risk zones identified

**Shrinkage**:
- Volume change during solidification
- Feeding distance analysis
- Isolated hot spot detection

**Hot Spots**:
- Thick section identification
- Modulus calculations
- Centerline shrinkage risk

### Step 6: Optimize Riser Design

Ask Claude:
```
Optimize the gating system for steel_solidification to ensure uniform solidification
```

This will:
- Run parametric studies
- Vary riser sizes and positions
- Evaluate Solidification Rate (G/R ratio)
- Recommend optimal configuration

## Advanced Analysis

### Cooling Curve Extraction

Ask Claude:
```
Extract temperature history at point (0.05, 0.05, 0.05) in steel_solidification
```

This helps:
- Validate solidification time
- Compare with analytical models (Chvorinov's rule)
- Assess dendrite arm spacing

### Niyama Criterion Calculation

The result analyzer automatically calculates:
```
Niyama = G / √R
```
Where:
- G = Temperature gradient (K/m)
- R = Cooling rate (K/s)

**Interpretation**:
- Ny > 1.0: Safe (no porosity)
- 0.5 < Ny < 1.0: Moderate risk
- Ny < 0.5: High porosity risk

### Feeding Distance Analysis

For shrinkage prediction:
```
Feeding Distance = L = C × √(t_sol)
```
Where:
- L = Maximum feeding distance
- t_sol = Local solidification time
- C = Material constant

## Visualization in ParaView

After exporting:
```
Export steel_solidification results in VTK format
```

Open in ParaView and visualize:

1. **Alpha Field**: Mold filling progression
2. **Temperature Field**: Heat distribution
3. **Velocity Field**: Flow patterns
4. **Calculated Fields**: Niyama criterion, solidification time

### ParaView Tips

**Create Isosurface**:
- Filters → Contour
- Select variable: `alpha.metal`
- Isovalues: 0.5 (liquid-solid interface)

**Animate Solidification Front**:
- View → Animation View
- Play through time steps to see solidification progression

**Temperature Slices**:
- Filters → Slice
- Slice Type: Plane
- Color by: T (temperature)

## Expected Results

### Typical Steel Casting

**Filling Phase** (0-10 seconds):
- Turbulent entry at gate
- Progressive filling from bottom
- Air venting from risers

**Solidification Phase** (10-100 seconds):
- Directional solidification from mold walls
- Hot spots in thick sections
- Riser feeds last 30 seconds

**Defect Locations**:
- Porosity: Minimal (if Niyama > 1.0)
- Shrinkage: Center of thick sections
- Hot tear risk: Sharp corners

## Parametric Studies

### Pouring Temperature Study

```
Run parametric study on steel_solidification varying pouring temperature from 1600°C to 1700°C in 25°C steps
```

Evaluate:
- Effect on filling pattern
- Solidification time variation
- Defect sensitivity

### Mold Material Comparison

Create variants:
```
Create steel_solidification_ceramic with ceramic mold
Create steel_solidification_metal with metal mold
```

Compare:
- Cooling rates
- Solidification times
- Defect likelihood

## Validation

### Chvorinov's Rule

Validate solidification time:
```
t_sol = C × (V/A)²
```

Compare simulation results with analytical prediction.

### Modulus Method

For each section, calculate:
```
M = V/A (Modulus)
```

Sections with higher modulus solidify later → shrinkage risk

## Troubleshooting

### Simulation Doesn't Converge
- Check mesh quality: `checkMesh`
- Reduce max Courant number in `controlDict`
- Increase solver iterations in `fvSolution`

### Phase Change Not Working
- Verify temperature range spans liquidus-solidus
- Check material properties in `thermophysicalProperties`
- Ensure `interPhaseChangeFoam` solver is used

### Long Computation Time
- Reduce mesh resolution in non-critical areas
- Use adaptive mesh refinement
- Run on HPC cluster with more processors

## Next Steps

1. Integrate with mechanical stress analysis (OpenFOAM → mechanical FEA)
2. Couple with microstructure prediction (SDAS, grain size)
3. Multi-cavity simulations
4. Automated defect remediation suggestions
