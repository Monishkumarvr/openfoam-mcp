"""MCP Server for OpenFOAM Foundry Simulations.

This server provides tools for AI agents to:
- Set up casting simulations
- Run mold filling analysis
- Perform solidification studies
- Predict casting defects
- Optimize gating systems
"""

import os
import sys
import asyncio
from typing import Any, Sequence
from pathlib import Path

from mcp.server import Server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from mcp.server.stdio import stdio_server

from loguru import logger

from .api.openfoam_client import OpenFOAMClient
from .api.case_manager import CaseManager
from .api.result_analyzer import ResultAnalyzer
from .builders.case_builder import CaseBuilder

# Configure logger
logger.remove()
logger.add(sys.stderr, level="INFO")

# Initialize server
app = Server("openfoam-mcp")

# Initialize managers
openfoam_client = OpenFOAMClient()
case_manager = CaseManager()
result_analyzer = ResultAnalyzer()


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available OpenFOAM foundry simulation tools."""
    return [
        Tool(
            name="create_casting_case",
            description="Create a new OpenFOAM case for casting simulation",
            inputSchema={
                "type": "object",
                "properties": {
                    "case_name": {
                        "type": "string",
                        "description": "Name for the simulation case"
                    },
                    "case_type": {
                        "type": "string",
                        "enum": ["mold_filling", "solidification", "continuous_casting", "die_casting"],
                        "description": "Type of casting simulation"
                    },
                    "metal_type": {
                        "type": "string",
                        "enum": ["steel", "aluminum", "iron", "copper", "bronze"],
                        "description": "Type of metal being cast"
                    },
                    "pouring_temperature": {
                        "type": "number",
                        "description": "Pouring temperature in Celsius"
                    },
                    "mold_material": {
                        "type": "string",
                        "enum": ["sand", "ceramic", "metal", "graphite"],
                        "description": "Mold material type",
                        "default": "sand"
                    }
                },
                "required": ["case_name", "case_type", "metal_type", "pouring_temperature"]
            }
        ),
        Tool(
            name="list_cases",
            description="List all OpenFOAM cases in the workspace",
            inputSchema={
                "type": "object",
                "properties": {
                    "filter_type": {
                        "type": "string",
                        "description": "Filter cases by type (optional)"
                    }
                }
            }
        ),
        Tool(
            name="setup_geometry",
            description="Set up geometry for casting simulation from STL file or parametric description",
            inputSchema={
                "type": "object",
                "properties": {
                    "case_name": {
                        "type": "string",
                        "description": "Name of the case to add geometry to"
                    },
                    "geometry_type": {
                        "type": "string",
                        "enum": ["stl_file", "blockMesh", "snappyHexMesh"],
                        "description": "Type of geometry input"
                    },
                    "stl_path": {
                        "type": "string",
                        "description": "Path to STL file (if geometry_type is stl_file)"
                    },
                    "dimensions": {
                        "type": "object",
                        "description": "Parametric dimensions for simple geometries (length, width, height in meters)",
                        "properties": {
                            "length": {"type": "number"},
                            "width": {"type": "number"},
                            "height": {"type": "number"}
                        }
                    },
                    "mesh_refinement": {
                        "type": "string",
                        "enum": ["coarse", "medium", "fine", "very_fine"],
                        "default": "medium",
                        "description": "Mesh refinement level"
                    }
                },
                "required": ["case_name", "geometry_type"]
            }
        ),
        Tool(
            name="setup_material_properties",
            description="Configure material properties for metal and mold",
            inputSchema={
                "type": "object",
                "properties": {
                    "case_name": {
                        "type": "string",
                        "description": "Name of the case"
                    },
                    "metal_properties": {
                        "type": "object",
                        "properties": {
                            "density": {"type": "number", "description": "Density in kg/m³"},
                            "viscosity": {"type": "number", "description": "Dynamic viscosity in Pa·s"},
                            "thermal_conductivity": {"type": "number", "description": "Thermal conductivity in W/(m·K)"},
                            "specific_heat": {"type": "number", "description": "Specific heat in J/(kg·K)"},
                            "liquidus_temp": {"type": "number", "description": "Liquidus temperature in K"},
                            "solidus_temp": {"type": "number", "description": "Solidus temperature in K"},
                            "latent_heat": {"type": "number", "description": "Latent heat of fusion in J/kg"}
                        }
                    },
                    "mold_properties": {
                        "type": "object",
                        "properties": {
                            "density": {"type": "number"},
                            "thermal_conductivity": {"type": "number"},
                            "specific_heat": {"type": "number"}
                        }
                    }
                },
                "required": ["case_name"]
            }
        ),
        Tool(
            name="setup_boundary_conditions",
            description="Configure boundary conditions for the simulation",
            inputSchema={
                "type": "object",
                "properties": {
                    "case_name": {
                        "type": "string",
                        "description": "Name of the case"
                    },
                    "inlet_velocity": {
                        "type": "number",
                        "description": "Inlet velocity in m/s (for mold filling)"
                    },
                    "inlet_temperature": {
                        "type": "number",
                        "description": "Inlet temperature in K"
                    },
                    "mold_wall_temperature": {
                        "type": "number",
                        "description": "Mold wall temperature in K"
                    },
                    "ambient_temperature": {
                        "type": "number",
                        "description": "Ambient temperature in K"
                    },
                    "heat_transfer_coefficient": {
                        "type": "number",
                        "description": "Heat transfer coefficient at mold-metal interface in W/(m²·K)"
                    }
                },
                "required": ["case_name"]
            }
        ),
        Tool(
            name="run_mesh_generation",
            description="Generate computational mesh for the case",
            inputSchema={
                "type": "object",
                "properties": {
                    "case_name": {
                        "type": "string",
                        "description": "Name of the case"
                    },
                    "parallel": {
                        "type": "boolean",
                        "default": False,
                        "description": "Run mesh generation in parallel"
                    },
                    "num_processors": {
                        "type": "integer",
                        "default": 4,
                        "description": "Number of processors for parallel execution"
                    }
                },
                "required": ["case_name"]
            }
        ),
        Tool(
            name="run_simulation",
            description="Run the OpenFOAM casting simulation",
            inputSchema={
                "type": "object",
                "properties": {
                    "case_name": {
                        "type": "string",
                        "description": "Name of the case to run"
                    },
                    "solver": {
                        "type": "string",
                        "enum": ["interFoam", "interPhaseChangeFoam", "compressibleInterFoam", "buoyantBoussinesqPimpleFoam"],
                        "default": "interFoam",
                        "description": "OpenFOAM solver to use"
                    },
                    "end_time": {
                        "type": "number",
                        "description": "Simulation end time in seconds"
                    },
                    "write_interval": {
                        "type": "number",
                        "description": "Time interval for writing results in seconds"
                    },
                    "parallel": {
                        "type": "boolean",
                        "default": False,
                        "description": "Run simulation in parallel"
                    },
                    "num_processors": {
                        "type": "integer",
                        "default": 4,
                        "description": "Number of processors for parallel execution"
                    }
                },
                "required": ["case_name"]
            }
        ),
        Tool(
            name="analyze_results",
            description="Analyze simulation results and predict casting defects",
            inputSchema={
                "type": "object",
                "properties": {
                    "case_name": {
                        "type": "string",
                        "description": "Name of the case to analyze"
                    },
                    "analysis_type": {
                        "type": "string",
                        "enum": ["filling_pattern", "temperature_distribution", "solidification_time", "defect_prediction", "all"],
                        "default": "all",
                        "description": "Type of analysis to perform"
                    },
                    "time_step": {
                        "type": "number",
                        "description": "Time step to analyze (if not specified, uses latest)"
                    }
                },
                "required": ["case_name"]
            }
        ),
        Tool(
            name="predict_defects",
            description="Predict casting defects based on simulation results",
            inputSchema={
                "type": "object",
                "properties": {
                    "case_name": {
                        "type": "string",
                        "description": "Name of the case"
                    },
                    "defect_types": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["porosity", "shrinkage", "hot_spots", "cold_shuts", "misruns"]
                        },
                        "description": "Types of defects to predict"
                    }
                },
                "required": ["case_name"]
            }
        ),
        Tool(
            name="export_results",
            description="Export simulation results in various formats",
            inputSchema={
                "type": "object",
                "properties": {
                    "case_name": {
                        "type": "string",
                        "description": "Name of the case"
                    },
                    "export_format": {
                        "type": "string",
                        "enum": ["vtk", "stl", "csv", "images"],
                        "description": "Export format"
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Output path for exported files"
                    }
                },
                "required": ["case_name", "export_format"]
            }
        ),
        Tool(
            name="get_case_status",
            description="Get the current status of a simulation case",
            inputSchema={
                "type": "object",
                "properties": {
                    "case_name": {
                        "type": "string",
                        "description": "Name of the case"
                    }
                },
                "required": ["case_name"]
            }
        ),
        Tool(
            name="optimize_gating_system",
            description="Run parametric study to optimize gate and riser positions",
            inputSchema={
                "type": "object",
                "properties": {
                    "case_name": {
                        "type": "string",
                        "description": "Base case name for optimization"
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Parameters to optimize",
                        "properties": {
                            "gate_positions": {
                                "type": "array",
                                "items": {"type": "object"}
                            },
                            "gate_sizes": {
                                "type": "array",
                                "items": {"type": "number"}
                            },
                            "riser_sizes": {
                                "type": "array",
                                "items": {"type": "number"}
                            }
                        }
                    },
                    "optimization_metric": {
                        "type": "string",
                        "enum": ["minimize_porosity", "minimize_fill_time", "uniform_solidification"],
                        "description": "Optimization objective"
                    }
                },
                "required": ["case_name", "optimization_metric"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    """Handle tool calls from AI agent."""

    try:
        if name == "create_casting_case":
            case_name = arguments["case_name"]
            case_type = arguments["case_type"]
            metal_type = arguments["metal_type"]
            pouring_temp = arguments["pouring_temperature"]
            mold_material = arguments.get("mold_material", "sand")

            logger.info(f"Creating casting case: {case_name} (type: {case_type})")

            result = await case_manager.create_case(
                case_name=case_name,
                case_type=case_type,
                metal_type=metal_type,
                pouring_temperature=pouring_temp,
                mold_material=mold_material
            )

            return [TextContent(
                type="text",
                text=f"✅ Created casting case: {case_name}\n"
                     f"Type: {case_type}\n"
                     f"Metal: {metal_type} at {pouring_temp}°C\n"
                     f"Mold: {mold_material}\n"
                     f"Location: {result['path']}\n\n"
                     f"Next steps:\n"
                     f"1. Use 'setup_geometry' to add geometry\n"
                     f"2. Use 'setup_material_properties' to configure materials\n"
                     f"3. Use 'setup_boundary_conditions' to set BCs\n"
                     f"4. Use 'run_mesh_generation' to create mesh\n"
                     f"5. Use 'run_simulation' to execute"
            )]

        elif name == "list_cases":
            filter_type = arguments.get("filter_type")

            cases = await case_manager.list_cases(filter_type=filter_type)

            if not cases:
                return [TextContent(type="text", text="No cases found.")]

            case_list = "\n".join([
                f"- {c['name']} ({c['type']}) - Status: {c['status']}"
                for c in cases
            ])

            return [TextContent(
                type="text",
                text=f"Found {len(cases)} case(s):\n{case_list}"
            )]

        elif name == "setup_geometry":
            case_name = arguments["case_name"]
            geometry_type = arguments["geometry_type"]

            logger.info(f"Setting up geometry for case: {case_name}")

            result = await case_manager.setup_geometry(
                case_name=case_name,
                geometry_type=geometry_type,
                stl_path=arguments.get("stl_path"),
                dimensions=arguments.get("dimensions"),
                mesh_refinement=arguments.get("mesh_refinement", "medium")
            )

            return [TextContent(
                type="text",
                text=f"✅ Geometry configured for {case_name}\n"
                     f"Type: {geometry_type}\n"
                     f"Mesh refinement: {arguments.get('mesh_refinement', 'medium')}\n"
                     f"Details: {result.get('details', 'N/A')}"
            )]

        elif name == "setup_material_properties":
            case_name = arguments["case_name"]

            result = await case_manager.setup_material_properties(
                case_name=case_name,
                metal_properties=arguments.get("metal_properties"),
                mold_properties=arguments.get("mold_properties")
            )

            return [TextContent(
                type="text",
                text=f"✅ Material properties configured for {case_name}\n"
                     f"Files updated: transportProperties, thermophysicalProperties"
            )]

        elif name == "setup_boundary_conditions":
            case_name = arguments["case_name"]

            result = await case_manager.setup_boundary_conditions(
                case_name=case_name,
                **{k: v for k, v in arguments.items() if k != "case_name"}
            )

            return [TextContent(
                type="text",
                text=f"✅ Boundary conditions configured for {case_name}\n"
                     f"Configured: velocity, pressure, temperature fields"
            )]

        elif name == "run_mesh_generation":
            case_name = arguments["case_name"]
            parallel = arguments.get("parallel", False)
            num_procs = arguments.get("num_processors", 4)

            logger.info(f"Running mesh generation for {case_name}")

            result = await openfoam_client.run_mesh_generation(
                case_name=case_name,
                parallel=parallel,
                num_processors=num_procs
            )

            return [TextContent(
                type="text",
                text=f"✅ Mesh generation completed for {case_name}\n"
                     f"Cells: {result.get('num_cells', 'N/A')}\n"
                     f"Points: {result.get('num_points', 'N/A')}\n"
                     f"Quality: {result.get('quality', 'N/A')}"
            )]

        elif name == "run_simulation":
            case_name = arguments["case_name"]
            solver = arguments.get("solver", "interFoam")
            parallel = arguments.get("parallel", False)

            logger.info(f"Running simulation for {case_name} with {solver}")

            result = await openfoam_client.run_simulation(
                case_name=case_name,
                solver=solver,
                end_time=arguments.get("end_time"),
                write_interval=arguments.get("write_interval"),
                parallel=parallel,
                num_processors=arguments.get("num_processors", 4)
            )

            return [TextContent(
                type="text",
                text=f"✅ Simulation completed for {case_name}\n"
                     f"Solver: {solver}\n"
                     f"Status: {result.get('status', 'completed')}\n"
                     f"Final time: {result.get('final_time', 'N/A')}s\n"
                     f"Output: {result.get('output_dir', 'N/A')}"
            )]

        elif name == "analyze_results":
            case_name = arguments["case_name"]
            analysis_type = arguments.get("analysis_type", "all")

            logger.info(f"Analyzing results for {case_name}")

            result = await result_analyzer.analyze(
                case_name=case_name,
                analysis_type=analysis_type,
                time_step=arguments.get("time_step")
            )

            analysis_text = f"📊 Analysis Results for {case_name}\n\n"

            if "filling_pattern" in result:
                analysis_text += f"Filling Pattern:\n{result['filling_pattern']}\n\n"

            if "temperature_distribution" in result:
                analysis_text += f"Temperature Distribution:\n{result['temperature_distribution']}\n\n"

            if "defects" in result:
                analysis_text += f"⚠️ Potential Defects:\n{result['defects']}\n\n"

            return [TextContent(type="text", text=analysis_text)]

        elif name == "predict_defects":
            case_name = arguments["case_name"]
            defect_types = arguments.get("defect_types", ["porosity", "shrinkage"])

            result = await result_analyzer.predict_defects(
                case_name=case_name,
                defect_types=defect_types
            )

            defect_text = f"🔍 Defect Prediction for {case_name}\n\n"
            for defect_type, prediction in result.items():
                defect_text += f"{defect_type.upper()}: {prediction}\n"

            return [TextContent(type="text", text=defect_text)]

        elif name == "export_results":
            case_name = arguments["case_name"]
            export_format = arguments["export_format"]
            output_path = arguments.get("output_path", f"./{case_name}_export")

            result = await openfoam_client.export_results(
                case_name=case_name,
                export_format=export_format,
                output_path=output_path
            )

            return [TextContent(
                type="text",
                text=f"✅ Results exported for {case_name}\n"
                     f"Format: {export_format}\n"
                     f"Location: {result['output_path']}"
            )]

        elif name == "get_case_status":
            case_name = arguments["case_name"]

            status = await case_manager.get_case_status(case_name)

            return [TextContent(
                type="text",
                text=f"Status for {case_name}:\n"
                     f"State: {status['state']}\n"
                     f"Progress: {status['progress']}%\n"
                     f"Last updated: {status['last_updated']}"
            )]

        elif name == "optimize_gating_system":
            case_name = arguments["case_name"]
            optimization_metric = arguments["optimization_metric"]

            logger.info(f"Starting optimization for {case_name}")

            result = await case_manager.optimize_gating(
                case_name=case_name,
                parameters=arguments.get("parameters", {}),
                metric=optimization_metric
            )

            return [TextContent(
                type="text",
                text=f"🎯 Optimization Results for {case_name}\n\n"
                     f"Objective: {optimization_metric}\n"
                     f"Best configuration: {result['best_config']}\n"
                     f"Improvement: {result['improvement']}%\n"
                     f"Iterations: {result['iterations']}"
            )]

        else:
            return [TextContent(
                type="text",
                text=f"❌ Unknown tool: {name}"
            )]

    except Exception as e:
        logger.error(f"Error executing tool {name}: {str(e)}")
        return [TextContent(
            type="text",
            text=f"❌ Error executing {name}: {str(e)}"
        )]


async def main():
    """Run the MCP server."""
    logger.info("Starting OpenFOAM MCP Server for Foundry Simulations")

    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
