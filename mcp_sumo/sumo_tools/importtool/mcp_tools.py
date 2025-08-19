#!/usr/bin/env python3
"""
SUMO导入工具模块 - 独立的FastMCP服务器
处理各种外部数据格式到SUMO格式的转换和导入功能
"""

import os
import subprocess
from typing import Dict, Any, List

from fastmcp import FastMCP, Context

# 设置环境变量
os.environ["SUMO_HOME"] = "D:\Program Files\SUMO"

# ────────────────────────────────────────────────────────────────────────────────
# 创建导入工具服务器
# ────────────────────────────────────────────────────────────────────────────────
importtool_mcp = FastMCP(name="SUMO_ImportTool_Tools")

# ────────────────────────────────────────────────────────────────────────────────
# TOOL 1: CityBrain流量导入
# ────────────────────────────────────────────────────────────────────────────────
@importtool_mcp.tool()
async def citybrain_flow_import(
        flow_file: str,
        output_file: str,
        prefix: str = "",
        ctx: Context = None
    ) -> Dict[str, Any]:
        """基于SUMO的citybrain_flow.py脚本导入CityBrains交通需求
        
        参数:
        flow_file: CityBrains流量文件路径
        output_file: 输出的SUMO路由文件路径
        prefix: 生成的流量ID前缀
        """
        
        cmd = [
            "python",
            os.path.join(os.environ.get("SUMO_HOME", ""), "tools", "import", "citybrain", "citybrain_flow.py"),
            "-f", flow_file,
            "-o", output_file
        ]
        
        if prefix:
            cmd.extend(["-p", prefix])
        
        if ctx:
            ctx.info(f"执行命令: {' '.join(cmd)}")
        
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        return {
            "success": process.returncode == 0,
            "message": "CityBrains流量导入成功" if process.returncode == 0 else "CityBrains流量导入失败",
            "stdout": process.stdout,
            "stderr": process.stderr,
            "file": output_file if os.path.exists(output_file) else None
        }

