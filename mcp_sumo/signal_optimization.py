import os
os.environ["SUMO_HOME"] = "D:\Program Files\SUMO"
from fastmcp import FastMCP, Context
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Tuple, Optional
import time
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['SimHei']
import numpy as np
from datetime import datetime
import csv

# ────────────────────────────────────────────────────────────────────────────────
# Initialize FastMCP
# ────────────────────────────────────────────────────────────────────────────────
mcp = FastMCP(name = "signal_optimization")

@mcp.prompt()
def get_signal_optimization_guidance() -> str:
    """
    Get signal optimization prompt template
    
    Returns:
        Prompt template string
    """
    template = """
The user wants to perform signal control optimization. Please ask the user to provide the following information:
1. Road network name
2. Traffic flow CSV file path
3. Signal control scheme CSV file path


Please help me complete the signal optimization task according to the following process:
1. If the user provides an OD matrix, use the generate_routes_from_od tool to generate traffic flow files
2. Generate signal control plan tls files from the user-provided signal control scheme CSV file
3. Run initial simulation to obtain evaluation metrics
4. Analyze simulation results, identify congested intersections, identify and optimize at least 5 intersections, print the intersection id and the metrics
5. Call the cal_lane_metrics tool to calculate lane-level metrics
6. Analyze intersection congestion directions from lane-level metrics, combined with intersection signal phase information from the CSV file, improve the original signal control scheme, which can include improving phase duration, cycle length, offset, etc.
7. Copy the original signal control scheme, apply the improved timing plan, and generate an optimized timing plan CSV file
8. Generate improved timing plan tls files from the improved timing plan CSV file
9. Simulate again using the optimized plan to obtain evaluation metrics
10. Compare metrics before and after optimization, form an optimization report, including:
   - Congested intersection analysis
   - Signal control plan optimizations and reasons
   - Before and after timing plan comparison (in table format)
   - Before and after metrics comparison (in table format)
   - Optimization effect assessment

Please explain your analysis process and decision reasoning in detail for each step.
"""
    return template

