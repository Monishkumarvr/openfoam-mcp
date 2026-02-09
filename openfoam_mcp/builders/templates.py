"""OpenFOAM case file templates for casting simulations."""

# Template for mold filling simulation
MOLD_FILLING_TEMPLATE = {
    "system/controlDict": """/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  v2306                                 |
|   \\\\  /    A nd           | Website:  www.openfoam.com                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      controlDict;
}}}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

application     foamRun;

solver          incompressibleVoF;

startFrom       startTime;

startTime       0;

stopAt          endTime;

endTime         10;

deltaT          0.001;

writeControl    adjustableRunTime;

writeInterval   0.5;

purgeWrite      0;

writeFormat     ascii;

writePrecision  6;

writeCompression off;

timeFormat      general;

timePrecision   6;

runTimeModifiable yes;

adjustTimeStep  yes;

maxCo           0.5;

maxAlphaCo      0.5;

maxDeltaT       1;

// ************************************************************************* //
""",

    "system/fvSchemes": """/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  v2306                                 |
|   \\\\  /    A nd           | Website:  www.openfoam.com                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      fvSchemes;
}}}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

ddtSchemes
{{{{
    default         Euler;
}}}}

gradSchemes
{{{{
    default         Gauss linear;
}}}}

divSchemes
{{{{
    div(rhoPhi,U)   Gauss linearUpwind grad(U);
    div(phi,alpha)  Gauss vanLeer;
    div(phirb,alpha) Gauss linear;
    div(((rho*nuEff)*dev2(T(grad(U))))) Gauss linear;
}}}}

laplacianSchemes
{{{{
    default         Gauss linear corrected;
}}}}

interpolationSchemes
{{{{
    default         linear;
}}}}

snGradSchemes
{{{{
    default         corrected;
}}}}

// ************************************************************************* //
""",

    "system/fvSolution": """/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  v2306                                 |
|   \\\\  /    A nd           | Website:  www.openfoam.com                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      fvSolution;
}}}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

solvers
{{{{
    "alpha.metal.*"
    {{{{
        nAlphaCorr      2;
        nAlphaSubCycles 1;
        cAlpha          1;
    }}}}

    pcorr
    {{{{
        solver          PCG;
        preconditioner  DIC;
        tolerance       1e-5;
        relTol          0;
    }}}}

    p_rgh
    {{{{
        solver          PCG;
        preconditioner  DIC;
        tolerance       1e-07;
        relTol          0.05;
    }}}}

    p_rghFinal
    {{{{
        $p_rgh;
        relTol          0;
    }}}}

    U
    {{{{
        solver          smoothSolver;
        smoother        symGaussSeidel;
        tolerance       1e-06;
        relTol          0;
    }}}}
}}}}

PIMPLE
{{{{
    momentumPredictor   no;
    nOuterCorrectors    1;
    nCorrectors         3;
    nNonOrthogonalCorrectors 0;
}}}}

relaxationFactors
{{{{
    equations
    {{{{
        ".*"            1;
    }}}}
}}}}

// ************************************************************************* //
""",

    "constant/transportProperties": """/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  v2306                                 |
|   \\\\  /    A nd           | Website:  www.openfoam.com                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "constant";
    object      transportProperties;
}}}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

phases (metal air);

metal
{{{{
    transportModel  Newtonian;
    nu              {metal_nu};
    rho             {metal_density};
}}}}

air
{{{{
    transportModel  Newtonian;
    nu              1.48e-05;
    rho             1;
}}}}

sigma           0.07;

// ************************************************************************* //
""",

    "constant/g": """/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  v2306                                 |
|   \\\\  /    A nd           | Website:  www.openfoam.com                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{{{
    version     2.0;
    format      ascii;
    class       uniformDimensionedVectorField;
    location    "constant";
    object      g;
}}}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 1 -2 0 0 0 0];
value           (0 0 -9.81);

// ************************************************************************* //
""",

    "constant/momentumTransport": """/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  11                                    |
|   \\\\  /    A nd           | Website:  www.openfoam.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "constant";
    object      momentumTransport;
}}}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

simulationType  laminar;

// ************************************************************************* //
""",

    "0/alpha.metal": """/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  v2306                                 |
|   \\\\  /    A nd           | Website:  www.openfoam.com                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    object      alpha.metal;
}}}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 0 0 0 0 0 0];

internalField   uniform 0;

boundaryField
{{{{
    walls
    {{{{
        type            zeroGradient;
    }}}}

    inlet
    {{{{
        type            fixedValue;
        value           uniform 1;
    }}}}

    outlet
    {{{{
        type            inletOutlet;
        inletValue      uniform 0;
        value           uniform 0;
    }}}}
}}}}

// ************************************************************************* //
""",

    "0/U": """/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  v2306                                 |
|   \\\\  /    A nd           | Website:  www.openfoam.com                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{{{
    version     2.0;
    format      ascii;
    class       volVectorField;
    object      U;
}}}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 1 -1 0 0 0 0];

internalField   uniform (0 0 0);

boundaryField
{{{{
    walls
    {{{{
        type            noSlip;
    }}}}

    inlet
    {{{{
        type            fixedValue;
        value           uniform (0 0 0.5);
    }}}}

    outlet
    {{{{
        type            pressureInletOutletVelocity;
        value           uniform (0 0 0);
    }}}}
}}}}

// ************************************************************************* //
""",

    "0/p_rgh": """/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  v2306                                 |
|   \\\\  /    A nd           | Website:  www.openfoam.com                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    object      p_rgh;
}}}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [1 -1 -2 0 0 0 0];

internalField   uniform 0;

boundaryField
{{{{
    walls
    {{{{
        type            fixedFluxPressure;
        value           uniform 0;
    }}}}

    inlet
    {{{{
        type            fixedFluxPressure;
        value           uniform 0;
    }}}}

    outlet
    {{{{
        type            totalPressure;
        p0              uniform 0;
        value           uniform 0;
    }}}}
}}}}

// ************************************************************************* //
"""
}

