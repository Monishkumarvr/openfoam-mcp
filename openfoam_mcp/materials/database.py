"""Materials database for steel and cast iron casting simulation.

IMPORTANT -- READ BEFORE USING THESE VALUES FOR ANYTHING CONSEQUENTIAL:

Every entry here is a NOMINAL, TYPICAL value for the grade, compiled from
general metallurgical/foundry references (ASM Metals Handbook Vol. 1 & 15,
common foundry engineering references, and the specific sources noted
per-entry where a value was checked directly). These are NOT certified,
heat-specific, or lab-measured properties. Real alloys vary by supplier,
melt chemistry, and heat treatment; liquidus/solidus in particular can
shift by tens of degrees between heats of the "same" grade. Anywhere this
data drives a real casting/tooling decision, verify against your actual
material certification or measure it directly.

Units (SI, matching what CaseBuilder/templates.py already expect):
    density              kg/m^3
    liquidus_temp        K
    solidus_temp         K
    latent_heat          J/kg
    specific_heat        J/(kg*K)   -- representative average, not a function of T
    thermal_conductivity W/(m*K)
    viscosity            Pa*s (dynamic, of the molten metal)
    niyama_threshold_mm  (K*s)^0.5 / mm -- below this, porosity risk (see
                          result_analyzer_real.py's Niyama predictor)

niyama_threshold_mm values are much less certain than the thermophysical
properties above: published thresholds vary by alloy, section size, and
which authors' correlation you use. Cast irons in particular partially
self-feed shrinkage via graphite expansion during eutectic solidification,
which is why their thresholds sit lower than steel's -- but this is a
family-level approximation the same way the interim table in
result_analyzer_real.py was, not a rigorously derived number per grade.
"""

from typing import Any, Dict, Optional

# ---------------------------------------------------------------------------
# Cast / carbon / alloy / stainless / tool steels
# ---------------------------------------------------------------------------

STEELS: Dict[str, Dict[str, Any]] = {
    "WCB": {
        "display_name": "ASTM A216 Grade WCB (cast carbon steel)",
        "density": 7850,
        "solidus_temp": 1683,      # 1410 C
        "liquidus_temp": 1723,     # 1450 C
        "latent_heat": 270000,
        "specific_heat": 460,
        "thermal_conductivity": 30,
        "viscosity": 0.0055,
        "niyama_threshold_mm": 2.0,
        "source": "Solidus/liquidus checked directly (makeitfrom.com, ASTM A216 WCB); "
                  "Cp/k/latent_heat/viscosity are typical carbon-steel handbook values.",
    },
    "WCC": {
        "display_name": "ASTM A216 Grade WCC (higher-Mn cast carbon steel)",
        "density": 7850,
        "solidus_temp": 1678,
        "liquidus_temp": 1718,
        "latent_heat": 270000,
        "specific_heat": 460,
        "thermal_conductivity": 29,
        "viscosity": 0.0055,
        "niyama_threshold_mm": 2.0,
        "source": "Nominal, close to WCB with slightly lower solidus/liquidus from higher Mn content.",
    },
    "1020": {
        "display_name": "AISI 1020 (low-carbon steel, ~0.2% C)",
        "density": 7870,
        "solidus_temp": 1755,
        "liquidus_temp": 1795,
        "latent_heat": 272000,
        "specific_heat": 470,
        "thermal_conductivity": 51,
        "viscosity": 0.0055,
        "niyama_threshold_mm": 2.2,
        "source": "Typical low-carbon-steel handbook values; k is notably higher than "
                  "alloy/stainless grades because low-carbon steel conducts heat well.",
    },
    "1045": {
        "display_name": "AISI 1045 (medium-carbon steel, ~0.45% C)",
        "density": 7850,
        "solidus_temp": 1690,
        "liquidus_temp": 1750,
        "latent_heat": 270000,
        "specific_heat": 460,
        "thermal_conductivity": 40,
        "viscosity": 0.0055,
        "niyama_threshold_mm": 2.0,
        "source": "Typical medium-carbon-steel handbook values.",
    },
    "4130": {
        "display_name": "AISI 4130 (Cr-Mo low-alloy steel)",
        "density": 7850,
        "solidus_temp": 1700,
        "liquidus_temp": 1760,
        "latent_heat": 265000,
        "specific_heat": 460,
        "thermal_conductivity": 32,
        "viscosity": 0.0058,
        "niyama_threshold_mm": 1.9,
        "source": "Typical Cr-Mo low-alloy-steel handbook values.",
    },
    "304": {
        "display_name": "304 austenitic stainless steel",
        "density": 7900,
        "solidus_temp": 1673,      # ~1400 C
        "liquidus_temp": 1723,     # ~1450 C
        "latent_heat": 260000,
        "specific_heat": 500,
        "thermal_conductivity": 16.2,
        "viscosity": 0.006,
        "niyama_threshold_mm": 1.5,
        "source": "Melting range checked directly (multiple sources, ~1400-1450 C); "
                  "k=16.2 W/mK at room temp is the well-established austenitic-stainless "
                  "value, roughly a third of plain carbon steel's -- this is the single "
                  "most important number distinguishing stainless thermal behavior.",
    },
    "316": {
        "display_name": "316 austenitic stainless steel (Mo-bearing)",
        "density": 7990,
        "solidus_temp": 1648,      # ~1375 C
        "liquidus_temp": 1673,     # ~1400 C
        "latent_heat": 260000,
        "specific_heat": 500,
        "thermal_conductivity": 16.3,
        "viscosity": 0.0065,
        "niyama_threshold_mm": 1.5,
        "source": "Solidus/liquidus checked directly (~1375-1400 C, multiple sources); "
                  "slightly lower melting range than 304 from higher Mo content.",
    },
    "CF8M": {
        "display_name": "CF8M (cast equivalent of 316 stainless)",
        "density": 7750,
        "solidus_temp": 1670,
        "liquidus_temp": 1700,
        "latent_heat": 260000,
        "specific_heat": 500,
        "thermal_conductivity": 14.5,
        "viscosity": 0.0065,
        "niyama_threshold_mm": 1.5,
        "source": "Nominal, close to wrought 316 (common investment-casting grade).",
    },
    "duplex_2205": {
        "display_name": "2205 duplex stainless steel",
        "density": 7800,
        "solidus_temp": 1690,
        "liquidus_temp": 1730,
        "latent_heat": 270000,
        "specific_heat": 480,
        "thermal_conductivity": 19,
        "viscosity": 0.0065,
        "niyama_threshold_mm": 1.7,
        "source": "Typical duplex-stainless handbook values; k intermediate between "
                  "austenitic stainless and carbon steel from the ferritic phase fraction.",
    },
    "H13": {
        "display_name": "H13 (Cr-Mo-V hot-work tool steel)",
        "density": 7800,
        "solidus_temp": 1700,      # ~1427 C onset
        "liquidus_temp": 1730,
        "latent_heat": 260000,
        "specific_heat": 460,
        "thermal_conductivity": 24.3,
        "viscosity": 0.0065,
        "niyama_threshold_mm": 1.8,
        "source": "Melting onset checked directly (~1427 C); liquidus/other properties nominal.",
    },
}