# ────────────────────────────────────────────────────────────────────────────────
# TOOL 2: CityBrain信息步骤导入
# ────────────────────────────────────────────────────────────────────────────────
@importtool_mcp.tool()
async def citybrain_infostep_import(
        info_file: str,
        output_file: str,
        lastpos: bool = False,
        length: float = 4,
        mingap: float = 1,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """基于SUMO的citybrain_infostep.py脚本导入CityBrains步进信息
        
        参数:
        info_file: CityBrains步进信息文件路径
        output_file: 输出的SUMO路由文件路径
        lastpos: 是否使用departPos 'last'来包含更多车辆
        length: 默认车辆长度
        mingap: 默认车辆最小间隙
        """
        
        cmd = [
            "python",
            os.path.join(os.environ.get("SUMO_HOME", ""), "tools", "import", "citybrain", "citybrain_infostep.py"),
            "-i", info_file,
            "-o", output_file,
            "--length", str(length),
            "--mingap", str(mingap)
        ]
        
        if lastpos:
            cmd.append("-l")
        
        if ctx:
            ctx.info(f"执行命令: {' '.join(cmd)}")
        
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        return {
            "success": process.returncode == 0,
            "message": "CityBrains步进信息导入成功" if process.returncode == 0 else "CityBrains步进信息导入失败",
            "stdout": process.stdout,
            "stderr": process.stderr,
            "file": output_file if os.path.exists(output_file) else None
        }

# ────────────────────────────────────────────────────────────────────────────────
# TOOL 3: CityBrain道路导入
# ────────────────────────────────────────────────────────────────────────────────
@importtool_mcp.tool()
async def citybrain_road_import(
        net_file: str,
        output: str = "net.net.xml",
        prefix: str = "net",
        junction_type: str = "allway_stop",
        temp_network: str = "tmp.net.xml",
        ignore_connections: bool = False,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """基于SUMO的citybrain_road.py脚本导入CityBrains路网
        
        参数:
        net_file: CityBrains网络文件路径
        output: 输出的SUMO网络文件名
        prefix: 平面XML文件的前缀
        junction_type: 没有交通信号灯的路口的默认类型
        temp_network: 中间网络文件
        ignore_connections: 是否使用netconvert猜测的连接而不是指定的连接
        """
        
        cmd = [
            "python",
            os.path.join(os.environ.get("SUMO_HOME", ""), "tools", "import", "citybrain", "citybrain_road.py"),
            "-n", net_file,
            "-o", output,
            "-p", prefix,
            "-j", junction_type,
            "-t", temp_network
        ]
        
        if ignore_connections:
            cmd.append("-x")
        
        if ctx:
            ctx.info(f"执行命令: {' '.join(cmd)}")
        
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        return {
            "success": process.returncode == 0,
            "message": "CityBrains路网导入成功" if process.returncode == 0 else "CityBrains路网导入失败",
            "stdout": process.stdout,
            "stderr": process.stderr,
            "file": output if os.path.exists(output) else None
        }

# ────────────────────────────────────────────────────────────────────────────────
# TOOL 4: GTFS到FCD导入
# ────────────────────────────────────────────────────────────────────────────────
@importtool_mcp.tool()
async def gtfs2fcd_import(
        gtfs: str,
        date: str,
        region: str = "gtfs",
        fcd: str = None,
        gpsdat: str = None,
        modes: str = None,
        vtype_output: str = "vtypes.xml",
        verbose: bool = False,
        begin: int = 0,
        end: int = 86400,
        bbox: str = None,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """基于SUMO的gtfs2fcd.py脚本将GTFS数据转换为FCD轨迹
        
        参数:
        gtfs: GTFS压缩文件路径
        date: 要导入的日期，格式：'YYYYMMDD'
        region: 要处理的区域
        fcd: 写入/读取生成的FCD文件的目录
        gpsdat: 写入/读取生成的gpsdat文件的目录
        modes: 要导入的模式列表，逗号分隔
        vtype_output: 写入生成的车辆类型的文件
        verbose: 是否显示详细信息
        begin: 导出的开始时间
        end: 导出的结束时间
        bbox: 用于过滤GTFS数据的边界框，格式：W,S,E,N
        """
        
        cmd = [
            "python",
            os.path.join(os.environ.get("SUMO_HOME", ""), "tools", "import", "gtfs", "gtfs2fcd.py"),
            "--gtfs", gtfs,
            "--date", date,
            "--region", region,
            "--vtype-output", vtype_output,
            "--begin", str(begin),
            "--end", str(end)
        ]
        
        if fcd:
            cmd.extend(["--fcd", fcd])
        
        if gpsdat:
            cmd.extend(["--gpsdat", gpsdat])
        
        if modes:
            cmd.extend(["--modes", modes])
        
        if verbose:
            cmd.append("-v")
        
        if bbox:
            cmd.extend(["--bbox", bbox])
        
        if ctx:
            ctx.info(f"执行命令: {' '.join(cmd)}")
        
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        return {
            "success": process.returncode == 0,
            "message": "GTFS数据转换成功" if process.returncode == 0 else "GTFS数据转换失败",
            "stdout": process.stdout,
            "stderr": process.stderr,
            "fcd_dir": fcd,
            "gpsdat_dir": gpsdat,
            "vtype_file": vtype_output if os.path.exists(vtype_output) else None
        }

# ────────────────────────────────────────────────────────────────────────────────
# TOOL 5: GTFS到公共交通导入
# ────────────────────────────────────────────────────────────────────────────────
@importtool_mcp.tool()
async def gtfs2pt_import(
        gtfs: str,
        date: str,
        network: str,
        region: str = "gtfs",
        route_output: str = None,
        additional_output: str = None,
        duration: int = 10,
        bus_stop_length: float = 13,
        train_stop_length: float = 110,
        tram_stop_length: float = 60,
        center_stops: bool = False,
        skip_access: bool = False,
        sort: bool = False,
        stops: str = None,
        hrtime: bool = False,
        fcd: str = None,
        gpsdat: str = None,
        modes: str = None,
        vtype_output: str = "vtypes.xml",
        verbose: bool = False,
        begin: int = 0,
        end: int = 86400,
        bbox: str = None,
        network_split: str = None,
        network_split_vclass: bool = False,
        warn_unmapped: bool = False,
        mapperlib: str = "lib/fcd-process-chain-2.2.2.jar",
        map_output: str = None,
        map_output_config: str = "conf/output_configuration_template.xml",
        map_input_config: str = "conf/input_configuration_template.xml",
        map_parameter: str = "conf/parameters_template.xml",
        poly_output: str = None,
        fill_gaps: float = 5000,
        skip_fcd: bool = False,
        skip_map: bool = False,
        osm_routes: str = None,
        warning_output: str = None,
        dua_repair_output: str = None,
        repair: bool = False,
        min_stops: int = 1,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """基于SUMO的gtfs2pt.py脚本将GTFS数据映射到给定网络，生成路线、站点和车辆
        
        参数:
        gtfs: GTFS压缩文件路径
        date: 要导入的日期，格式：'YYYYMMDD'
        network: 使用的SUMO网络
        region: 要处理的区域
        route_output: 写入生成的公共交通车辆的文件
        additional_output: 写入生成的公共交通站点和路线的文件
        duration: 在站点等待的最小时间
        bus_stop_length: 公交车站的长度
        train_stop_length: 火车站的长度
        tram_stop_length: 电车站的长度
        center_stops: 使用站点位置作为中心而不是前端
        skip_access: 不创建访问链接
        sort: 对输出文件进行排序
        stops: 包含预定义站点位置的文件
        hrtime: 以h:m:s格式写入时间
        fcd: 写入/读取生成的FCD文件的目录
        gpsdat: 写入/读取生成的gpsdat文件的目录
        modes: 要导入的模式列表，逗号分隔
        vtype_output: 写入生成的车辆类型的文件
        verbose: 是否显示详细信息
        begin: 导出的开始时间
        end: 导出的结束时间
        bbox: 用于过滤GTFS数据的边界框，格式：W,S,E,N
        network_split: 写入生成的网络的目录
        network_split_vclass: 使用允许的vclass而不是边缘类型来分割网络
        warn_unmapped: 警告未映射的路线
        mapperlib: 要使用的映射库
        map_output: 写入生成的映射文件的目录
        map_output_config: 映射库的输出配置模板
        map_input_config: 映射库的输入配置模板
        map_parameter: 映射库的参数模板
        poly_output: 写入生成的多边形文件的文件
        fill_gaps: 站点之间的最大距离
        skip_fcd: 跳过生成fcd数据
        skip_map: 跳过网络映射
        osm_routes: osm路线文件
        warning_output: 写入来自gtfs的未映射元素的文件
        dua_repair_output: 写入有错误的osm路线的文件
        repair: 修复osm路线
        min_stops: 导入的公共交通线路必须具有的最小站点数
        """
        
        cmd = [
            "python",
            os.path.join(os.environ.get("SUMO_HOME", ""), "tools", "import", "gtfs", "gtfs2pt.py"),
            "--gtfs", gtfs,
            "--date", date,
            "--network", network,
            "--region", region,
            "--duration", str(duration),
            "--bus-stop-length", str(bus_stop_length),
            "--train-stop-length", str(train_stop_length),
            "--tram-stop-length", str(tram_stop_length),
            "--begin", str(begin),
            "--end", str(end),
            "--min-stops", str(min_stops),
            "--fill-gaps", str(fill_gaps),
            "--mapperlib", mapperlib
        ]
        
        if route_output:
            cmd.extend(["--route-output", route_output])
        if additional_output:
            cmd.extend(["--additional-output", additional_output])
        if center_stops:
            cmd.append("--center-stops")
        if skip_access:
            cmd.append("--skip-access")
        if sort:
            cmd.append("--sort")
        if stops:
            cmd.extend(["--stops", stops])
        if hrtime:
            cmd.append("-H")
        if fcd:
            cmd.extend(["--fcd", fcd])
        if gpsdat:
            cmd.extend(["--gpsdat", gpsdat])
        if modes:
            cmd.extend(["--modes", modes])
        if vtype_output:
            cmd.extend(["--vtype-output", vtype_output])
        if verbose:
            cmd.append("-v")
        if bbox:
            cmd.extend(["--bbox", bbox])
        if network_split:
            cmd.extend(["--network-split", network_split])
        if network_split_vclass:
            cmd.append("--network-split-vclass")
        if warn_unmapped:
            cmd.append("--warn-unmapped")
        if map_output:
            cmd.extend(["--map-output", map_output])
        if map_output_config:
            cmd.extend(["--map-output-config", map_output_config])
        if map_input_config:
            cmd.extend(["--map-input-config", map_input_config])
        if map_parameter:
            cmd.extend(["--map-parameter", map_parameter])
        if poly_output:
            cmd.extend(["--poly-output", poly_output])
        if skip_fcd:
            cmd.append("--skip-fcd")
        if skip_map:
            cmd.append("--skip-map")
        if osm_routes:
            cmd.extend(["--osm-routes", osm_routes])
        if warning_output:
            cmd.extend(["--warning-output", warning_output])
        if dua_repair_output:
            cmd.extend(["--dua-repair-output", dua_repair_output])
        if repair:
            cmd.append("--repair")
        
        if ctx:
            ctx.info(f"执行命令: {' '.join(cmd)}")
        
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        result = {
            "success": process.returncode == 0,
            "message": "GTFS数据映射成功" if process.returncode == 0 else "GTFS数据映射失败",
            "stdout": process.stdout,
            "stderr": process.stderr
        }
        
        # 添加输出文件信息
        if route_output is None:
            route_output = region + "_pt_vehicles.add.xml"
        if additional_output is None:
            additional_output = region + "_pt_stops.add.xml"
        if warning_output is None:
            warning_output = region + "_missing.xml"
        
        if os.path.exists(route_output):
            result["route_file"] = route_output
        if os.path.exists(additional_output):
            result["additional_file"] = additional_output
        if os.path.exists(warning_output):
            result["warning_file"] = warning_output
        if os.path.exists(vtype_output):
            result["vtype_file"] = vtype_output
        if poly_output and os.path.exists(poly_output):
            result["poly_file"] = poly_output
            
        return result

# ────────────────────────────────────────────────────────────────────────────────
# TOOL 6: Vissim路线解析
# ────────────────────────────────────────────────────────────────────────────────
@importtool_mcp.tool()
async def vissim_parse_routes(
        vissim_net: str,
        output: str = "out",
        edgemap: str = None,
        seed: int = 42,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """基于SUMO的vissim_parseRoutes.py脚本从VISSIM网络解析路线
        
        参数:
        vissim_net: VISSIM网络文件
        output: 输出文件名前缀
        edgemap: 重命名边的边名映射（格式：orig1:renamed1,orig2:renamed2,...）
        seed: 随机种子
        """
        
        cmd = [
            "python",
            os.path.join(os.environ.get("SUMO_HOME", ""), "tools", "import", "vissim", "vissim_parseRoutes.py"),
            vissim_net,
            "--output", output,
            "--seed", str(seed)
        ]
        
        if edgemap:
            cmd.extend(["--edgemap", edgemap])
        
        if ctx:
            ctx.info(f"执行命令: {' '.join(cmd)}")
        
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        flows_file = output + ".flows.xml"
        routes_file = output + ".rou.xml"
        
        return {
            "success": process.returncode == 0,
            "message": "VISSIM路线解析成功" if process.returncode == 0 else "VISSIM路线解析失败",
            "stdout": process.stdout,
            "stderr": process.stderr,
            "flows_file": flows_file if os.path.exists(flows_file) else None,
            "routes_file": routes_file if os.path.exists(routes_file) else None
        }

# ────────────────────────────────────────────────────────────────────────────────
# TOOL 7: Visum边缘类型转换
# ────────────────────────────────────────────────────────────────────────────────
@importtool_mcp.tool()
async def visum_convert_edge_types(
        visum_net: str,
        output: str,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """基于SUMO的visum_convertEdgeTypes.py脚本将VISUM边类型定义转换为SUMO表示
        
        参数:
        visum_net: VISUM网络文件
        output: 输出的XML文件
        """
        
        cmd = [
            "python",
            os.path.join(os.environ.get("SUMO_HOME", ""), "tools", "import", "visum", "visum_convertEdgeTypes.py"),
            visum_net,
            output
        ]
        
        if ctx:
            ctx.info(f"执行命令: {' '.join(cmd)}")
        
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        return {
            "success": process.returncode == 0,
            "message": "VISUM边类型转换成功" if process.returncode == 0 else "VISUM边类型转换失败",
            "stdout": process.stdout,
            "stderr": process.stderr,
            "file": output if os.path.exists(output) else None
        }

# ────────────────────────────────────────────────────────────────────────────────
# TOOL 8: DXF到JuPedSim导入
# ────────────────────────────────────────────────────────────────────────────────
@importtool_mcp.tool()
async def dxf2jupedsim_import(
        file: str,
        output: str = None,
        test: bool = False,
        walkable_layer: str = "walkable_areas",
        obstacle_layer: str = "obstacles",
        walkable_color: str = "179,217,255",
        obstacle_color: str = "255,204,204",
        sumo_layer: int = 0,
        projection: str = "EPSG:32633",
        ctx: Context = None
    ) -> Dict[str, Any]:
        """基于SUMO的dxf2jupedsim.py脚本将DXF文件转换为JuPedSim多边形
        
        参数:
        file: 要读取的DXF文件
        output: 多边形输出文件名
        test: 写入DXF测试文件并退出
        walkable_layer: 包含可行走区域的DXF图层名称
        obstacle_layer: 包含障碍物的DXF图层名称
        walkable_color: 定义可行走区域的多边形颜色
        obstacle_color: 定义障碍物的多边形颜色
        sumo_layer: 用于渲染定义可行走区域的多边形的SUMO图层
        projection: 用于转换回地理坐标的EPSG代码或投影字符串
        """
        
        cmd = [
            "python",
            os.path.join(os.environ.get("SUMO_HOME", ""), "tools", "import", "dxf", "dxf2jupedsim.py"),
            file,
            "--walkable-layer", walkable_layer,
            "--obstacle-layer", obstacle_layer,
            "--walkable-color", walkable_color,
            "--obstacle-color", obstacle_color,
            "--sumo-layer", str(sumo_layer),
            "--projection", projection
        ]
        
        if output:
            cmd.extend(["--output", output])
        
        if test:
            cmd.append("--test")
        
        if ctx:
            ctx.info(f"执行命令: {' '.join(cmd)}")
        
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if output is None:
            output = file[:-3] + "add.xml"
        
        return {
            "success": process.returncode == 0,
            "message": "DXF转换为JuPedSim多边形成功" if process.returncode == 0 else "DXF转换为JuPedSim多边形失败",
            "stdout": process.stdout,
            "stderr": process.stderr,
            "file": output if os.path.exists(output) else None
        }

# ────────────────────────────────────────────────────────────────────────────────
# 导入工具资源
# ────────────────────────────────────────────────────────────────────────────────
@importtool_mcp.resource("data://importtool/config")
def get_importtool_config() -> Dict[str, Any]:
    """获取导入工具配置信息"""
    return {
        "version": "1.0.0",
        "name": "SUMO Import Tools",
        "description": "SUMO导入工具包，支持多种外部数据格式到SUMO格式的转换",
        "tools": [
            "citybrain_flow_import",
            "citybrain_infostep_import",
            "citybrain_road_import",
            "gtfs2fcd_import",
            "gtfs2pt_import",
            "vissim_parse_routes",
            "visum_convert_edge_types",
            "dxf2jupedsim_import"
        ],
        "supported_formats": [
            "CityBrain格式",
            "GTFS公交数据",
            "Vissim格式",
            "Visum格式",
            "DXF格式",
            "OpenDrive格式"
        ],
        "import_categories": [
            "交通流量数据",
            "公共交通数据",
            "道路网络数据",
            "仿真模型数据",
            "行人仿真数据"
        ]
    }

@importtool_mcp.resource("data://importtool/help")
def get_importtool_help() -> Dict[str, str]:
    """获取导入工具帮助信息"""
    return {
        "citybrain_flow_import": "导入CityBrain交通流量数据，转换为SUMO路由格式",
        "citybrain_infostep_import": "导入CityBrain信息步骤数据，用于交通分析",
        "citybrain_road_import": "导入CityBrain道路网络数据，转换为SUMO网络格式",
        "gtfs2fcd_import": "将GTFS公交数据转换为FCD（浮动车数据）轨迹格式",
        "gtfs2pt_import": "将GTFS公交数据转换为SUMO公共交通路线和站点",
        "vissim_parse_routes": "解析Vissim路由文件并转换为SUMO兼容格式",
        "visum_convert_edge_types": "将Visum道路类型定义转换为SUMO边缘类型",
        "dxf2jupedsim_import": "将DXF格式的建筑图纸转换为JuPedSim行人仿真器格式"
    }

@importtool_mcp.resource("data://importtool/examples")
def get_importtool_examples() -> Dict[str, Any]:
    """获取导入工具使用示例"""
    return {
        "citybrain_import": {
            "description": "CityBrain数据导入",
            "tools": ["citybrain_flow_import", "citybrain_road_import"],
            "parameters": {
                "flow_file": "citybrain_flow.json",
                "road_file": "citybrain_road.json",
                "output_file": "sumo_routes.rou.xml"
            }
        },
        "public_transport": {
            "description": "公共交通数据导入",
            "tools": ["gtfs2fcd_import", "gtfs2pt_import"],
            "parameters": {
                "gtfs_file": "gtfs_data.zip",
                "net_file": "network.net.xml",
                "output_routes": "pt_routes.rou.xml",
                "output_stops": "pt_stops.add.xml"
            }
        },
        "commercial_tools": {
            "description": "商业仿真工具数据导入",
            "tools": ["vissim_parse_routes", "visum_convert_edge_types"],
            "parameters": {
                "vissim_file": "routes.inp",
                "visum_file": "network.net",
                "output_file": "converted.xml"
            }
        },
        "pedestrian_simulation": {
            "description": "行人仿真数据导入",
            "tools": ["dxf2jupedsim_import"],
            "parameters": {
                "dxf_file": "building_plan.dxf",
                "output": "pedestrian_geometry.xml",
                "walkable_layer": "walkable_areas",
                "obstacle_layer": "obstacles"
            }
        }
    }

# 如果直接运行此文件，启动导入工具服务器
if __name__ == "__main__":
    print("启动SUMO导入工具服务器...")
    importtool_mcp.run(transport="sse", host="127.0.0.1", port=8025)
