import asyncio
import contextlib
import io
import logging
import os
import time
os.environ["SUMO_HOME"] = "D:\Program Files\SUMO"
import subprocess
from typing import Any, Dict, List, Tuple

import httpx
import osmnx as ox
from fastmcp import FastMCP, Context, Image
from tools.separate_light import separate_traffic_lights

# ────────────────────────────────────────────────────────────────────────────────
# Initialize FastMCP
# ────────────────────────────────────────────────────────────────────────────────
ox.settings.log_console = False
mcp = FastMCP(name = "sumo_simulation")

OVERPASS_API = "https://overpass.osm.jp/api/interpreter"

# ────────────────────────────────────────────────────────────────────────────────
# Helper: Safely run external commands
# ────────────────────────────────────────────────────────────────────────────────
def run_command(cmd: List[str], timeout: int = None) -> Tuple[bool, str]:
    try:
        completed = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
            timeout=timeout,
            shell=True
        )
        return completed.returncode == 0, completed.stdout
    except Exception as e:
        return False, str(e)

@mcp.prompt()
def get_sumo_simulation_guidance() -> str:
    """
    Get SUMO simulation prompt template
    
    Returns:
        Prompt template string
    """
    template = """
The user wants to perform SUMO simulation. Please ask the user to provide the following information:
1. Road network name
2. Traffic flow CSV file path
3. Signal control scheme CSV file path


Please help me complete the SUMO simulation task according to the following process:
1. Download the OSM road network for the specified area based on user requirements
2. Convert the OSM road network to a SUMO road network
3. Generate traffic flow according to user requirements
4. Generate simulation configuration files using four signal control methods: fixed timing, actuated control, Webster optimized timing, and green wave optimized timing, run simulations, and obtain evaluation metrics
5. Analyze and compare simulation results, generate simulation reports

"""
    return template