# ---------------------------------------------------------------------------
# Cast irons (gray, ductile/nodular, compacted graphite, malleable, white)
# ---------------------------------------------------------------------------

CAST_IRONS: Dict[str, Dict[str, Any]] = {
    "gray_iron_class20": {
        "display_name": "ASTM A48 Class 20 gray iron",
        "density": 7150,
        "solidus_temp": 1423,      # ~1150 C
        "liquidus_temp": 1523,     # ~1250 C
        "latent_heat": 240000,
        "specific_heat": 460,
        "thermal_conductivity": 46,
        "viscosity": 0.004,
        "niyama_threshold_mm": 1.0,
        "source": "k=46 W/mK checked directly (graphite-flake gray iron, well above "
                  "steel-adjacent alloys). Lower Niyama threshold vs. steel reflects "
                  "graphite-expansion self-feeding during eutectic solidification "
                  "(family-level approximation, not derived for this specific class).",
    },
    "gray_iron_class30": {
        "display_name": "ASTM A48 Class 30 gray iron",
        "density": 7200,
        "solidus_temp": 1408,
        "liquidus_temp": 1478,
        "latent_heat": 230000,
        "specific_heat": 460,
        "thermal_conductivity": 48,
        "viscosity": 0.0042,
        "niyama_threshold_mm": 1.0,
        "source": "Nominal, consistent with Class 20 (higher-strength grades trend to "
                  "slightly finer graphite structure and marginally higher k).",
    },
    "gray_iron_class40": {
        "display_name": "ASTM A48 Class 40 gray iron",
        "density": 7250,
        "solidus_temp": 1398,
        "liquidus_temp": 1458,
        "latent_heat": 220000,
        "specific_heat": 460,
        "thermal_conductivity": 50,
        "viscosity": 0.0045,
        "niyama_threshold_mm": 1.1,
        "source": "Nominal, following the Class 20/30 trend.",
    },
    "ductile_iron_60-40-18": {
        "display_name": "ASTM A536 60-40-18 ductile (nodular) iron, ferritic",
        "density": 7100,
        "solidus_temp": 1418,
        "liquidus_temp": 1428,
        "latent_heat": 260000,
        "specific_heat": 460,
        "thermal_conductivity": 36,
        "viscosity": 0.004,
        "niyama_threshold_mm": 1.2,
        "source": "k=36 W/mK checked directly. Narrower solidification range than gray "
                  "iron reflects ductile iron's near-eutectic composition; latent heat "
                  "higher than gray iron's from the nodular-graphite eutectic reaction.",
    },
    "ductile_iron_80-55-06": {
        "display_name": "ASTM A536 80-55-06 ductile iron, ferritic-pearlitic",
        "density": 7100,
        "solidus_temp": 1408,
        "liquidus_temp": 1418,
        "latent_heat": 255000,
        "specific_heat": 460,
        "thermal_conductivity": 32,
        "viscosity": 0.0042,
        "niyama_threshold_mm": 1.2,
        "source": "Nominal, following the 60-40-18 trend with lower k from increased "
                  "pearlite fraction.",
    },
    "ductile_iron_100-70-03": {
        "display_name": "ASTM A536 100-70-03 ductile iron, pearlitic",
        "density": 7150,
        "solidus_temp": 1398,
        "liquidus_temp": 1408,
        "latent_heat": 250000,
        "specific_heat": 460,
        "thermal_conductivity": 28,
        "viscosity": 0.0045,
        "niyama_threshold_mm": 1.3,
        "source": "Nominal, fully pearlitic matrix further reduces k vs. 80-55-06.",
    },
    "CGI": {
        "display_name": "Compacted graphite iron (CGI)",
        "density": 7100,
        "solidus_temp": 1408,
        "liquidus_temp": 1428,
        "latent_heat": 245000,
        "specific_heat": 460,
        "thermal_conductivity": 38,
        "viscosity": 0.0042,
        "niyama_threshold_mm": 1.1,
        "source": "Nominal; properties intentionally between gray and ductile iron, "
                  "matching CGI's vermicular (worm-shaped) graphite morphology.",
    },
    "malleable_iron": {
        "display_name": "Malleable iron (as-cast white iron, pre-anneal)",
        "density": 7300,
        "solidus_temp": 1423,
        "liquidus_temp": 1523,
        "latent_heat": 230000,
        "specific_heat": 460,
        "thermal_conductivity": 30,
        "viscosity": 0.0045,
        "niyama_threshold_mm": 1.3,
        "source": "Nominal. Properties are for the as-cast carbidic structure -- "
                  "malleabilizing heat treatment (not modeled here) changes the graphite "
                  "morphology and mechanical properties afterward, not the casting-stage physics.",
    },
    "white_iron": {
        "display_name": "White (chilled) iron",
        "density": 7700,
        "solidus_temp": 1423,
        "liquidus_temp": 1523,
        "latent_heat": 220000,
        "specific_heat": 460,
        "thermal_conductivity": 20,
        "viscosity": 0.005,
        "niyama_threshold_mm": 1.5,
        "source": "Nominal. Carbide (cementite) rather than graphite microstructure "
                  "gives white iron notably lower k than the graphitic irons above.",
    },
}

MATERIALS: Dict[str, Dict[str, Any]] = {**STEELS, **CAST_IRONS}


def get_material(grade: str) -> Dict[str, Any]:
    """Look up a material by grade name (case-insensitive, - and _ interchangeable).

    Raises KeyError with the list of known grades if not found -- callers
    should not silently fall back to a default alloy for a typo'd grade
    name, since that would run a simulation under the wrong material
    without any indication.
    """
    key = grade.strip()
    if key in MATERIALS:
        return MATERIALS[key]

    normalized = key.lower().replace("-", "_")
    for name, props in MATERIALS.items():
        if name.lower().replace("-", "_") == normalized:
            return props

    raise KeyError(
        f"Unknown material grade '{grade}'. Known grades: {', '.join(sorted(MATERIALS))}"
    )


def list_grades(category: Optional[str] = None) -> Dict[str, str]:
    """Return {grade_key: display_name} for all grades, or one category
    ('steel' or 'cast_iron')."""
    if category == "steel":
        source = STEELS
    elif category == "cast_iron":
        source = CAST_IRONS
    elif category is None:
        source = MATERIALS
    else:
        raise ValueError("category must be 'steel', 'cast_iron', or None")
    return {k: v["display_name"] for k, v in source.items()}
