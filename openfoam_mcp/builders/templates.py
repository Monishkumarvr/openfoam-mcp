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

deltaT          0.001;

writeControl    adjustableRunTime;

writeInterval   5;

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
        solver          smoothSolver;
        smoother        symGaussSeidel;
        tolerance       1e-06;
        relTol          0;
    }}

    UFinal
    {{
        $U;
        relTol          0;
    }}

    "(T|e|h).*"
    {{
        solver          smoothSolver;
        smoother        symGaussSeidel;
        tolerance       1e-07;
        relTol          0;
    }}

    TFinal
    {{
        $T;
        relTol          0;
    }}
}}

PIMPLE
{{
    momentumPredictor   yes;
    nOuterCorrectors    1;
    nCorrectors         3;
    nNonOrthogonalCorrectors 0;
}}

relaxationFactors
{{
    equations
    {{
        ".*"            1;
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
        Cp          {metal_cp};
        Hf          0;
        Tref        300;
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
        Cp          1007;
        Hf          0;
        Tref        300;
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

internalField   uniform {ambient_temp};

boundaryField
{{
    walls
    {{
        type            fixedValue;
        value           uniform {ambient_temp};
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
"""
}