# ────────────────────────────────────────────────────────────────────────────────
# TOOL 2: Download OSM by place name
# ────────────────────────────────────────────────────────────────────────────────
@mcp.tool()
async def osm_download_by_place(
    place_name: str,
    simulation_name: str = "sim1",
    proxy: str = "http://127.0.0.1:50563",
    ctx: Context = None,
) -> Dict[str, Any]:
    """Download OSM data by place name and save to simulation directory.
    
    Args:
        place_name: Place name, e.g. "West District, Beijing, China"
        simulation_name: Simulation name, used as subfolder name
        proxy: Proxy server address
        ctx: Context object for logging
    """
    name = place_name.strip()
    if not name:
        if ctx:
            ctx.error("Error: Place name cannot be empty")
        return {"success": False, "message": "Error: Place name cannot be empty"}
    if name.startswith("`") or name.startswith("{"):
        if ctx:
            ctx.error("Error: Invalid place name parameter")
        return {"success": False, "message": "Error: Invalid place name parameter"}

    # Create basic directory structure
    base_dir = os.path.join("data", "simulation")
    sim_dir = os.path.join(base_dir, simulation_name)
    
    # Ensure directory exists
    os.makedirs(sim_dir, exist_ok=True)
    
    # Create filename with area name and date
    sanitized_name = place_name.replace(",", "_").replace(" ", "_").replace("/", "_")
    date_str = time.strftime("%Y%m%d")
    output_file = os.path.join(sim_dir, f"{sanitized_name}_{date_str}.osm")
    
    if ctx:
        ctx.info(f"--- Starting OSM Data Download ---")
        ctx.info(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        ctx.info(f"Place: {place_name}")
        ctx.info(f"Output file: {output_file}")

    # # Set proxy
    orig_http = None
    # orig_http, orig_https = os.environ.get("HTTP_PROXY"), os.environ.get("HTTPS_PROXY")
    # os.environ["HTTP_PROXY"], os.environ["HTTPS_PROXY"] = proxy, proxy
    try:
        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            def _dl() -> Tuple[str, int, int, int]:
                if ctx:
                    ctx.info(f"Downloading map data using OSMnx...")
                
                # Download map data using OSMnx
                G = ox.graph_from_place(name, network_type='drive', custom_filter='["highway"~"motorway|trunk|primary|secondary|tertiary"]', simplify=False, retain_all=False)
                
                if ctx:
                    ctx.info(f"Download complete, saving to OSM format...")
                    ctx.info(f"Number of nodes: {len(G.nodes)}")
                    ctx.info(f"Number of edges: {len(G.edges)}")
                
                # Save as OSM file
                ox.save_graph_xml(G, filepath=output_file)
                size = os.path.getsize(output_file)
                
                if ctx:
                    ctx.info(f"Saved as OSM file, size: {size} bytes")
                
                return os.path.abspath(output_file), size, len(G.nodes), len(G.edges)
            
            # Execute download operation asynchronously
            filepath, size, nn, ne = await asyncio.to_thread(_dl)
        
        # Capture standard output
        stdout_content = stdout.getvalue()
        if stdout_content and ctx:
            ctx.debug("Standard output:")
            ctx.debug(stdout_content)
        
        # Log success information
        if ctx:
            ctx.info("--- Download successful ---")
            ctx.info(f"File path: {filepath}")
            ctx.info(f"File size: {size} bytes")
            ctx.info(f"Number of nodes: {nn}")
            ctx.info(f"Number of edges: {ne}")
            ctx.info(f"Completion time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        return {
            "success": True, 
            "message": "OSM download successful", 
            "data": {
                "simulation_dir": os.path.abspath(sim_dir),
                "osm_file": filepath, 
                "file_size": size, 
                "num_nodes": nn, 
                "num_edges": ne
            }
        }
    except Exception as e:
        # Log error information
        if ctx:
            ctx.error(f"Error: {str(e)}")
            import traceback
            ctx.error(traceback.format_exc())
        
        return {"success": False, "message": f"OSM download failed: {e}"}
    finally:
        # Restore proxy settings
        if orig_http is not None:
            os.environ["HTTP_PROXY"] = orig_http
        else:
            os.environ.pop("HTTP_PROXY", None)

# ────────────────────────────────────────────────────────────────────────────────
# TOOL 3: Convert to SUMO network
# ────────────────────────────────────────────────────────────────────────────────
@mcp.tool()
async def convert_osm_to_sumo(
    osm_file: str,
    simulation_name: str = "sim1",
    netconvert_options: str = "",
    ctx: Context = None,
) -> Dict[str, Any]:
    """Convert OSM file to SUMO .net.xml and save to simulation directory.
    
    Args:
        osm_file: OSM file path
        simulation_name: Simulation name, used as subfolder name
        netconvert_options: Additional netconvert options
        ctx: Context object for logging
    """
    # Create basic directory structure
    base_dir = os.path.join("data", "simulation")
    sim_dir = os.path.join(base_dir, simulation_name)
    
    # Ensure directory exists
    os.makedirs(sim_dir, exist_ok=True)
    
    # If OSM file is not in simulation directory, copy to simulation directory
    osm_basename = os.path.basename(osm_file)
    sim_osm_file = os.path.join(sim_dir, osm_basename)
    
    if os.path.abspath(osm_file) != os.path.abspath(sim_osm_file):
        try:
            import shutil
            shutil.copy2(osm_file, sim_osm_file)
        except Exception as e:
            if ctx:
                ctx.error(f"Failed to copy OSM file: {e}")
            return {"success": False, "message": f"Failed to copy OSM file: {e}"}
    
    # Use OSM file in simulation directory
    osm_file = sim_osm_file
    
    # Set output file path
    output_prefix = os.path.join(sim_dir, f"{simulation_name}_net")
    net_file = f"{output_prefix}.net.xml"
    
    # Check if typemap file exists
    typemap = "typemap.xml"
    if os.path.exists(typemap):
        # Copy typemap to simulation directory
        sim_typemap = os.path.join(sim_dir, typemap)
        try:
            import shutil
            shutil.copy2(typemap, sim_typemap)
            typemap = sim_typemap
        except Exception:
            # If copy fails, use original file
            if ctx:
                ctx.warning("Failed to copy typemap file, will use original file")
            pass
    
    # Log conversion process
    if ctx:
        ctx.info(f"--- Starting OSM to SUMO network conversion ---")
        ctx.info(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        ctx.info(f"OSM file: {osm_file}")
        ctx.info(f"Output file: {net_file}")
    
    # Build netconvert command
    cmd = [
        "netconvert", "--osm", osm_file, "--output", net_file,
        "--geometry.remove", "--roundabouts.guess", "--ramps.guess",
        "--junctions.join", "--tls.guess-signals", "--tls.discard-simple",
        "--tls.join", "--output.street-names"
    ]
    
    if os.path.exists(typemap): 
        cmd += ["--type-files", typemap]
    
    if netconvert_options: 
        cmd += netconvert_options.split()
    
    # Log command
    if ctx:
        ctx.info(f"Executing command: {' '.join(cmd)}")
    
    # Execute command
    ok, out = run_command(cmd)
    
    # Log output
    if ctx:
        ctx.debug("Command output:")
        ctx.debug(out)
    
    if ok:
        # Log success information
        if ctx:
            ctx.info("--- Conversion successful ---")
            ctx.info(f"Network file: {os.path.abspath(net_file)}")
            ctx.info(f"Completion time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Extract traffic signal timing plan
        tls_file = None
        try:
            tls_file = os.path.join(sim_dir, f"{simulation_name}_tls.add.xml")
            if ctx:
                ctx.info(f"Extracting traffic signal timing plan...")
            
            separate_traffic_lights(net_file, tls_file, program_id='fixed')
            
            if os.path.exists(tls_file) and os.path.getsize(tls_file) > 0:
                if ctx:
                    ctx.info(f"Traffic signal timing plan extracted to: {tls_file}")
            else:
                if ctx:
                    ctx.warning(f"No traffic signals found or extraction failed")
                tls_file = None
        except Exception as e:
            if ctx:
                ctx.warning(f"Failed to extract traffic signals: {str(e)}")
            tls_file = None
        
        return {
            "success": True, 
            "message": "Conversion successful", 
            "data": {
                "simulation_dir": os.path.abspath(sim_dir),
                "net_file": os.path.abspath(net_file),
                "tls_file": os.path.abspath(tls_file) if tls_file else None
            }
        }
    else:
        # Log failure information
        if ctx:
            ctx.error("--- Conversion failed ---")
            ctx.error(f"Error message: {out}")
            ctx.error(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        return {
            "success": False, 
            "message": f"Conversion failed", 
            "data": {
                "error": out
            }
        }

# ────────────────────────────────────────────────────────────────────────────────
# TOOL 4: Generate random trips and routes
# ────────────────────────────────────────────────────────────────────────────────
@mcp.tool()
async def generate_random_trips(
    net_file: str,
    simulation_name: str = "sim1",
    num_trips: int = 100,
    begin_time: int = 0,
    end_time: int = 3600,
    ctx: Context = None,
) -> Dict[str, Any]:
    """Generate trips and routes using randomTrips.py and duarouter, and organize into specified folder structure.
    
    Args:
        net_file: Network file path
        simulation_name: Simulation name, used as subfolder name
        num_trips: Number of trips to generate
        begin_time: Start time (seconds)
        end_time: End time (seconds)
        ctx: Context object for logging
    """
    if not os.path.exists(net_file):
        if ctx:
            ctx.error(f"Network file does not exist: {net_file}")
        return {"success": False, "message": f"Network file does not exist: {net_file}"}
    
    # Create basic directory structure
    base_dir = os.path.join("data", "simulation")
    sim_dir = os.path.join(base_dir, simulation_name)
    
    # Ensure directory exists
    os.makedirs(sim_dir, exist_ok=True)
    
    # If network file is not in simulation directory, copy to simulation directory
    net_basename = os.path.basename(net_file)
    sim_net_file = os.path.join(sim_dir, net_basename)
    
    if os.path.abspath(net_file) != os.path.abspath(sim_net_file):
        try:
            import shutil
            shutil.copy2(net_file, sim_net_file)
        except Exception as e:
            if ctx:
                ctx.error(f"Failed to copy network file: {e}")
            return {"success": False, "message": f"Failed to copy network file: {e}"}
    
    # Use network file in simulation directory
    net_file = sim_net_file
    
    # Set output file path
    output_prefix = os.path.join(sim_dir, simulation_name)
    trips_file = f"{output_prefix}.trips.xml"
    rou_file = f"{output_prefix}.rou.xml"
    
    # Find randomTrips.py script
    script = os.path.join(os.environ.get("SUMO_HOME", ""), "tools", "randomTrips.py")
    if not os.path.exists(script):
        alt_script = os.path.join(os.path.dirname(__file__), "tools", "randomTrips.py")
        if os.path.exists(alt_script):
            script = alt_script
        else:
            if ctx:
                ctx.error(f"Script not found: randomTrips.py")
            return {"success": False, "message": f"Script not found: randomTrips.py"}
    
    try:
        # Log process
        if ctx:
            ctx.info(f"--- Starting random trip generation {simulation_name} ---")
            ctx.info(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            ctx.info(f"Network file: {net_file}")
            ctx.info(f"Number of trips: {num_trips}")
            ctx.info(f"Start time: {begin_time} seconds")
            ctx.info(f"End time: {end_time} seconds")
        
        # Build randomTrips command
        cmd1 = [
            "python", script, "-n", net_file, "-o", trips_file,
            "-p", str((end_time - begin_time) / num_trips), "-b", str(begin_time), "-e", str(end_time)
        ]
        
        # Log command
        if ctx:
            ctx.info(f"Executing command: {' '.join(cmd1)}")
        
        # Execute randomTrips command
        process = subprocess.run(
            cmd1,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
            timeout=300,  # 5 minutes timeout
            shell=True
        )
        
        # Log output
        if ctx:
            ctx.debug(f"Command return code: {process.returncode}")
            ctx.debug("Command output:")
            ctx.debug(process.stdout)
        
        if process.returncode != 0:
            if ctx:
                ctx.error("randomTrips.py execution failed")
            return {
                "success": False, 
                "message": f"randomTrips.py execution failed, see log for details"
            }
        
        if not os.path.exists(trips_file):
            if ctx:
                ctx.error("Trip file not generated")
            return {
                "success": False, 
                "message": f"Trip file not generated"
            }
        
        # Build duarouter command
        cmd2 = [
            "duarouter", "--route-files", trips_file, "--net-file", net_file,
            "--output-file", rou_file, "--ignore-errors", "true"
        ]
        
        # Log command
        if ctx:
            ctx.info(f"Executing command: {' '.join(cmd2)}")
        
        # Execute duarouter command
        process2 = subprocess.run(
            cmd2,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
            timeout=300,
            shell=True
        )
        
        # Log output
        if ctx:
            ctx.debug(f"Command return code: {process2.returncode}")
            ctx.debug("Command output:")
            ctx.debug(process2.stdout)
        
        if process2.returncode != 0:
            if ctx:
                ctx.error("duarouter execution failed")
            return {
                "success": False, 
                "message": f"duarouter execution failed, see log for details"
            }
        
        if not os.path.exists(rou_file):
            if ctx:
                ctx.error("Route file not generated")
            return {
                "success": False, 
                "message": f"Route file not generated"
            }
        
        # Log success information
        if ctx:
            ctx.info("--- Random trip generation successful ---")
            ctx.info(f"Trip file: {os.path.abspath(trips_file)}")
            ctx.info(f"Route file: {os.path.abspath(rou_file)}")
            ctx.info(f"Completion time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        return {
            "success": True, 
            "message": "Generation successful", 
            "data": {
                "simulation_dir": os.path.abspath(sim_dir),
                "trips_file": os.path.abspath(trips_file), 
                "route_file": os.path.abspath(rou_file)
            }
        }
    except subprocess.TimeoutExpired as e:
        if ctx:
            ctx.error(f"Error: Command execution timed out ({e})")
        return {
            "success": False, 
            "message": f"Command execution timed out"
        }
    except Exception as e:
        import traceback
        if ctx:
            ctx.error(f"Error: {str(e)}")
            ctx.error(traceback.format_exc())
        return {
            "success": False, 
            "message": f"Generation failed: {str(e)}"
        }

# ────────────────────────────────────────────────────────────────────────────────
# TOOL 5: Create SUMO configuration file
# ────────────────────────────────────────────────────────────────────────────────
@mcp.tool()
async def create_sumo_config(
    net_file: str,
    route_file: str,
    simulation_name: str = "sim1",
    tls_file: str = None,
    gui: bool = True,
    begin_time: int = 0,
    end_time: int = 3600,
    ctx: Context = None,
) -> Dict[str, Any]:
    """Generate SUMO simulation configuration file and organize into specified folder structure.
    
    Args:
        net_file: Network file path
        route_file: Route file path
        simulation_name: Simulation name, used as subfolder name
        tls_file: Traffic signal timing file path, optional
        gui: Whether to use GUI mode
        begin_time: Start time (seconds)
        end_time: End time (seconds)
        ctx: Context object for logging
    """
    # Create basic directory structure
    base_dir = os.path.join("data", "simulation")
    sim_dir = os.path.join(base_dir, simulation_name)
    
    # Ensure directory exists
    os.makedirs(sim_dir, exist_ok=True)
    
    # Copy network and route files to simulation directory
    net_basename = os.path.basename(net_file)
    route_basename = os.path.basename(route_file)
    
    dst_net_file = os.path.join(sim_dir, net_basename)
    dst_route_file = os.path.join(sim_dir, route_basename)
    
    # Copy traffic signal file (if any)
    dst_tls_file = None
    tls_basename = None
    if tls_file and os.path.exists(tls_file):
        tls_basename = os.path.basename(tls_file)
        dst_tls_file = os.path.join(sim_dir, tls_basename)
    
    if ctx:
        ctx.info(f"--- Starting SUMO configuration creation ---")
        ctx.info(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        ctx.info(f"Network file: {net_file}")
        ctx.info(f"Route file: {route_file}")
        if tls_file:
            ctx.info(f"Traffic signal file: {tls_file}")
        ctx.info(f"Simulation name: {simulation_name}")
    
    # Copy files if source and destination are different
    try:
        if os.path.abspath(net_file) != os.path.abspath(dst_net_file):
            import shutil
            shutil.copy2(net_file, dst_net_file)
            if ctx:
                ctx.debug(f"Copied network file: {net_file} -> {dst_net_file}")
        
        if os.path.abspath(route_file) != os.path.abspath(dst_route_file):
            import shutil
            shutil.copy2(route_file, dst_route_file)
            if ctx:
                ctx.debug(f"Copied route file: {route_file} -> {dst_route_file}")
        
        if tls_file and os.path.exists(tls_file) and os.path.abspath(tls_file) != os.path.abspath(dst_tls_file):
            import shutil
            shutil.copy2(tls_file, dst_tls_file)
            if ctx:
                ctx.debug(f"Copied traffic signal file: {tls_file} -> {dst_tls_file}")
    except Exception as e:
        if ctx:
            ctx.error(f"Failed to copy file: {e}")
        return {"success": False, "message": f"Failed to copy file: {e}"}
    
    # Create configuration file
    output_file = os.path.join(sim_dir, "sim.sumocfg")
    
    # Build configuration file content
    additional_files = []
    if tls_basename:
        additional_files.append(tls_basename)
    
    additional_files_str = ""
    if additional_files:
        additional_files_str = f'<additional-files value="{",".join(additional_files)}"/>'
    
    config_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<configuration xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/sumoConfiguration.xsd">
    <input>
        <net-file value="{net_basename}"/>
        <route-files value="{route_basename}"/>
        {additional_files_str}
    </input>
    <time>
        <begin value="{begin_time}"/>
        <end value="{end_time}"/>
    </time>
    <processing>
        <ignore-route-errors value="true"/>
    </processing>
    <routing>
        <device.rerouting.adaptation-steps value="18"/>
        <device.rerouting.adaptation-interval value="10"/>
    </routing>
    <report>
        <verbose value="true"/>
        <duration-log.statistics value="true"/>
        <no-step-log value="true"/>
    </report>
</configuration>
"""
    try:
        with open(output_file, "w") as f:
            f.write(config_content)
        
        if ctx:
            ctx.info(f"Configuration file created: {output_file}")
            if tls_basename:
                ctx.info(f"Traffic signal configuration added: {tls_basename}")
        
        return {
            "success": True, 
            "message": "Configuration file created", 
            "data": {
                "simulation_dir": os.path.abspath(sim_dir),
                "config_file": os.path.abspath(output_file),
                "tls_file": os.path.abspath(dst_tls_file) if dst_tls_file else None,
                "run_cmd": f"{'sumo-gui' if gui else 'sumo'} -c {output_file}"
            }
        }
    except Exception as e:
        if ctx:
            ctx.error(f"Failed to create configuration: {e}")
        return {"success": False, "message": f"Failed to create configuration: {e}"}

# ────────────────────────────────────────────────────────────────────────────────
# TOOL 6: Run fixed-time control simulation
# ────────────────────────────────────────────────────────────────────────────────
@mcp.tool()
async def run_simulation(
    net_file: str,
    route_file: str,
    simulation_name: str = "sim1",
    control_type: str = "fixed",
    tls_file: str = None,
    gui: bool = False,
    begin_time: int = 0,
    end_time: int = 3600,
    min_time: int = 5,
    max_time: int = 60,
    ctx: Context = None,
) -> Dict[str, Any]:
    """Run SUMO traffic simulation with specified traffic signal control method.
    
    Args:
        net_file: Network file path
        route_file: Route file path
        simulation_name: Simulation name, used as subfolder name
        control_type: Traffic signal control type, supports "fixed", "actuated", "webster", "greenwave"
        tls_file: Traffic signal timing file path, if None will be auto-generated based on control_type
        gui: Whether to use GUI mode (use GUI to view single simulation; don't use GUI to compare multiple simulation metrics)
        begin_time: Start time (seconds)
        end_time: End time (seconds)
        min_time: Minimum phase time (seconds), only for actuated control
        max_time: Maximum phase time (seconds), only for actuated control
    """
    # Check input files
    if not os.path.exists(net_file):
        if ctx:
            ctx.error(f"Network file does not exist: {net_file}")
        return {"success": False, "message": f"Network file does not exist: {net_file}"}
    
    if not os.path.exists(route_file):
        if ctx:
            ctx.error(f"Route file does not exist: {route_file}")
        return {"success": False, "message": f"Route file does not exist: {route_file}"}
    
    # Validate control type
    valid_control_types = ["fixed", "actuated", "webster", "greenwave"]
    if control_type not in valid_control_types:
        if ctx:
            ctx.error(f"Invalid control type: {control_type}, supported types are: {', '.join(valid_control_types)}")
        return {"success": False, "message": f"Invalid control type: {control_type}"}
    
    # Create basic directory structure
    base_dir = os.path.join("data", "simulation")
    sim_dir = os.path.join(base_dir, simulation_name)
    results_dir = os.path.join(sim_dir, "results")
    
    # Ensure directory exists
    os.makedirs(results_dir, exist_ok=True)
    
    # Set output file path
    run_dir = os.path.join(results_dir, control_type)
    os.makedirs(run_dir, exist_ok=True)
    
    tripinfo_file = os.path.join(run_dir, f"tripinfo.xml")
    
    # Copy necessary files to run directory
    try:
        import shutil
        dst_net_file = os.path.join(run_dir, os.path.basename(net_file))
        dst_route_file = os.path.join(run_dir, os.path.basename(route_file))
        
        if os.path.abspath(net_file) != os.path.abspath(dst_net_file):
            shutil.copy2(net_file, dst_net_file)
            if ctx:
                ctx.debug(f"Copied network file: {net_file} -> {dst_net_file}")
        
        if os.path.abspath(route_file) != os.path.abspath(dst_route_file):
            shutil.copy2(route_file, dst_route_file)
            if ctx:
                ctx.debug(f"Copied route file: {route_file} -> {dst_route_file}")
        
    except Exception as e:
        if ctx:
            ctx.error(f"Failed to copy file: {e}")
        return {"success": False, "message": f"Failed to copy file: {e}"}
    
    # Prepare appropriate traffic signal file based on control type
    final_tls_file = None
    
    if ctx:
        ctx.info(f"--- Starting to prepare {control_type} control mode simulation ---")
    
    if control_type == "fixed":
        # Fixed timing mode
        if tls_file:
            # If tls file is provided, use it directly
            if os.path.exists(tls_file):
                dst_tls_file = os.path.join(run_dir, os.path.basename(tls_file))
                if os.path.abspath(tls_file) != os.path.abspath(dst_tls_file):
                    try:
                        shutil.copy2(tls_file, dst_tls_file)
                        final_tls_file = dst_tls_file
                        if ctx:
                            ctx.info(f"Using provided fixed timing plan: {dst_tls_file}")
                    except Exception as e:
                        if ctx:
                            ctx.warning(f"Failed to copy signal file: {e}")
            else:
                if ctx:
                    ctx.warning(f"Provided signal file does not exist: {tls_file}")
        
                # If not provided or provided file is invalid, try to extract from network file
        if not final_tls_file:
            try:
                if ctx:
                    ctx.info(f"Extracting default traffic signal timing plan from network file...")
                
                extracted_tls_file = os.path.join(run_dir, f"{control_type}_tls.add.xml")
                from tools.separate_light import separate_traffic_lights
                separate_traffic_lights(dst_net_file, extracted_tls_file, program_id='fixed')
                
                if os.path.exists(extracted_tls_file) and os.path.getsize(extracted_tls_file) > 0:
                    final_tls_file = extracted_tls_file
                    if ctx:
                        ctx.info(f"Successfully extracted default traffic signal timing plan: {extracted_tls_file}")
                else:
                    if ctx:
                        ctx.warning(f"No traffic signals found or extraction failed")
            except Exception as e:
                if ctx:
                    ctx.warning(f"Failed to extract default traffic signal timing plan: {str(e)}")
    
    elif control_type == "actuated":
        # Actuated control mode
        actuated_tls_file = os.path.join(run_dir, f"{control_type}_tls.add.xml")
        
        # First try to get base timing plan (from provided file or extract from network file)
        base_tls_file = None
        if tls_file and os.path.exists(tls_file):
            base_tls_file = tls_file
            if ctx:
                ctx.info(f"Using provided signal file as base: {tls_file}")
        else:
            try:
                if ctx:
                    ctx.info(f"Extracting base traffic signal timing plan from network file...")
                
                temp_tls_file = os.path.join(run_dir, "temp_tls.add.xml")
                from tools.separate_light import separate_traffic_lights
                separate_traffic_lights(dst_net_file, temp_tls_file, program_id='actuated')
                
                if os.path.exists(temp_tls_file) and os.path.getsize(temp_tls_file) > 0:
                    base_tls_file = temp_tls_file
                    if ctx:
                        ctx.info(f"Successfully extracted base traffic signal timing plan")
                else:
                    if ctx:
                        ctx.warning(f"No traffic signals found or extraction failed")
            except Exception as e:
                if ctx:
                    ctx.warning(f"Failed to extract base traffic signal timing plan: {str(e)}")
        
        # Convert base timing plan to actuated control
        if base_tls_file:
            try:
                import xml.etree.ElementTree as ET
                
                if ctx:
                    ctx.info(f"Converting traffic signal timing plan to actuated control...")
                
                # Parse original tls file
                tree = ET.parse(base_tls_file)
                root = tree.getroot()
                
                # Convert to actuated control
                for tlLogic in root.findall('./tlLogic'):
                    # Set as actuated control
                    tlLogic.set('type', 'actuated')
                    tlLogic.set('programID', 'actuated')
                    
                    # Modify each phase
                    for phase in tlLogic.findall('./phase'):
                        # Get original phase information
                        duration = int(phase.get('duration', '30'))
                        state = phase.get('state', '')
                        
                        # Set actuated phase attributes
                        phase.set('duration', str(max_time))
                        phase.set('minDur', str(min(min_time, duration)))
                        phase.set('maxDur', str(max_time))
                        phase.set('state', state)
                
                # Save converted file
                tree.write(actuated_tls_file, encoding='utf-8', xml_declaration=True)
                final_tls_file = actuated_tls_file
                
                if ctx:
                    ctx.info(f"Successfully converted to actuated control: {actuated_tls_file}")
            except Exception as e:
                if ctx:
                    ctx.warning(f"Failed to convert to actuated control: {str(e)}")
    
    elif control_type == "webster":
        # Webster timing mode
        # Find tlsCycleAdaptation.py script
        sumo_tools_dir = os.path.join(os.environ.get("SUMO_HOME", ""), "tools")
        tls_script = os.path.join(sumo_tools_dir, "tlsCycleAdaptation.py")
        
        if not os.path.exists(tls_script):
            alt_script = os.path.join(os.path.dirname(__file__), "tools", "tlsCycleAdaptation.py")
            if os.path.exists(alt_script):
                tls_script = alt_script
            else:
                if ctx:
                    ctx.error(f"Script not found: tlsCycleAdaptation.py")
                return {"success": False, "message": f"Script not found: tlsCycleAdaptation.py"}
        
        # Generate Webster timing plan
        webster_tls_file = os.path.join(run_dir, f"{control_type}_tls.add.xml")
        
        try:
            if ctx:
                ctx.info(f"Generating Webster timing plan...")
            
            # Build command
            webster_cmd = [
                "python",
                tls_script,
                "-n", dst_net_file,
                "-r", dst_route_file,
                "-o", webster_tls_file
            ]
            
            # Log command
            if ctx:
                ctx.info(f"Executing command: {' '.join(webster_cmd)}")
            
            # Execute command
            process = subprocess.run(
                webster_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                check=False,
                timeout=300,  # 5 minutes timeout
                shell=True
            )
            
            # Log output
            if ctx:
                ctx.debug(f"Command return code: {process.returncode}")
                ctx.debug("Command output:")
                ctx.debug(process.stdout)
            
            if process.returncode != 0:
                if ctx:
                    ctx.error("Failed to generate Webster timing")
                return {
                    "success": False,
                    "message": "Failed to generate Webster timing",
                    "error": process.stdout
                }
            
            if not os.path.exists(webster_tls_file) or os.path.getsize(webster_tls_file) == 0:
                if ctx:
                    ctx.error("Webster timing file generation failed or is empty")
                return {
                    "success": False,
                    "message": "Webster timing file generation failed or is empty"
                }
            
            final_tls_file = webster_tls_file
            if ctx:
                ctx.info(f"Successfully generated Webster timing plan: {webster_tls_file}")
        
        except Exception as e:
            if ctx:
                ctx.error(f"Failed to generate Webster timing: {str(e)}")
            return {"success": False, "message": f"Failed to generate Webster timing: {str(e)}"}
    
    elif control_type == "greenwave":
        # Green wave timing mode
        # Find tlsCoordinator.py script
        sumo_tools_dir = os.path.join(os.environ.get("SUMO_HOME", ""), "tools")
        tls_script = os.path.join(sumo_tools_dir, "tlsCoordinator.py")
        
        if not os.path.exists(tls_script):
            alt_script = os.path.join(os.path.dirname(__file__), "tools", "tlsCoordinator.py")
            if os.path.exists(alt_script):
                tls_script = alt_script
            else:
                if ctx:
                    ctx.error(f"Script not found: tlsCoordinator.py")
                return {"success": False, "message": f"Script not found: tlsCoordinator.py"}
        
        # Generate green wave timing plan
        greenwave_tls_file = os.path.join(run_dir, f"{control_type}_tls.add.xml")
        
        try:
            if ctx:
                ctx.info(f"Generating green wave coordination timing plan...")
            
            # Build command
            greenwave_cmd = [
                "python",
                tls_script,
                "-n", dst_net_file,
                "-r", dst_route_file,
                "-o", greenwave_tls_file
            ]
            
            # Log command
            if ctx:
                ctx.info(f"Executing command: {' '.join(greenwave_cmd)}")
            
            # Execute command
            process = subprocess.run(
                greenwave_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                check=False,
                timeout=300,  # 5 minutes timeout
                shell=True
            )
            
            # Log output
            if ctx:
                ctx.debug(f"Command return code: {process.returncode}")
                ctx.debug("Command output:")
                ctx.debug(process.stdout)
            
            if process.returncode != 0:
                if ctx:
                    ctx.error("Failed to generate green wave coordination timing")
                return {
                    "success": False,
                    "message": "Failed to generate green wave coordination timing",
                    "error": process.stdout
                }
            
            if not os.path.exists(greenwave_tls_file) or os.path.getsize(greenwave_tls_file) == 0:
                if ctx:
                    ctx.error("Green wave coordination timing file generation failed or is empty")
                return {
                    "success": False,
                    "message": "Green wave coordination timing file generation failed or is empty"
                }
            
            final_tls_file = greenwave_tls_file
            if ctx:
                ctx.info(f"Successfully generated green wave coordination timing plan: {greenwave_tls_file}")
        
        except Exception as e:
            if ctx:
                ctx.error(f"Failed to generate green wave coordination timing: {str(e)}")
            return {"success": False, "message": f"Failed to generate green wave coordination timing: {str(e)}"}
    
    # Generate simulation configuration file
    config_file = os.path.join(run_dir, f"sim.sumocfg")
    
    # Add traffic signal file to configuration if available
    additional_files_str = ""
    if final_tls_file and os.path.exists(final_tls_file):
        additional_files_str = f'<additional-files value="{os.path.basename(final_tls_file)}"/>'
    
    config_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<configuration xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/sumoConfiguration.xsd">
    <input>
        <net-file value="{os.path.basename(dst_net_file)}"/>
        <route-files value="{os.path.basename(dst_route_file)}"/>
        {additional_files_str}
    </input>
    <time>
        <begin value="{begin_time}"/>
        <end value="{end_time}"/>
    </time>
    <output>
        <tripinfo-output value="{os.path.basename(tripinfo_file)}"/>
    </output>
    <processing>
        <ignore-route-errors value="true"/>
        <time-to-teleport value="300"/>
        <collision.action value="warn"/>
    </processing>
    <report>
        <verbose value="true"/>
        <duration-log.statistics value="true"/>
        <no-step-log value="true"/>
    </report>
</configuration>
"""
    try:
        with open(config_file, "w") as f:
            f.write(config_content)
        
        if ctx:
            ctx.info(f"--- Starting {control_type} control simulation {control_type} ---")
            ctx.info(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            ctx.info(f"Network file: {dst_net_file}")
            ctx.info(f"Route file: {dst_route_file}")
            if final_tls_file and os.path.exists(final_tls_file):
                ctx.info(f"Signal file: {final_tls_file}")
            ctx.info(f"Created simulation configuration file: {config_file}")
        
        # Build SUMO command
        sumo_cmd = ["sumo-gui" if gui else "sumo", "-c", config_file]
        
        # Log command
        if ctx:
            ctx.info(f"Executing command: {' '.join(sumo_cmd)}")
        
        # Execute SUMO command
        process = subprocess.run(
            sumo_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
            timeout=600,  # 10 minutes timeout
            shell=True
        )
        
        # Log output
        if ctx:
            ctx.debug(f"Command return code: {process.returncode}")
            ctx.debug("Command output:")
            ctx.debug(process.stdout)
        
        if process.returncode != 0:
            if ctx:
                ctx.error("SUMO execution failed")
            return {
                "success": False,
                "message": "SUMO execution failed",
                "error": process.stdout
            }
        
        # Check result file
        if not os.path.exists(tripinfo_file) or os.path.getsize(tripinfo_file) == 0:
            if ctx:
                ctx.error("Tripinfo file generation failed or is empty")
            return {
                "success": False,
                "message": "Tripinfo file generation failed or is empty"
            }
        
        if ctx:
            ctx.info(f"--- {control_type} control simulation completed ---")
            ctx.info(f"Completion time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            ctx.info(f"Results directory: {run_dir}")
            ctx.info(f"Trip information: {tripinfo_file}")
        
        return {
            "success": True,
            "message": f"{control_type} control simulation completed",
            "data": {
                "run_dir": os.path.abspath(run_dir),
                "config_file": os.path.abspath(config_file),
                "tripinfo_file": os.path.abspath(tripinfo_file),
                "tls_file": os.path.abspath(final_tls_file) if final_tls_file else None,
                "control_type": control_type
            }
        }
    
    except subprocess.TimeoutExpired:
        if ctx:
            ctx.error("Simulation execution timed out")
        return {
            "success": False,
            "message": "Simulation execution timed out"
        }
    except Exception as e:
        import traceback
        if ctx:
            ctx.error(f"Failed to execute simulation: {str(e)}")
            ctx.error(traceback.format_exc())
        return {
            "success": False,
            "message": f"Failed to execute simulation: {str(e)}"
        }

# ────────────────────────────────────────────────────────────────────────────────
# TOOL 7: Compare multiple simulation results' performance metrics and generate charts
# ────────────────────────────────────────────────────────────────────────────────
@mcp.tool()
async def compare_simulation_results(
    tripinfo_files: str,
    labels: str = None,
    output_dir: str = "",
    ctx: Context = None,
) -> Dict[str, Any]:
    """Compare performance metrics of multiple simulation results and generate charts.
    
    Args:
        tripinfo_files: List of tripinfo file paths, can be JSON string or Python list
        labels: List of labels corresponding to each tripinfo file, can be JSON string or Python list
        output_dir: Output directory, default is the parent directory of the first tripinfo file's directory
    """
    # Process tripinfo_files parameter
    if isinstance(tripinfo_files, str):
        # If it's a string, try to parse as JSON
        import json
        try:
            if tripinfo_files.startswith("[") and tripinfo_files.endswith("]"):
                # First replace backslashes in JSON string with forward slashes or double backslashes
                normalized_json = tripinfo_files.replace("\\", "/")
                tripinfo_files = json.loads(normalized_json)
            else:
                # May be a single file path or comma-separated multiple paths
                if "," in tripinfo_files:
                    tripinfo_files = tripinfo_files.split(",")
                else:
                    tripinfo_files = [tripinfo_files]
        except json.JSONDecodeError:
            # If not valid JSON, assume it's a single file path or comma-separated multiple paths
            if "," in tripinfo_files:
                tripinfo_files = tripinfo_files.split(",")
            else:
                tripinfo_files = [tripinfo_files]
    
    # Normalize all paths
    normalized_files = []
    for path in tripinfo_files:
        # Handle various formats in Windows paths
        # 1. Convert double slash format (//) to single slash
        path = path.replace("//", "/")
        # 2. Convert forward slash (/) to system path separator
        path = os.path.normpath(path)
        normalized_files.append(path)
    
    tripinfo_files = normalized_files
    
    if ctx:
        ctx.info(f"Processed file paths: {tripinfo_files}")
    
    # Process labels parameter
    if labels is not None:
        if isinstance(labels, str):
            # If it's a string, try to parse as JSON
            import json
            try:
                if labels.startswith("[") and labels.endswith("]"):
                    labels = json.loads(labels)
                else:
                    # May be a single label or comma-separated multiple labels
                    if "," in labels:
                        labels = labels.split(",")
                    else:
                        labels = [labels]
            except json.JSONDecodeError:
                # If not valid JSON, assume it's a single label or comma-separated multiple labels
                if "," in labels:
                    labels = labels.split(",")
                else:
                    labels = [labels]
    
    if not tripinfo_files:
        if ctx:
            ctx.error("Error: At least one tripinfo file is required")
        return {"success": False, "message": "Error: At least one tripinfo file is required"}
    
    # Verify all files exist
    missing_files = []
    for f in tripinfo_files:
        if not os.path.exists(f):
            # Try different path formats
            alt_paths = [
                f.replace("/", "\\"),  # Forward slash to backslash
                f.replace("\\", "/"),  # Backslash to forward slash
                f.replace("//", "/"),  # Double forward slash to single forward slash
                f.replace("\\\\", "\\")  # Double backslash to single backslash
            ]
            
            found = False
            for alt_path in alt_paths:
                if os.path.exists(alt_path):
                    # Update to valid path
                    tripinfo_files[tripinfo_files.index(f)] = alt_path
                    found = True
                    if ctx:
                        ctx.debug(f"Found alternative path: {alt_path}")
                    break
            
            if not found:
                missing_files.append(f)
                if ctx:
                    ctx.debug(f"File does not exist: {f}")
                    ctx.debug(f"None of the alternative paths exist")
    
    if missing_files:
        if ctx:
            ctx.error(f"The following tripinfo files do not exist: {', '.join(missing_files)}")
        return {"success": False, "message": f"The following tripinfo files do not exist: {', '.join(missing_files)}"}
    
    # If no labels provided, use default labels
    if not labels or len(labels) != len(tripinfo_files):
        labels = [f"Method{i+1}" for i in range(len(tripinfo_files))]
    
    # Determine output directory
    if not output_dir:
        # Default to parent directory of first tripinfo file's directory
        first_file_dir = os.path.dirname(tripinfo_files[0])
        output_dir = os.path.dirname(first_file_dir)
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Build compare_and_draw.py script path
    script_path = os.path.join(os.path.dirname(__file__), "tools", "compare_and_draw.py")
    if not os.path.exists(script_path):
        if ctx:
            ctx.error(f"Script not found: {script_path}")
        return {"success": False, "message": f"Script not found: {script_path}"}
    
    # Build command
    cmd = ["python", script_path]
    for f in tripinfo_files:
        cmd.extend(["--results", f])
    for l in labels:
        cmd.extend(["--labels", l])
    cmd.extend(["--output", output_dir])
    
    if ctx:
        ctx.info(f"--- Starting to compare simulation results ---")
        ctx.info(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        ctx.info(f"Files to compare: {', '.join(tripinfo_files)}")
        ctx.info(f"Labels: {', '.join(labels)}")
        ctx.info(f"Output directory: {output_dir}")
        ctx.info(f"Executing command: {' '.join(cmd)}")
    
    try:
        # Execute command
        process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
            timeout=300,  # 5 minutes timeout
            shell=True
        )
        
        # Log output
        if ctx:
            ctx.debug(f"Command return code: {process.returncode}")
            ctx.debug("Command output:")
            ctx.debug(process.stdout)
        
        if process.returncode != 0:
            if ctx:
                ctx.error("Comparison script execution failed")
            return {
                "success": False,
                "message": "Comparison script execution failed",
                "error": process.stdout
            }
        
        # Check expected output files
        expected_files = [
            os.path.join(output_dir, "comparison_radar.png"),
            os.path.join(output_dir, "comparison_metrics.csv")
        ]
        
        missing_output = []
        for f in expected_files:
            if not os.path.exists(f):
                missing_output.append(f)
        
        if missing_output:
            if ctx:
                ctx.warning(f"The following expected output files were not generated: {', '.join(missing_output)}")
        
        if ctx:
            ctx.info(f"--- Comparison completed ---")
            ctx.info(f"Completion time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            if os.path.exists(os.path.join(output_dir, "comparison_radar.png")):
                ctx.info(f"Radar chart: {os.path.join(output_dir, 'comparison_radar.png')}")
            if os.path.exists(os.path.join(output_dir, "comparison_metrics.csv")):
                ctx.info(f"Metrics data: {os.path.join(output_dir, 'comparison_metrics.csv')}")
        
        return {
            "success": True,
            "message": "Simulation results comparison completed",
            "data": {
                "output_dir": os.path.abspath(output_dir),
                "image_path": os.path.abspath(os.path.join(output_dir, "comparison_radar.png")) if os.path.exists(os.path.join(output_dir, "comparison_radar.png")) else None,
                "metrics_csv": os.path.abspath(os.path.join(output_dir, "comparison_metrics.csv")) if os.path.exists(os.path.join(output_dir, "comparison_metrics.csv")) else None
            }
        }
    
    except subprocess.TimeoutExpired:
        if ctx:
            ctx.error("Comparison script execution timed out")
        return {
            "success": False,
            "message": "Comparison script execution timed out"
        }
    except Exception as e:
        import traceback
        if ctx:
            ctx.error(f"Comparison failed: {str(e)}")
            ctx.error(traceback.format_exc())
        return {
            "success": False,
            "message": f"Comparison failed: {str(e)}"
        }

# ────────────────────────────────────────────────────────────────────────────────
# MCP Resources
# ────────────────────────────────────────────────────────────────────────────────
@mcp.resource("data://radar/{simulation_name}")
def get_radar_chart(simulation_name: str) -> Image:
    """Provide radar chart resource for specified simulation.
    
    Args:
        simulation_name: Simulation name
        
    Returns:
        Image object of radar chart
    """
    # Find radar chart file path
    base_dir = os.path.join("data", "simulation", simulation_name)
    results_dir = os.path.join(base_dir, "results")
    radar_path = os.path.join(results_dir, "comparison_radar.png")
    
    # If not found, try to look in results directory
    if not os.path.exists(radar_path):
        for root, dirs, files in os.walk(results_dir):
            for file in files:
                if file == "comparison_radar.png":
                    radar_path = os.path.join(root, file)
                    break
            if os.path.exists(radar_path):
                break
    
    # If radar chart is found, read and return Image object
    if os.path.exists(radar_path):
        with open(radar_path, "rb") as f:
            data = f.read()
        return Image(data=data, format="png")
    
    # If radar chart is not found, return empty image
    return None

@mcp.resource("data://metrics/{simulation_name}")
def get_metrics_data(simulation_name: str) -> dict:
    """Provide metrics data for specified simulation as JSON.
    
    Args:
        simulation_name: Simulation name
        
    Returns:
        Metrics data JSON object
    """
    # Find metrics CSV file path
    base_dir = os.path.join("data", "simulation", simulation_name)
    results_dir = os.path.join(base_dir, "results")
    metrics_path = os.path.join(results_dir, "comparison_metrics.csv")
    
    # If not found, try to look in results directory
    if not os.path.exists(metrics_path):
        for root, dirs, files in os.walk(results_dir):
            for file in files:
                if file == "comparison_metrics.csv":
                    metrics_path = os.path.join(root, file)
                    break
            if os.path.exists(metrics_path):
                break
    
    # If metrics file is found, read and process as dictionary
    if os.path.exists(metrics_path):
        import csv
        headers = []
        rows = []
        with open(metrics_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for i, row in enumerate(reader):
                if i == 0:  # Header row contains metric names
                    headers = row[1:]  # Skip first column (empty column)
                else:
                    method_name = row[0]
                    values = row[1:]
                    # Convert to float
                    values = [float(v) if v else 0.0 for v in values]
                    rows.append({"method": method_name, "values": values})
        
        # Construct result
        result = {
            "metrics": headers,
            "methods": [r["method"] for r in rows],
            "data": rows
        }
        return result
    
    # If metrics file is not found, return empty object
    return {"metrics": [], "methods": [], "data": []}

@mcp.resource("data://tripinfo/{simulation_name}/{control_type}")
def get_tripinfo(simulation_name: str, control_type: str) -> str:
    """Provide trip information XML for specified simulation and control type.
    
    Args:
        simulation_name: Simulation name
        control_type: Control type (fixed, actuated, webster, greenwave)
        
    Returns:
        Trip information XML string
    """
    # Find trip information file path
    base_dir = os.path.join("data", "simulation", simulation_name)
    results_dir = os.path.join(base_dir, "results")
    control_dir = os.path.join(results_dir, control_type)
    tripinfo_path = os.path.join(control_dir, "tripinfo.xml")
    
    # If trip information file is found, read and return content
    if os.path.exists(tripinfo_path):
        with open(tripinfo_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    # If trip information file is not found, return empty string
    return ""

# ────────────────────────────────────────────────────────────────────────────────
# Application entry
# ────────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run(transport="sse", host = "127.0.0.1", port = 8015)