@mcp.tool()
def generate_routes_from_od(
    net_file: str,
    od_file: str,
    output_dir: str = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Generate SUMO traffic route files from OD matrix
    
    Args:
        net_file: SUMO network file path
        od_file: OD matrix CSV file path (tab-separated)
        output_dir: Output directory, defaults to output folder in the same directory as the OD file
        
    Returns:
        Route file path
    """
    from tools.OD2rou import generate_traffic_from_od
    
    if ctx:
        ctx.info(f"Starting route generation from OD matrix: {od_file}")
    
    # Check if files exist
    if not os.path.exists(net_file):
        if ctx:
            ctx.error(f"Network file does not exist: {net_file}")
        return {"success": False, "message": f"Network file does not exist: {net_file}"}
    
    if not os.path.exists(od_file):
        if ctx:
            ctx.error(f"OD matrix file does not exist: {od_file}")
        return {"success": False, "message": f"OD matrix file does not exist: {od_file}"}
    
    # If output directory is not specified, use default directory
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(od_file), "output")
    
    try:
        # Call function from OD2rou.py to generate routes
        routes_file_path = generate_traffic_from_od(net_file, od_file, output_dir)
        
        # Check generated files
        taz_file = os.path.join(output_dir, "taz.xml")
        taz_relation_file = os.path.join(output_dir, "tazRelation.xml")
        trips_file = os.path.join(output_dir, "trips.xml")
        
        if ctx:
            ctx.info(f"Route generation completed: {routes_file_path}")
        
        return {
            "success": True,
            "message": "Route file generated successfully",
            "files": {
                "routes": routes_file_path
            },
            "output_dir": output_dir
        }
    
    except Exception as e:
        if ctx:
            ctx.error(f"Route generation exception: {str(e)}")
        import traceback
        return {
            "success": False,
            "message": f"Route generation exception: {str(e)}",
            "traceback": traceback.format_exc()
        }

@mcp.tool()
def run_simulation(
    net_file: str,
    route_file: str,
    tls_file: str = None,
    simulation_name: str = "sim1",
    begin_time: int = 0,
    end_time: int = 3600,
    output_dir: str = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Execute SUMO simulation and output performance metric files
    
    Args:
        net_file: Network file path
        route_file: Traffic flow file path
        tls_file: Signal control plan file path (optional)
        simulation_name: Simulation name
        begin_time: Simulation start time
        end_time: Simulation end time
        output_dir: Output directory, defaults to "data/{simulation_name}/simulation_output"
        ctx: Context object
        
    Returns:
        Dictionary containing simulation result paths
    """
    if ctx:
        ctx.info(f"Starting SUMO simulation: {simulation_name}")
    
    # Check if files exist
    if not os.path.exists(net_file):
        if ctx:
            ctx.error(f"Network file does not exist: {net_file}")
        return {"success": False, "message": f"Network file does not exist: {net_file}"}
    
    if not os.path.exists(route_file):
        if ctx:
            ctx.error(f"Traffic flow file does not exist: {route_file}")
        return {"success": False, "message": f"Traffic flow file does not exist: {route_file}"}
    
    if tls_file and not os.path.exists(tls_file):
        if ctx:
            ctx.warning(f"Signal file does not exist: {tls_file}")
        tls_file = None
    
    # Create output directory
    if output_dir is None:
        output_dir = os.path.join("data", simulation_name, "simulation_output")
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Set output file paths
    tripinfo_file = os.path.join(output_dir, f"{simulation_name}_tripinfo.xml")
    queue_file = os.path.join(output_dir, f"{simulation_name}_queue.xml")
    edge_data_file = os.path.join(output_dir, f"{simulation_name}_edgedata.xml")
    
    # Build SUMO command
    sumo_cmd = [
        "sumo",  # Use command line mode, without GUI
        "-n", net_file,
        "-r", route_file,
        "--begin", str(begin_time),
        "--end", str(end_time),
        "--no-step-log", "true",
        "--no-warnings", "true",
        "--tripinfo-output", tripinfo_file,
        "--queue-output", queue_file,
        "--edgedata-output", edge_data_file,
        "--waiting-time-memory", "3600",
        "--duration-log.statistics", "true"
    ]
    
    # If signal timing file is provided, add to command
    if tls_file:
        sumo_cmd.extend(["-a", tls_file])
    
    if ctx:
        ctx.info(f"SUMO command: {' '.join(sumo_cmd)}")
    
    try:
        # Execute SUMO simulation
        import subprocess
        process = subprocess.run(
            sumo_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False
        )
        
        # Check if execution was successful
        if process.returncode != 0:
            if ctx:
                ctx.error(f"SUMO execution failed, return code: {process.returncode}")
                ctx.error(f"Output: {process.stdout}")
            return {
                "success": False,
                "message": "SUMO execution failed",
                "output": process.stdout,
                "return_code": process.returncode
            }
        
        # Check if output files were generated
        if not os.path.exists(tripinfo_file) or not os.path.exists(queue_file) or not os.path.exists(edge_data_file):
            if ctx:
                ctx.warning("Some output files were not generated")
        
        if ctx:
            ctx.info(f"Simulation completed: {simulation_name}")
        
        return {
            "success": True,
            "message": "Simulation executed successfully",
            "files": {
                "tripinfo": tripinfo_file,
                "queue": queue_file,
                "edge_data": edge_data_file
            },
            "simulation_name": simulation_name,
            "output_dir": output_dir
        }
    
    except Exception as e:
        if ctx:
            ctx.error(f"Simulation execution exception: {str(e)}")
        import traceback
        return {
            "success": False,
            "message": f"Simulation execution exception: {str(e)}",
            "traceback": traceback.format_exc()
        }

# @mcp.tool()
# def get_traffic_light_details(
#     net_file: str,
#     tls_file: str,
#     junction_id: str,
#     ctx: Context = None
# ) -> Dict[str, Any]:
#     """
#     Get signal phase details for specified intersection
    
#     Args:
#     net_file: SUMO network file path
#     tls_file: SUMO signal file path
#     junction_id: Intersection ID
    
#     Returns:
#     Dictionary containing signal phase information
#     """
#     from tools.junction_utils import analyze_traffic_light_phases
    
#     if ctx:
#         ctx.info(f"Starting analysis of intersection {junction_id} signal phases")
    
#     # Check if files exist
#     if not os.path.exists(net_file):
#         if ctx:
#             ctx.error(f"Network file does not exist: {net_file}")
#         return {"success": False, "message": f"Network file does not exist: {net_file}"}
    
#     try:
#         # Call analyze_traffic_light_phases function to get phase information
#         phases_info = analyze_traffic_light_phases(net_file, tls_file, junction_id)
        
#         if phases_info is None:
#             if ctx:
#                 ctx.warning(f"Unable to get signal phase information for intersection {junction_id}")
#             return {
#                 "success": False,
#                 "message": f"Unable to get signal phase information for intersection {junction_id}"
#             }
        
#         # Format phase information for better display
#         formatted_phases = []
#         for i, phase in enumerate(phases_info):
#             formatted_phase = {
#                 "phase_id": i + 1,
#                 "duration": phase["duration"],
#                 "description": phase["description"],
#                 "allowed_lanes": list(phase["allowed_lanes"])
#             }
#             formatted_phases.append(formatted_phase)
        
#         if ctx:
#             ctx.info(f"Intersection {junction_id} has {len(formatted_phases)} phases")
#             for phase in formatted_phases:
#                 ctx.info(f"Phase {phase['phase_id']}: Duration {phase['duration']} seconds, Direction: {phase['description']}")
        
#         return {
#             "success": True,
#             "junction_id": junction_id,
#             "phases_count": len(formatted_phases),
#             "phases": formatted_phases
#         }
    
#     except Exception as e:
#         if ctx:
#             ctx.error(f"Error analyzing intersection signal phases: {str(e)}")
#         import traceback
#         return {
#             "success": False,
#             "message": f"Error analyzing intersection signal phases: {str(e)}",
#             "traceback": traceback.format_exc()
#         }

@mcp.tool()
def cal_lane_metrics(xml_path: str) -> Optional[Dict[str, Dict[str, float]]]:
    """
    Calculate queue metrics for each lane from queue.xml output file
    
    Args:
        xml_path: queue.xml file path
    
    Returns:
        Dictionary containing average queue time and queue length for each lane
    """
    if not os.path.exists(xml_path):
        return None
        
    # Load XML file
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    # Initialize counters and result dictionary
    lane_metrics = {}
    max_timestep = 0
    
    # Traverse data for all timesteps
    for data in root.findall("data"):
        timestep = float(data.get("timestep"))
        max_timestep = max(max_timestep, timestep)
        
        # Traverse all lanes for this timestep
        for lane in data.find("lanes").findall("lane"):
            lane_id = lane.get("id")
            
            # Skip internal lanes (starting with ":")
            if lane_id.startswith(":"):
                continue
                
            # Get queue time and length
            queue_time = float(lane.get("queueing_time"))
            queue_length = float(lane.get("queueing_length"))
            
            # Initialize lane data
            if lane_id not in lane_metrics:
                lane_metrics[lane_id] = {
                    "total_queue_time": 0.0,
                    "total_queue_length": 0.0
                }
            
            # Accumulate current timestep lane data
            lane_metrics[lane_id]["total_queue_time"] += queue_time
            lane_metrics[lane_id]["total_queue_length"] += queue_length
    
    # Calculate total simulation duration (number of timesteps)
    simulation_timesteps = max_timestep + 1
    
    # Calculate average for each lane
    result = {}
    for lane_id, metrics in lane_metrics.items():
        result[lane_id] = {
            "avg_queue_time": metrics["total_queue_time"] / simulation_timesteps,
            "avg_queue_length": metrics["total_queue_length"] / simulation_timesteps
        }
    
    return result

@mcp.tool()
def cal_simulation_metrics(
    edge_data_path: str = None,
    queue_data_path: str = None,
    tripinfo_path: str = None,
    output_file: str = None
) -> str:
    """
    Get all simulation performance metrics at once and save to JSON file
    
    Args:
        edge_data_path: edgedata.xml file path
        queue_data_path: queue.xml file path
        tripinfo_path: tripinfo.xml file path
        output_file: Output JSON file path, defaults to metrics_{timestamp}.json
    
    Returns:
        Saved JSON file path
    """
    # Import functions from get_score module
    from tools.get_score import cal_edge_metrics, cal_junction_metrics, cal_network_metrics
    
    result = {}
    
    # Get road edge metrics
    if edge_data_path and os.path.exists(edge_data_path):
        edge_metrics = cal_edge_metrics(edge_data_path)
        if edge_metrics:
            result["edge_metrics"] = edge_metrics
    
    # Get junction queue metrics
    if queue_data_path and os.path.exists(queue_data_path):
        junction_metrics = cal_junction_metrics(queue_data_path)
        if junction_metrics:
            result["junction_metrics"] = junction_metrics
    
    # Get network level metrics
    if tripinfo_path and os.path.exists(tripinfo_path):
        network_metrics = cal_network_metrics(tripinfo_path)
        if network_metrics:
            result["network_metrics"] = network_metrics
    
    # Generate output file path
    if output_file is None:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        metrics_dir = os.path.join("data", "metrics")
        os.makedirs(metrics_dir, exist_ok=True)
        output_file = os.path.join(metrics_dir, f"metrics_{timestamp}.json")
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Save as JSON file
    import json
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    return output_file

@mcp.tool()
def compare_metrics(before_metrics_path: str, after_metrics_path: str, output_file: str = None) -> str:
    """
    Compare metrics before and after optimization, reading metrics from JSON files
    
    Args:
        before_metrics_path: Pre-optimization metrics file path
        after_metrics_path: Post-optimization metrics file path
        output_file: Output comparison result JSON file path, defaults to comparison_{timestamp}.json
        
    Returns:
        Saved comparison result JSON file path
    """
    # Read metrics files
    import json
    
    try:
        with open(before_metrics_path, 'r', encoding='utf-8') as f:
            before_metrics = json.load(f)
        
        with open(after_metrics_path, 'r', encoding='utf-8') as f:
            after_metrics = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        return {"error": f"Failed to read metrics files: {str(e)}"}
    
    # Generate output file path
    if output_file is None:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        comparison_dir = os.path.join("data", "comparison")
        os.makedirs(comparison_dir, exist_ok=True)
        output_file = os.path.join(comparison_dir, f"comparison_{timestamp}.json")
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Calculate comparison results
    improvements = {}
    
    # Process top-level metrics (edge_metrics, junction_metrics, network_metrics)
    all_keys = set(before_metrics.keys()) & set(after_metrics.keys())
    
    for key in all_keys:
        if key == "network_metrics":
            # Network level metrics comparison
            network_before = before_metrics[key]
            network_after = after_metrics[key]
            network_improved = {}
            
            for metric in set(network_before.keys()) & set(network_after.keys()):
                if isinstance(network_before[metric], (int, float)) and isinstance(network_after[metric], (int, float)):
                    if network_before[metric] != 0:
                        change = (network_after[metric] - network_before[metric]) / network_before[metric] * 100
                        # For time and queue metrics, negative values indicate improvement
                        if metric in ["avg_duration", "avg_waiting_time", "avg_waiting_count"]:
                            change = -change
                        network_improved[metric] = round(change, 2)
                    else:
                        network_improved[metric] = 0 if network_after[metric] == 0 else float('inf')
            
            improvements["network_metrics"] = network_improved
            
        elif key == "junction_metrics":
            # Junction level metrics comparison
            junction_improved = {}
            
            # Find junctions present in both datasets
            common_junctions = set(before_metrics[key].keys()) & set(after_metrics[key].keys())
            
            for junction_id in common_junctions:
                junction_before = before_metrics[key][junction_id]
                junction_after = after_metrics[key][junction_id]
                junction_metrics = {}
                
                for metric in set(junction_before.keys()) & set(junction_after.keys()):
                    if isinstance(junction_before[metric], (int, float)) and isinstance(junction_after[metric], (int, float)):
                        if junction_before[metric] != 0:
                            change = (junction_after[metric] - junction_before[metric]) / junction_before[metric] * 100
                            # For queue metrics, negative values indicate improvement
                            if metric in ["avg_queue_time", "avg_queue_length"]:
                                change = -change
                            junction_metrics[metric] = round(change, 2)
                        else:
                            junction_metrics[metric] = 0 if junction_after[metric] == 0 else float('inf')
                
                junction_improved[junction_id] = junction_metrics
            
            # Calculate average improvement rate at junction level
            if junction_improved:
                avg_improvements = {
                    "avg_queue_time_improvement": 0.0,
                    "avg_queue_length_improvement": 0.0,
                    "junction_count": len(junction_improved)
                }
                
                for junction_data in junction_improved.values():
                    if "avg_queue_time" in junction_data:
                        avg_improvements["avg_queue_time_improvement"] += junction_data["avg_queue_time"]
                    if "avg_queue_length" in junction_data:
                        avg_improvements["avg_queue_length_improvement"] += junction_data["avg_queue_length"]
                
                avg_improvements["avg_queue_time_improvement"] /= len(junction_improved)
                avg_improvements["avg_queue_length_improvement"] /= len(junction_improved)
                
                junction_improved["_average"] = {
                    k: round(v, 2) for k, v in avg_improvements.items()
                }
            
            improvements["junction_metrics"] = junction_improved
            
        elif key == "edge_metrics":
            # Edge level metrics comparison
            edge_improved = {}
            
            # Find edges present in both datasets
            common_edges = set(before_metrics[key].keys()) & set(after_metrics[key].keys())
            
            for edge_id in common_edges:
                edge_before = before_metrics[key][edge_id]
                edge_after = after_metrics[key][edge_id]
                edge_metrics = {}
                
                for metric in set(edge_before.keys()) & set(edge_after.keys()):
                    if isinstance(edge_before[metric], (int, float)) and isinstance(edge_after[metric], (int, float)):
                        if edge_before[metric] != 0:
                            change = (edge_after[metric] - edge_before[metric]) / edge_before[metric] * 100
                            # For time loss metrics, negative values indicate improvement; for speed, positive values indicate improvement
                            if metric in ["travel_time", "time_loss"]:
                                change = -change
                            edge_metrics[metric] = round(change, 2)
                        else:
                            edge_metrics[metric] = 0 if edge_after[metric] == 0 else float('inf')
                
                edge_improved[edge_id] = edge_metrics
            
            # Calculate average improvement rate at edge level
            if edge_improved:
                avg_improvements = {
                    "avg_travel_time_improvement": 0.0,
                    "avg_time_loss_improvement": 0.0,
                    "avg_speed_improvement": 0.0,
                    "edge_count": len(edge_improved)
                }
                
                for edge_data in edge_improved.values():
                    if "travel_time" in edge_data:
                        avg_improvements["avg_travel_time_improvement"] += edge_data["travel_time"]
                    if "time_loss" in edge_data:
                        avg_improvements["avg_time_loss_improvement"] += edge_data["time_loss"]
                    if "speed" in edge_data:
                        avg_improvements["avg_speed_improvement"] += edge_data["speed"]
                
                avg_improvements["avg_travel_time_improvement"] /= len(edge_improved)
                avg_improvements["avg_time_loss_improvement"] /= len(edge_improved)
                avg_improvements["avg_speed_improvement"] /= len(edge_improved)
                
                edge_improved["_average"] = {
                    k: round(v, 2) for k, v in avg_improvements.items()
                }
            
            improvements["edge_metrics"] = edge_improved
    
    # Add overall performance improvement summary
    has_network = "network_metrics" in improvements
    has_junction = "junction_metrics" in improvements and "_average" in improvements["junction_metrics"]
    has_edge = "edge_metrics" in improvements and "_average" in improvements["edge_metrics"]
    
    if has_network or has_junction or has_edge:
        overall = {}
        
        if has_network:
            overall.update({
                "travel_time_improvement": improvements["network_metrics"].get("avg_duration", 0),
                "waiting_time_improvement": improvements["network_metrics"].get("avg_waiting_time", 0)
            })
        
        if has_junction:
            overall.update({
                "queue_time_improvement": improvements["junction_metrics"]["_average"].get("avg_queue_time_improvement", 0),
                "queue_length_improvement": improvements["junction_metrics"]["_average"].get("avg_queue_length_improvement", 0)
            })
        
        if has_edge:
            overall.update({
                "edge_travel_time_improvement": improvements["edge_metrics"]["_average"].get("avg_travel_time_improvement", 0),
                "edge_time_loss_improvement": improvements["edge_metrics"]["_average"].get("avg_time_loss_improvement", 0),
                "speed_improvement": improvements["edge_metrics"]["_average"].get("avg_speed_improvement", 0)
            })
        
        improvements["_overall"] = overall
    
    # Save comparison results as JSON file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(improvements, f, ensure_ascii=False, indent=2)
    
    return output_file

@mcp.tool()
def tls_to_csv(tls_file: str, net_file: str, output_file: str = None, ctx: Context = None) -> Dict[str, Any]:
    """
    Generate CSV format signal timing from tls file
    
    Args:
        tls_file: Signal timing file path
        net_file: Network file path
        output_file: Output CSV file path, defaults to tls_phases.csv in the same directory as tls file
        
    Returns:
        Dictionary containing CSV file path
    """
    import xml.etree.ElementTree as ET
    import os
    import csv
    from tools.junction_utils import analyze_traffic_light_phases
    
    if ctx:
        ctx.info(f"Starting CSV generation from signal timing file: {tls_file}")
    
    # Check if files exist
    if not os.path.exists(tls_file):
        if ctx:
            ctx.error(f"Signal file does not exist: {tls_file}")
        return {"success": False, "message": f"Signal file does not exist: {tls_file}"}
    
    if not os.path.exists(net_file):
        if ctx:
            ctx.error(f"Network file does not exist: {net_file}")
        return {"success": False, "message": f"Network file does not exist: {net_file}"}
    
    try:
        # Parse XML file to get traffic light information
        tree = ET.parse(tls_file)
        root = tree.getroot()
        
        # Prepare CSV data
        csv_data = [["junction_id", "phase_name", "green", "yellow", "red", "offset"]]
        
        # Find all traffic lights
        tl_count = 0
        phase_count = 0
        
        # In tls file, traffic light elements can be tlLogic or direct children of additionals
        tl_logics = root.findall(".//tlLogic")
        if not tl_logics:
            tl_logics = root.findall("./tlLogic")
        
        for tl_logic in tl_logics:
            junction_id = tl_logic.get("id")
            offset = tl_logic.get("offset", "0")
            
            if ctx:
                ctx.info(f"Processing intersection: {junction_id}")
            
            # Get phase information for this traffic light
            phases_info = analyze_traffic_light_phases(net_file, tls_file, junction_id)
            
            if phases_info:
                tl_count += 1
                # Process each phase
                for i, phase in enumerate(phases_info):
                    description = phase["description"]
                    duration = phase["duration"]
                    
                    # Check if next phase is yellow
                    yellow_duration = 0
                    if i + 1 < len(phases_info):
                        next_phase = phases_info[i + 1]
                        if next_phase["description"] == "None" or (len(next_phase["allowed_lanes"]) == 0):
                            yellow_duration = next_phase["duration"]
                    
                    # Only record green phases
                    if description != "None" and len(phase["allowed_lanes"]) > 0:
                        csv_data.append([
                            junction_id,
                            description,
                            str(duration),
                            str(yellow_duration),
                            "0",  # Red time defaults to 0
                            offset
                        ])
                        phase_count += 1
        
        # Set default output filename
        if output_file is None:
            output_dir = os.path.dirname(tls_file)
            output_file = os.path.join(output_dir, "tls_phases.csv")
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Write CSV file
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(csv_data)
        
        if ctx:
            ctx.info(f"CSV file generated successfully: {output_file}")
            ctx.info(f"Processed {tl_count} intersections, {phase_count} phases")
        
        return {
            "success": True,
            "message": "CSV file generated successfully",
            "file": output_file
        }
    
    except Exception as e:
        if ctx:
            ctx.error(f"Error generating CSV file: {str(e)}")
        import traceback
        return {
            "success": False,
            "message": f"Error generating CSV file: {str(e)}",
            "traceback": traceback.format_exc()
        }

@mcp.tool()
def csv_to_tls(csv_file: str, net_file: str, output_file: str = None, ctx: Context = None) -> Dict[str, Any]:
    """
    Generate tls file from CSV format signal timing
    
    Args:
        csv_file: CSV signal timing file path
        net_file: Network file path
        output_file: Output tls file path, defaults to generated_tls.add.xml in the same directory as csv file
        
    Returns:
        Dictionary containing tls file path and status information
    """
    import os
    import csv
    import xml.dom.minidom as minidom
    import xml.etree.ElementTree as ET
    import sumolib
    
    if ctx:
        ctx.info(f"Starting signal timing generation from CSV file: {csv_file}")
    
    # Check if files exist
    if not os.path.exists(csv_file):
        if ctx:
            ctx.error(f"CSV file does not exist: {csv_file}")
        return {"success": False, "message": f"CSV file does not exist: {csv_file}"}
    
    if not os.path.exists(net_file):
        if ctx:
            ctx.error(f"Network file does not exist: {net_file}")
        return {"success": False, "message": f"Network file does not exist: {net_file}"}
    
    try:
        # Read CSV file
        csv_data = []
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)  # Skip header
            for row in reader:
                csv_data.append(row)
        
        if ctx:
            ctx.info(f"Successfully read CSV file, {len(csv_data)} rows of data")
        
        # Group by intersection ID
        junctions = {}
        for row in csv_data:
            if len(row) < 6:
                continue
                
            junction_id = row[0]
            phase_name = row[1]
            green = int(row[2])
            yellow = int(row[3])
            red = int(row[4])
            offset = int(row[5])
            
            if junction_id not in junctions:
                junctions[junction_id] = {
                    "phases": [],
                    "offset": offset
                }
            
            junctions[junction_id]["phases"].append({
                "name": phase_name,
                "green": green,
                "yellow": yellow,
                "red": red
            })
        
        # Load network using sumolib
        if ctx:
            ctx.info(f"Loading network file: {net_file}")
        net = sumolib.net.readNet(net_file)
        
        # Create tls XML file
        root = ET.Element("additional")
        
        # Create TLS ID to object mapping
        tls_dict = {}
        for tls in net._tlss:
            tls_dict[tls._id] = tls
            if ctx:
                ctx.info(f"Found traffic light: {tls._id}")
        
        for junction_id, junction_data in junctions.items():
            if ctx:
                ctx.info(f"Processing intersection: {junction_id}")
            
            # Try to get traffic light object
            if junction_id not in tls_dict:
                if ctx:
                    ctx.warning(f"Could not find traffic light information for intersection {junction_id} in the network")
                continue
            
            # Get traffic light object
            tls = tls_dict[junction_id]
            connections = tls.getConnections()
            num_links = len(connections)
            
            if ctx:
                ctx.info(f"Intersection {junction_id} has {num_links} connections")
            
            if num_links == 0:
                if ctx:
                    ctx.warning(f"Intersection {junction_id} has no controlled connections")
                continue
            
            # Create traffic light logic element
            tl_logic = ET.SubElement(root, "tlLogic")
            tl_logic.set("id", junction_id)
            tl_logic.set("type", "static")
            tl_logic.set("programID", "generated")
            tl_logic.set("offset", str(junction_data["offset"]))
            
            # Build direction to connection index mapping
            direction_map = {}
            
            # Traverse all connections, determine direction based on entry lane position
            for idx, conn in enumerate(connections):
                try:
                    inLane, outLane, linkIndex = conn
                    
                    # Get entry lane shape
                    lane_shape = inLane.getShape()
                    if len(lane_shape) < 2:
                        if ctx:
                            ctx.warning(f"Entry lane shape insufficient for connection {idx}")
                        continue
                    
                    # Calculate lane angle
                    p1, p2 = lane_shape[-2], lane_shape[-1]
                    import math
                    angle_rad = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
                    angle_deg = (math.degrees(angle_rad) + 360) % 360
                    
                    # Map angle to direction
                    if 45 <= angle_deg < 135:
                        direction = "South"
                    elif 135 <= angle_deg < 225:
                        direction = "East"
                    elif 225 <= angle_deg < 315:
                        direction = "North"
                    else:
                        direction = "West"
                    
                    # Add to mapping
                    if direction not in direction_map:
                        direction_map[direction] = []
                    direction_map[direction].append(linkIndex)
                except Exception as e:
                    if ctx:
                        ctx.error(f"Error processing connection {idx}: {str(e)}")
            
            # Create green and yellow phases for each phase
            for phase_data in junction_data["phases"]:
                # Get phase name
                phase_name = phase_data["name"]
                
                # Create default all-red state
                state_list = ['r'] * num_links
                
                # Set signal state for corresponding directions based on phase name
                for direction in ["North", "South", "East", "West"]:
                    if direction in phase_name and direction in direction_map:
                        for idx in direction_map[direction]:
                            if idx < len(state_list):
                                state_list[idx] = 'G'
                
                # Create green phase
                green_phase = ET.SubElement(tl_logic, "phase")
                green_phase.set("duration", str(phase_data["green"]))
                green_phase.set("state", "".join(state_list))
                
                # If yellow time exists, create yellow phase
                if phase_data["yellow"] > 0:
                    yellow_list = state_list.copy()
                    for i, s in enumerate(yellow_list):
                        if s == 'G':
                            yellow_list[i] = 'y'
                    
                    yellow_phase = ET.SubElement(tl_logic, "phase")
                    yellow_phase.set("duration", str(phase_data["yellow"]))
                    yellow_phase.set("state", "".join(yellow_list))
        
        # Set default output filename
        if output_file is None:
            output_dir = os.path.dirname(csv_file)
            output_file = os.path.join(output_dir, "generated_tls.add.xml")
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Prettify XML and save
        xml_str = ET.tostring(root, encoding='utf-8')
        dom = minidom.parseString(xml_str)
        pretty_xml = dom.toprettyxml(indent="    ")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(pretty_xml)
        
        if ctx:
            ctx.info(f"tls file generated successfully: {output_file}")
            ctx.info(f"Processed {len(junctions)} intersections")
        
        return {
            "success": True,
            "message": "tls file generated successfully",
            "file": output_file,
            "stats": {
                "junction_count": len(junctions)
            }
        }
    
    except Exception as e:
        if ctx:
            ctx.error(f"Error generating tls file: {str(e)}")
        import traceback
        return {
            "success": False, 
            "message": f"Error generating tls file: {str(e)}",
            "traceback": traceback.format_exc()
        }

if __name__ == "__main__":
    mcp.run(transport="sse", host = "127.0.0.1", port = 8016)