import asyncio
import contextlib
import io
import os
import time
import subprocess
from typing import Any, Dict, List, Tuple

import osmnx as ox
import requests
from fastmcp import FastMCP, Context

# 设置环境变量
os.environ["SUMO_HOME"] = "D:\Program Files\SUMO"

# ────────────────────────────────────────────────────────────────────────────────
# 创建辅助工具服务器
# ────────────────────────────────────────────────────────────────────────────────
ox.settings.log_console = False
auxiliary_mcp = FastMCP(name="SUMO_Auxiliary_Tools")

# ────────────────────────────────────────────────────────────────────────────────
# TOOL 1: Download OSM by place name
# ────────────────────────────────────────────────────────────────────────────────
@auxiliary_mcp.tool()
async def osm_download_by_place(
    place_name: str,
    simulation_name: str = "sim1",
    ctx: Context = None,
) -> Dict[str, Any]:
    """Download OSM data by place name and save to simulation directory.
    
    Args:
        place_name: Place name, e.g. "West District, Beijing, China"
        simulation_name: Simulation name, used as subfolder name
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

# ────────────────────────────────────────────────────────────────────────────────
# TOOL 2: Generate Random Trips
# ────────────────────────────────────────────────────────────────────────────────
@auxiliary_mcp.tool()
async def generate_random_trips(
    net_file: str,
    output_dir: str = None,
    trip_count: int = 100,
    begin_time: int = 0,
    end_time: int = 3600,
    period: float = 1.0,
    min_distance: float = 0.0,
    max_distance: float = None,
    vehicle_class: str = "passenger",
    prefix: str = "",
    seed: int = 42,
    route_file: str = None,
    advanced_options: Dict[str, Any] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """基于SUMO的randomTrips.py脚本生成随机行程和路线
    
    参数:
    net_file: SUMO网络文件路径
    output_dir: 输出目录，默认为当前目录
    trip_count: 生成的行程数量
    begin_time: 开始时间（秒）
    end_time: 结束时间（秒）
    period: 车辆生成间隔（秒）
    min_distance: 最小行程距离（米）
    max_distance: 最大行程距离（米），默认不限制
    vehicle_class: 车辆类型
    prefix: 行程ID前缀
    seed: 随机数种子
    route_file: 如果提供，则使用duarouter生成路线文件
    advanced_options: 其他randomTrips.py支持的高级选项
    """
    
    if not os.path.exists(net_file):
        if ctx:
            ctx.error(f"网络文件不存在: {net_file}")
        return {"success": False, "message": f"网络文件不存在: {net_file}"}
    
    # 设置基本目录结构
    if output_dir is None:
        output_dir = os.path.dirname(net_file)
    os.makedirs(output_dir, exist_ok=True)
    
    # 设置输出文件路径
    trip_file = os.path.join(output_dir, f"{prefix}trips.xml")
    
    # 构建基本命令
    cmd = [
        "python", os.path.join(os.environ.get("SUMO_HOME", ""), "tools", "randomTrips.py"),
        "-n", net_file,
        "-o", trip_file,
        "-b", str(begin_time),
        "-e", str(end_time),
        "--seed", str(seed),
        "-p", str(period),
        "--min-distance", str(min_distance),
        "--prefix", prefix,
        "--vehicle-class", vehicle_class
    ]
    
    # 添加可选参数
    if max_distance is not None:
        cmd.extend(["--max-distance", str(max_distance)])
    
    if route_file is not None:
        cmd.extend(["-r", route_file])
    
    # 添加高级选项
    if advanced_options:
        for key, value in advanced_options.items():
            if value is True:
                cmd.append(f"--{key}")
            elif value is not False and value is not None:
                cmd.extend([f"--{key}", str(value)])
    
    # 执行命令
    if ctx:
        ctx.info(f"执行命令: {' '.join(cmd)}")
    
    try:
        process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        
        if process.returncode != 0:
            if ctx:
                ctx.error(f"randomTrips.py执行失败: {process.stderr}")
            return {
                "success": False,
                "message": f"randomTrips.py执行失败，返回码: {process.returncode}",
                "stderr": process.stderr,
                "stdout": process.stdout
            }
        
        result = {
            "success": True,
            "message": "随机行程生成成功",
            "files": {
                "trip_file": trip_file
            }
        }
        
        if route_file is not None:
            result["files"]["route_file"] = route_file
            
        return result
        
    except Exception as e:
        if ctx:
            ctx.error(f"执行随机行程生成异常: {str(e)}")
        import traceback
        return {
            "success": False,
            "message": f"执行异常: {str(e)}",
            "traceback": traceback.format_exc()
        }

# ────────────────────────────────────────────────────────────────────────────────
# TOOL 3: TLS Cycle Adaptation
# ────────────────────────────────────────────────────────────────────────────────
@auxiliary_mcp.tool()
async def tls_cycle_adaptation(
    # 输入选项
    net_file: str,
    route_files: str,
    begin: float = None,
    
    # 输出选项
    output_file: str = "tlsAdaptation.add.xml",
    
    # 处理选项
    yellow_time: int = 4,
    all_red: int = 0,
    lost_time: int = 4,
    min_green: int = 4,
    green_filter_time: int = 0,
    min_cycle: int = 20,
    max_cycle: int = 120,
    existing_cycle: bool = False,
    write_critical_flows: bool = False,
    program: str = "a",
    saturation_headway: float = 2,
    restrict_cyclelength: bool = False,
    unified_cycle: bool = False,
    sorted: bool = False,
    skip: str = "",
    verbose: bool = False,
    
    ctx: Context = None
) -> Dict[str, Any]:
    """使用tlsCycleAdaptation.py优化交通信号灯的周期长度和绿灯时间
    
    参数:
    # 输入选项
    net_file: 网络文件(必需)
    route_files: 路由文件，多个文件用逗号分隔(必需)
    begin: 优化周期的开始时间(秒)
    
    # 输出选项
    output_file: 定义输出文件名
    
    # 处理选项
    yellow_time: 黄灯时间
    all_red: 每个周期的全红时间
    lost_time: 每个相位启动和清空的损失时间
    min_green: 没有交通流量时的最小绿灯时间
    green_filter_time: 计算关键流量时，不计算绿灯时间低于INT的相位
    min_cycle: 最小周期长度
    max_cycle: 最大周期长度
    existing_cycle: 使用现有的周期长度
    write_critical_flows: 打印每个交通灯和相位的关键流量
    program: 使用此程序ID保存新定义
    saturation_headway: 计算小时饱和流量的饱和车头时距(秒)
    restrict_cyclelength: 将最大周期长度限制为给定值
    unified_cycle: 使用计算出的最大周期长度作为所有交叉口的周期长度
    sorted: 假设路由文件已排序(提前中止读取)
    skip: 要跳过的交通灯ID，用逗号分隔
    verbose: 显示详细信息
    """
    
    cmd = [
        "python",
        os.path.join(os.environ.get("SUMO_HOME", ""), "tools", "tlsCycleAdaptation.py"),
        "-n", net_file,
        "-r", route_files,
        "-o", output_file,
        "-y", str(yellow_time),
        "-a", str(all_red),
        "-l", str(lost_time),
        "-g", str(min_green),
        "--green-filter-time", str(green_filter_time),
        "--min-cycle", str(min_cycle),
        "--max-cycle", str(max_cycle),
        "-p", program,
        "-H", str(saturation_headway),
        "--skip", skip
    ]
    
    if begin is not None:
        cmd.extend(["-b", str(begin)])
    if existing_cycle:
        cmd.append("-e")
    if write_critical_flows:
        cmd.append("--write-critical-flows")
    if restrict_cyclelength:
        cmd.append("-R")
    if unified_cycle:
        cmd.append("-u")
    if sorted:
        cmd.append("--sorted")
    if verbose:
        cmd.append("-v")
    
    if ctx:
        ctx.info(f"执行命令: {' '.join(cmd)}")
    
    process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    result = {
        "success": process.returncode == 0,
        "message": "交通信号灯周期优化成功" if process.returncode == 0 else "交通信号灯周期优化失败",
        "stdout": process.stdout,
        "stderr": process.stderr
    }
    
    if os.path.exists(output_file):
        result["output_file"] = output_file
    
    return result

# ────────────────────────────────────────────────────────────────────────────────
# TOOL 4: TLS Coordinator
# ────────────────────────────────────────────────────────────────────────────────
@auxiliary_mcp.tool()
async def tls_coordinator(
    # 输入选项
    net_file: str,
    route_file: str,
    additional_file: str = None,
    
    # 输出选项
    output_file: str = "tlsOffsets.add.xml",
    
    # 处理选项
    verbose: bool = False,
    ignore_priority: bool = False,
    speed_factor: float = 0.8,
    evaluate: bool = False,
    
    ctx: Context = None
) -> Dict[str, Any]:
    """使用tlsCoordinator.py协调交通信号灯的偏移量，创建绿波
    
    参数:
    # 输入选项
    net_file: 定义网络文件(必需)
    route_file: 定义输入路由文件(必需)
    additional_file: 定义要协调的替换交通信号灯计划
    
    # 输出选项
    output_file: 定义输出文件名
    
    # 处理选项
    verbose: 显示详细信息
    ignore_priority: 在排序TLS对时忽略道路优先级
    speed_factor: 车辆速度与速度限制的平均比率
    evaluate: 运行场景并打印持续时间统计信息
    """
    
    cmd = [
        "python",
        os.path.join(os.environ.get("SUMO_HOME", ""), "tools", "tlsCoordinator.py"),
        "-n", net_file,
        "-r", route_file,
        "-o", output_file,
        "--speed-factor", str(speed_factor)
    ]
    
    if additional_file:
        cmd.extend(["-a", additional_file])
    if verbose:
        cmd.append("-v")
    if ignore_priority:
        cmd.append("-i")
    if evaluate:
        cmd.append("-e")
    
    if ctx:
        ctx.info(f"执行命令: {' '.join(cmd)}")
    
    process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    result = {
        "success": process.returncode == 0,
        "message": "交通信号灯协调成功" if process.returncode == 0 else "交通信号灯协调失败",
        "stdout": process.stdout,
        "stderr": process.stderr
    }
    
    if os.path.exists(output_file):
        result["output_file"] = output_file
    
    return result

# ────────────────────────────────────────────────────────────────────────────────
# TOOL 5: Create SUMO configuration file
# ────────────────────────────────────────────────────────────────────────────────
@auxiliary_mcp.tool()
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
                "run_cmd": f"{'sumo' if gui else 'sumo'} -c {output_file}"
            }
        }
    except Exception as e:
        if ctx:
            ctx.error(f"Failed to create configuration: {e}")
        return {"success": False, "message": f"Failed to create configuration: {e}"}

# ────────────────────────────────────────────────────────────────────────────────
# TOOL 6: Show picture to user
# ────────────────────────────────────────────────────────────────────────────────
@auxiliary_mcp.tool()
async def show_picture(
    image_path: str,
    title: str = "图片",
    description: str = "",
    ctx: Context = None,
) -> Dict[str, Any]:
    """向用户展示图片。
    
    Args:
        image_path: 图片文件路径
        title: 图片标题
        description: 图片描述
        ctx: Context object for logging
    """
    # 检查图片文件是否存在
    if not os.path.exists(image_path):
        if ctx:
            ctx.error(f"图片文件不存在: {image_path}")
        return {"success": False, "message": f"图片文件不存在: {image_path}"}
    
    # 检查文件是否为图片格式
    valid_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg']
    file_ext = os.path.splitext(image_path)[1].lower()
    if file_ext not in valid_extensions:
        if ctx:
            ctx.error(f"不支持的图片格式: {file_ext}")
        return {"success": False, "message": f"不支持的图片格式: {file_ext}"}
    
    # 获取图片的绝对路径
    abs_image_path = os.path.abspath(image_path)
    
    # 通知前端显示图片
    try:
        # 发送HTTP请求到前端后端接口，通知显示图片
        import requests
        frontend_backend_url = "http://localhost:5000/api/show_picture"
        
        payload = {
            "image_path": abs_image_path,
            "title": title,
            "description": description,
            "timestamp": time.time()
        }
        
        response = requests.post(frontend_backend_url, json=payload, timeout=5)
        
        if response.status_code == 200:
            if ctx:
                ctx.info(f"成功向用户展示图片: {title}")
                ctx.info(f"图片路径: {abs_image_path}")
                if description:
                    ctx.info(f"图片描述: {description}")
            
            return {
                "success": True,
                "message": f"成功向用户展示图片: {title}",
                "data": {
                    "image_path": abs_image_path,
                    "title": title,
                    "description": description
                }
            }
        else:
            if ctx:
                ctx.warning(f"前端接口调用失败: {response.status_code}")
            return {
                "success": False,
                "message": "前端接口调用失败，但图片路径已记录",
                "data": {
                    "image_path": abs_image_path,
                    "title": title,
                    "description": description
                }
            }
    
    except Exception as e:
        if ctx:
            ctx.warning(f"无法连接到前端接口: {str(e)}")
        
        # 即使前端接口调用失败，也返回成功，因为图片路径信息已经提供
        return {
            "success": True,
            "message": f"图片准备就绪: {title}",
            "data": {
                "image_path": abs_image_path,
                "title": title,
                "description": description
            }
        }

# ────────────────────────────────────────────────────────────────────────────────
# TOOL 7: Run simulation for fixed-time control, Webster control, Greenwave control or Actuated control
# ────────────────────────────────────────────────────────────────────────────────
@auxiliary_mcp.tool()
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
# TOOL 8: Compare multiple simulation results' performance metrics and generate charts
# ────────────────────────────────────────────────────────────────────────────────
@auxiliary_mcp.tool()
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
# 辅助工具资源
# ────────────────────────────────────────────────────────────────────────────────
@auxiliary_mcp.resource("data://auxiliary/config")
def get_auxiliary_config() -> Dict[str, Any]:
    """获取辅助工具配置信息"""
    return {
        "version": "1.0.0",
        "name": "SUMO Auxiliary Tools",
        "description": "辅助SUMO工具包，包含OSM下载、随机行程生成、交通信号灯优化等功能",
        "tools": [
            "osm_download_by_place",
            "generate_random_trips", 
            "tls_cycle_adaptation",
            "tls_coordinator",
            "create_sumo_config",
            "show_picture",
            "run_simulation",
            "compare_simulation_results"
        ]
    }

@auxiliary_mcp.resource("data://auxiliary/help")
def get_auxiliary_help() -> Dict[str, str]:
    """获取辅助工具帮助信息"""
    return {
        "osm_download_by_place": "根据地名下载OSM地图数据",
        "generate_random_trips": "生成随机交通行程",
        "tls_cycle_adaptation": "优化交通信号灯周期长度",
        "tls_coordinator": "协调交通信号灯偏移量，创建绿波",
        "create_sumo_config": "生成SUMO仿真配置文件",
        "show_picture": "向用户展示图片",
        "run_simulation": "运行SUMO交通仿真，支持固定配时、感应控制、Webster优化、绿波协调四种控制方式",
        "compare_simulation_results": "对比多个仿真结果的性能指标，生成雷达图和数据表"
    }

# 如果直接运行此文件，启动辅助工具服务器
if __name__ == "__main__":
    print("启动SUMO辅助工具服务器...")
    auxiliary_mcp.run(transport="sse", host="127.0.0.1", port=8017)