# Template for solidification simulation (with heat transfer)
# Template for solidification simulation (with heat transfer)
SOLIDIFICATION_TEMPLATE = {
    "system/controlDict": """/*--------------------------------*- C++ -*----------------------------------*\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  11                                    |
|   \\  /    A nd           | Website:  www.openfoam.org                      |
|    \\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      controlDict;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

application     foamRun;

solver          compressibleVoF;

startFrom       startTime;

startTime       0;

stopAt          endTime;

endTime         100;

// Initial timestep for solidification (stable formulation allows larger dt)
deltaT          1e-5;

writeControl    adjustableRunTime;

writeInterval   5;

purgeWrite      0;

writeFormat     binary;

writePrecision  6;

writeCompression off;

timeFormat      general;

timePrecision   6;

runTimeModifiable yes;

// Adaptive timestep control
adjustTimeStep  yes;

// Courant limits for solidification with stable source terms
maxCo           0.5;

// Interface Courant for VOF stability
maxAlphaCo      0.5;

// Maximum timestep - prevents missing transients
maxDeltaT       0.01;

// Maximum diffusion number for thermal stability
maxDi           10;

// ************************************************************************* //
""",

    "system/fvSchemes": """/*--------------------------------*- C++ -*----------------------------------*\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  11                                    |
|   \\  /    A nd           | Website:  www.openfoam.org                      |
|    \\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      fvSchemes;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

ddtSchemes
{{
    default         Euler;
}}

gradSchemes
{{
    default         Gauss linear;
    limited         cellLimited Gauss linear 1;
}}

divSchemes
{{
    default                             none;
    
    div(phi,alpha)                      Gauss vanLeer;
    div(phi,alpha.metal)                Gauss vanLeer;
    div(phi,alpha.air)                  Gauss vanLeer;
    div(phirb,alpha)                    Gauss linear;
    div(phirb,alpha.metal)              Gauss linear;
    div(phirb,alpha.air)                Gauss linear;
    
    div(rhoPhi,U)                       Gauss linearUpwindV grad(U);
    div(phi,U)                          Gauss linearUpwindV grad(U);
    div(alphaRhoPhi,U)                  Gauss linearUpwindV grad(U);
    
    div(rhoPhi,T)                       Gauss linearUpwind limited;
    div(phi,T)                          Gauss linearUpwind limited;
    div(alphaRhoPhi,T)                  Gauss linearUpwind limited;
    div(alphaRhoPhi.metal,T)            Gauss linearUpwind limited;
    div(alphaRhoPhi.air,T)              Gauss linearUpwind limited;
    
    div(rhoPhi,K)                       Gauss linearUpwind limited;
    div(phi,K)                          Gauss linearUpwind limited;
    div(alphaRhoPhi,K)                  Gauss linearUpwind limited;
    
    div(rhoPhi,e)                       Gauss linearUpwind limited;
    div(phi,e)                          Gauss linearUpwind limited;
    div(alphaRhoPhi,e)                  Gauss linearUpwind limited;
    
    div(rhoPhi,h)                       Gauss linearUpwind limited;
    div(phi,h)                          Gauss linearUpwind limited;
    div(alphaRhoPhi,h)                  Gauss linearUpwind limited;
    div(alphaRhoPhi.metal,h.metal)      Gauss linearUpwind limited;
    div(alphaRhoPhi.air,h.air)          Gauss linearUpwind limited;
    
    div(phi,p)                          Gauss linearUpwind limited;
    
    div(((rho*nuEff)*dev2(T(grad(U))))) Gauss linear;
    div((nuEff*dev2(T(grad(U)))))       Gauss linear;
}}

laplacianSchemes
{{
    default         Gauss linear corrected;
}}

interpolationSchemes
{{
    default         linear;
}}

snGradSchemes
{{
    default         corrected;
}}

fluxRequired
{{
    default         no;
    p               ;
    alpha.metal     ;
}}

// ************************************************************************* //
""",

    "system/fvSolution": """/*--------------------------------*- C++ -*----------------------------------*\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  11                                    |
|   \\  /    A nd           | Website:  www.openfoam.org                      |
|    \\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      fvSolution;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

solvers
{{
    "alpha.metal.*"
    {{
        nAlphaCorr      2;
        nAlphaSubCycles 1;
        cAlpha          1;
    }}

    ".*(rho|rhoFinal)"
    {{
        solver          diagonal;
    }}

    pcorr
    {{
        solver          PCG;
        preconditioner  DIC;
        tolerance       1e-5;
        relTol          0;
    }}

    p_rgh
    {{
        solver          PCG;
        preconditioner  DIC;
        tolerance       1e-07;
        relTol          0.05;
    }}

    p_rghFinal
    {{
        $p_rgh;
        relTol          0;
    }}

    p
    {{
        solver          PCG;
        preconditioner  DIC;
        tolerance       1e-07;
        relTol          0.05;
    }}

    pFinal
    {{
        $p;
        relTol          0;
    }}

    U
    {{
        solver          PBiCGStab;
        preconditioner  DILU;
        tolerance       1e-06;
        relTol          0.1;
        maxIter         50;
    }}

    UFinal
    {{
        $U;
        relTol          0;
    }}

    "(T|e|h).*"
    {{
        solver          PBiCGStab;
        preconditioner  DILU;
        tolerance       1e-07;
        relTol          0.1;
        maxIter         50;
    }}

    TFinal
    {{
        $T;
        relTol          0;
    }}
}}

PIMPLE
{{
    // Enable momentum predictor for compressible flow
    momentumPredictor   yes;

    // Outer correctors for pressure-velocity-energy coupling
    // Increased to 5 for solidification with source terms
    nOuterCorrectors    5;

    // Pressure correctors per outer loop
    nCorrectors         3;

    // Non-orthogonal correctors (increase if mesh has issues)
    nNonOrthogonalCorrectors 1;

    // Energy correctors for temperature equation
    // 2 iterations handle latent heat source term coupling
    nEnergyCorrectors   2;

    // Tighter tolerances for thermal solidification
    outerCorrectorResidualControl
    {{
        p_rgh
        {{
            tolerance   1e-5;
            relTol      0;
        }}
        U
        {{
            tolerance   1e-5;
            relTol      0;
        }}
        "(e|h|T)"
        {{
            tolerance   1e-6;
            relTol      0;
        }}
    }}
}}

// Under-relaxation for solidification stability
// Stable source formulation allows more reasonable values
relaxationFactors
{{
    fields
    {{
        p_rgh           0.7;
        p               0.7;
    }}

    equations
    {{
        U               0.7;
        "(e|h|T)"       0.6;
        ".*"            0.7;
    }}
}}

// ************************************************************************* //
""",

    "constant/g": """/*--------------------------------*- C++ -*----------------------------------*\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  v2306                                 |
|   \\  /    A nd           | Website:  www.openfoam.com                      |
|    \\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       uniformDimensionedVectorField;
    location    "constant";
    object      g;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 1 -2 0 0 0 0];
value           (0 0 -9.81);

// ************************************************************************* //
""",

    "constant/momentumTransport": """/*--------------------------------*- C++ -*----------------------------------*\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  11                                    |
|   \\  /    A nd           | Website:  www.openfoam.org                      |
|    \\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "constant";
    object      momentumTransport;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

simulationType  laminar;

// ************************************************************************* //
""",

    "constant/phaseProperties": """/*--------------------------------*- C++ -*----------------------------------*\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  11                                    |
|   \\  /    A nd           | Website:  www.openfoam.org                      |
|    \\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "constant";
    object      phaseProperties;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

type    thermalPhaseChangeMultiphaseSystem;

phases  (metal gas);

metal
{{
    type            pureMovingPhaseModel;
}}

gas
{{
    type            pureMovingPhaseModel;
}}

sigma   0.07;

// ************************************************************************* //
""",

    "constant/physicalProperties.metal": """/*--------------------------------*- C++ -*----------------------------------*\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  11                                    |
|   \\  /    A nd           | Website:  www.openfoam.org                      |
|    \\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "constant";
    object      physicalProperties.metal;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

thermoType
{{
    type            heRhoThermo;
    mixture         pureMixture;
    transport       const;
    thermo          hConst;
    equationOfState rhoConst;
    specie          specie;
    energy          sensibleEnthalpy;
}}

mixture
{{
    specie
    {{
        molWeight   26.98;
    }}
    equationOfState
    {{
        rho         {metal_density};
    }}
    thermodynamics
    {{
        Cp          {metal_specific_heat};
        Hf          0;
    }}
    transport
    {{
        mu          {metal_viscosity};
        Pr          0.7;
    }}
}}

// ************************************************************************* //
""",

    "constant/physicalProperties.gas": """/*--------------------------------*- C++ -*----------------------------------*\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  11                                    |
|   \\  /    A nd           | Website:  www.openfoam.org                      |
|    \\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "constant";
    object      physicalProperties.gas;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

thermoType
{{
    type            heRhoThermo;
    mixture         pureMixture;
    transport       const;
    thermo          hConst;
    equationOfState perfectGas;
    specie          specie;
    energy          sensibleEnthalpy;
}}

mixture
{{
    specie
    {{
        molWeight   28.97;
    }}
    thermodynamics
    {{
        Cp          1005;
        Hf          0;
    }}
    transport
    {{
        mu          1.8e-05;
        Pr          0.7;
    }}
}}

// ************************************************************************* //
""",

    "0/alpha.metal": """/*--------------------------------*- C++ -*----------------------------------*\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  v2306                                 |
|   \\  /    A nd           | Website:  www.openfoam.com                      |
|    \\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    object      alpha.metal;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 0 0 0 0 0 0];

internalField   uniform 0;

boundaryField
{{
    walls
    {{
        type            zeroGradient;
    }}

    inlet
    {{
        type            fixedValue;
        value           uniform 1;
    }}

    outlet
    {{
        type            inletOutlet;
        inletValue      uniform 0;
        value           uniform 0;
    }}
}}

// ************************************************************************* //
""",

    "0/U": """/*--------------------------------*- C++ -*----------------------------------*\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  v2306                                 |
|   \\  /    A nd           | Website:  www.openfoam.com                      |
|    \\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volVectorField;
    object      U;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 1 -1 0 0 0 0];

internalField   uniform (0 0 0);

boundaryField
{{
    walls
    {{
        type            noSlip;
    }}

    inlet
    {{
        type            fixedValue;
        value           uniform (0 0 0.5);
    }}

    outlet
    {{
        type            pressureInletOutletVelocity;
        value           uniform (0 0 0);
    }}
}}

// ************************************************************************* //
""",

    "0/p_rgh": """/*--------------------------------*- C++ -*----------------------------------*\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  v2306                                 |
|   \\  /    A nd           | Website:  www.openfoam.com                      |
|    \\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    object      p_rgh;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [1 -1 -2 0 0 0 0];

internalField   uniform 0;

boundaryField
{{
    walls
    {{
        type            fixedFluxPressure;
        value           uniform 0;
    }}

    inlet
    {{
        type            fixedFluxPressure;
        value           uniform 0;
    }}

    outlet
    {{
        type            totalPressure;
        p0              uniform 0;
        value           uniform 0;
    }}
}}

// ************************************************************************* //
""",

    "0/p": """/*--------------------------------*- C++ -*----------------------------------*\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  11                                    |
|   \\  /    A nd           | Website:  www.openfoam.org                      |
|    \\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    object      p;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [1 -1 -2 0 0 0 0];

internalField   uniform 101325;

boundaryField
{{
    walls
    {{
        type            calculated;
        value           uniform 101325;
    }}

    inlet
    {{
        type            calculated;
        value           uniform 101325;
    }}

    outlet
    {{
        type            totalPressure;
        p0              uniform 101325;
        value           uniform 101325;
    }}
}}

// ************************************************************************* //
""",

    "0/T": """/*--------------------------------*- C++ -*----------------------------------*\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  v2306                                 |
|   \\  /    A nd           | Website:  www.openfoam.com                      |
|    \\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    object      T;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 0 0 1 0 0 0];

internalField   uniform {mold_temp};

boundaryField
{{
    walls
    {{
        type            fixedValue;
        value           uniform {mold_temp};
    }}

    inlet
    {{
        type            fixedValue;
        value           uniform {pouring_temp};
    }}

    outlet
    {{
        type            zeroGradient;
    }}
}}

// ************************************************************************* //
""",

    "system/fvOptions": """/*--------------------------------*- C++ -*----------------------------------*\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  11                                    |
|   \\  /    A nd           | Website:  www.openfoam.org                      |
|    \\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      fvOptions;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

solidificationHeat
{{
    type            coded;
    active          yes;
    name            solidificationSource;

    selectionMode   all;

    field           h;

    codeCorrect
    #{{
        // Do nothing
    #}};

    codeAddSup
    #{{
        const volScalarField& T = mesh().lookupObject<volScalarField>("T");
        const volScalarField& alpha = mesh().lookupObject<volScalarField>("alpha.metal");

        // Aluminum solidification properties
        const scalar Tsolidus = {solidus_temp};   // K
        const scalar Tliquidus = {liquidus_temp}; // K
        const scalar L = {latent_heat};           // J/kg
        const scalar rho = {metal_density};       // kg/m³

        scalarField& hSource = eqn.source();
        const scalarField& V = mesh().V();

        // Calculate liquid fraction
        scalarField fl = (T.primitiveField() - Tsolidus) / (Tliquidus - Tsolidus);
        fl = max(min(fl, 1.0), 0.0);

        // STABLE FORMULATION: Use characteristic solidification timescale
        // instead of 1/deltaT which causes instability
        // For aluminum die casting: typical solidification time ~1-10 seconds
        const scalar tau = 5.0;  // Characteristic solidification time [s]
        const scalar relax = 0.1;  // Under-relaxation factor for stability

        forAll(hSource, i)
        {{
            if (alpha[i] > 0.5)  // Only in metal phase
            {{
                if (T[i] < Tliquidus && T[i] > Tsolidus)
                {{
                    // In mushy zone - add latent heat source
                    // Source = rho * L * (solid_fraction) / tau * relax
                    // Negative sign because solidification RELEASES heat (exothermic)
                    scalar solidFraction = 1.0 - fl[i];
                    hSource[i] -= relax * rho * L * solidFraction * V[i] / tau;
                }}
            }}
        }}
    #}};

    codeSetValue
    #{{
        // Do nothing
    #}};
}}

mushyZoneDrag
{{
    type            coded;
    active          yes;
    name            mushyZoneSource;

    selectionMode   all;

    field           U;

    codeCorrect
    #{{
        // Do nothing
    #}};

    codeAddSup
    #{{
        const volScalarField& T = mesh().lookupObject<volScalarField>("T");
        const volScalarField& alpha = mesh().lookupObject<volScalarField>("alpha.metal");
        const volVectorField& U = mesh().lookupObject<volVectorField>("U");

        // Aluminum solidification properties
        const scalar Tsolidus = {solidus_temp};
        const scalar Tliquidus = {liquidus_temp};
        const scalar mu = {metal_viscosity};  // Pa·s
        const scalar K0 = 1e-7;     // Reference permeability m²
        const scalar Amush = 1e5;   // Mushy zone constant

        vectorField& USource = eqn.source();
        const scalarField& V = mesh().V();

        // Calculate liquid fraction
        scalarField fl = (T.primitiveField() - Tsolidus) / (Tliquidus - Tsolidus);
        fl = max(min(fl, 1.0), 0.0);

        forAll(USource, i)
        {{
            if (alpha[i] > 0.5)  // Only in metal phase
            {{
                if (fl[i] < 0.999)  // Not fully liquid
                {{
                    // Carman-Kozeny permeability model
                    scalar flCubed = fl[i] * fl[i] * fl[i];
                    scalar solidFrac = 1.0 - fl[i];
                    scalar K = K0 * flCubed / (solidFrac * solidFrac + 1e-6);

                    // Darcy drag: F = -mu/K * U
                    scalar drag = mu / (K + 1e-12);

                    // Add drag term (momentum sink)
                    USource[i] -= drag * U[i] * V[i];
                }}
            }}
        }}
    #}};

    codeSetValue
    #{{
        // Do nothing
    #}};
}}

// ************************************************************************* //
"""
}
