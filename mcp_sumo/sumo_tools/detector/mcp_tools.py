#!/usr/bin/env python3
"""
SUMO检测器工具模块 - 独立的FastMCP服务器
处理交通流量检测、数据转换和分析功能
"""

import os
import subprocess
import traceback
from typing import Dict, Any, List

from fastmcp import FastMCP, Context

# 设置环境变量
os.environ["SUMO_HOME"] = "D:\Program Files\SUMO"

# ────────────────────────────────────────────────────────────────────────────────
# 创建检测器工具服务器
# ────────────────────────────────────────────────────────────────────────────────
detector_mcp = FastMCP(name="SUMO_Detector_Tools")

# ────────────────────────────────────────────────────────────────────────────────
# TOOL 1: 流量数据转换为边缘数据
# ────────────────────────────────────────────────────────────────────────────────
@detector_mcp.tool()
async def convert_flow_to_edge_data(
    flow_file: str,
    output_file: str,
    detector_file: str = None,
    flow_columns: str = "qPKW,qLKW",
    begin_time: int = 0,
    end_time: int = 1440,
    interval: int = 1440,
    cadyts_format: bool = False,
    ctx: Context = None
) -> Dict[str, Any]:
    """基于SUMO的edgeDataFromFlow.py脚本将CSV流量数据转换为XML边缘数据格式
    
    此工具将检测器流量数据（CSV格式）转换为SUMO的edgeData XML格式
    （遵循meandata格式: http://sumo.dlr.de/xsd/meandata_file.xsd）
    
    参数:
    flow_file: 包含流量数据的CSV文件路径
    output_file: 输出的edgeData XML文件路径
    detector_file: 检测器定义文件路径，如果不提供则从流量文件中推断
    flow_columns: 包含流量数据的列名（以逗号分隔）
    begin_time: 开始时间（分钟或H:M:S格式）
    end_time: 结束时间（分钟或H:M:S格式）
    interval: 聚合时间间隔（分钟或H:M:S格式）
    cadyts_format: 是否生成cadyts格式的输出
    """
    
    if not os.path.exists(flow_file):
        if ctx:
            ctx.error(f"流量文件不存在: {flow_file}")
        return {"success": False, "message": f"流量文件不存在: {flow_file}"}
    
    if detector_file and not os.path.exists(detector_file):
        if ctx:
            ctx.error(f"检测器文件不存在: {detector_file}")
        return {"success": False, "message": f"检测器文件不存在: {detector_file}"}
    
    # 确保输出目录存在
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    # 构建命令
    cmd = [
        "python",
        os.path.join(os.environ.get("SUMO_HOME", ""), "tools", "detector", "edgeDataFromFlow.py"),
        "-f", flow_file,
        "-o", output_file,
        "--flow-columns", flow_columns,
        "--begin", str(begin_time),
        "--end", str(end_time),
        "--interval", str(interval)
    ]
    
    if detector_file:
        cmd.extend(["-d", detector_file])
    if cadyts_format:
        cmd.append("--cadyts")
    
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
        
        result = {
            "success": process.returncode == 0,
            "message": "流量数据转换成功" if process.returncode == 0 else "流量数据转换失败",
            "stdout": process.stdout,
            "stderr": process.stderr,
            "command": " ".join(cmd)
        }
        
        if process.returncode == 0 and os.path.exists(output_file):
            result["output_file"] = output_file
            result["file_size"] = os.path.getsize(output_file)
        
        return result
        
    except Exception as e:
        if ctx:
            ctx.error(f"执行流量数据转换异常: {str(e)}")
        return {
            "success": False,
            "message": f"执行异常: {str(e)}",
            "traceback": traceback.format_exc()
        }

# ────────────────────────────────────────────────────────────────────────────────
# TOOL 2: 边缘数据转换为流量数据
# ────────────────────────────────────────────────────────────────────────────────
@detector_mcp.tool()
async def convert_edge_data_to_flow(
    edge_data_file: str,
    detector_file: str,
    output_file: str = None,
    flow_output_file: str = None,
    flow_column: str = "qPKW",
    detector_flow_file: str = None,
    interval: int = 1440,
    begin_time: int = 0,
    end_time: int = None,
    respect_zero: bool = False,
    long_names: bool = False,
    edge_names: bool = False,
    ctx: Context = None
) -> Dict[str, Any]:
    """基于SUMO的flowFromEdgeData.py脚本将XML边缘数据转换为CSV流量数据
    
    此工具将SUMO的edgeData XML格式转换为检测器流量数据（CSV格式）
    
    参数:
    edge_data_file: 输入的edgeData XML文件路径
    detector_file: 检测器定义文件路径
    output_file: 输出的流量CSV文件路径
    flow_output_file: 备用流量输出文件路径
    flow_column: 要提取的流量数据列名
    detector_flow_file: 检测器流量输出文件路径
    interval: 时间间隔（分钟）
    begin_time: 开始时间（分钟）
    end_time: 结束时间（分钟），如果为None则处理所有数据
    respect_zero: 是否保留零值
    long_names: 是否使用长名称
    edge_names: 是否使用边缘名称而不是检测器名称
    """
    
    if not os.path.exists(edge_data_file):
        if ctx:
            ctx.error(f"边缘数据文件不存在: {edge_data_file}")
        return {"success": False, "message": f"边缘数据文件不存在: {edge_data_file}"}
    
    if not os.path.exists(detector_file):
        if ctx:
            ctx.error(f"检测器文件不存在: {detector_file}")
        return {"success": False, "message": f"检测器文件不存在: {detector_file}"}
    
    # 设置默认输出文件
    if not output_file:
        output_file = edge_data_file.replace('.xml', '_flow.csv')
    
    # 确保输出目录存在
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    # 构建命令
    cmd = [
        "python",
        os.path.join(os.environ.get("SUMO_HOME", ""), "tools", "detector", "flowFromEdgeData.py"),
        "-e", edge_data_file,
        "-d", detector_file,
        "-o", output_file,
        "--flow-column", flow_column,
        "--interval", str(interval),
        "--begin", str(begin_time)
    ]
    
    if end_time is not None:
        cmd.extend(["--end", str(end_time)])
    if flow_output_file:
        cmd.extend(["--flow-output", flow_output_file])
    if detector_flow_file:
        cmd.extend(["--detector-flow-file", detector_flow_file])
    if respect_zero:
        cmd.append("--respect-zero")
    if long_names:
        cmd.append("--long-names")
    if edge_names:
        cmd.append("--edge-names")
    
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
        
        result = {
            "success": process.returncode == 0,
            "message": "边缘数据转换成功" if process.returncode == 0 else "边缘数据转换失败",
            "stdout": process.stdout,
            "stderr": process.stderr,
            "command": " ".join(cmd)
        }
        
        if process.returncode == 0 and os.path.exists(output_file):
            result["output_file"] = output_file
            result["file_size"] = os.path.getsize(output_file)
            if flow_output_file and os.path.exists(flow_output_file):
                result["flow_output_file"] = flow_output_file
            if detector_flow_file and os.path.exists(detector_flow_file):
                result["detector_flow_file"] = detector_flow_file
        
        return result
        
    except Exception as e:
        if ctx:
            ctx.error(f"执行边缘数据转换异常: {str(e)}")
        return {
            "success": False,
            "message": f"执行异常: {str(e)}",
            "traceback": traceback.format_exc()
        }

# ────────────────────────────────────────────────────────────────────────────────
# TOOL 3: 检测器坐标映射
# ────────────────────────────────────────────────────────────────────────────────
@detector_mcp.tool()
async def map_detector_coordinates(
    net_file: str,
    detector_file: str,
    output_file: str,
    detector_output_file: str = "detector.out.xml",
    id_column: str = "id",
    longitude_column: str = "lon",
    latitude_column: str = "lat",
    delimiter: str = ";",
    max_radius: float = 1000,
    vehicle_class: str = "passenger",
    interval: int = 3600,
    ctx: Context = None
) -> Dict[str, Any]:
    """基于SUMO的mapDetectors.py脚本将检测器坐标映射到道路网络
    
    此工具通过地图匹配将坐标点映射到SUMO网络中的车道上，并生成感应环检测器定义。
    
    参数:
    net_file: SUMO网络文件路径
    detector_file: 包含检测器ID和坐标的CSV文件路径
    output_file: 生成的检测器定义输出文件路径
    detector_output_file: 检测器数据输出文件路径
    id_column: CSV文件中包含检测器ID的列名
    longitude_column: CSV文件中包含经度的列名
    latitude_column: CSV文件中包含纬度的列名
    delimiter: CSV文件的分隔符
    max_radius: 映射坐标时的最大距离误差（米）
    vehicle_class: 仅考虑允许指定车辆类型的边缘
    interval: 生成的检测器的聚合时间间隔（秒）
    """
    
    if not os.path.exists(net_file):
        if ctx:
            ctx.error(f"网络文件不存在: {net_file}")
        return {"success": False, "message": f"网络文件不存在: {net_file}"}
    
    if not os.path.exists(detector_file):
        if ctx:
            ctx.error(f"检测器文件不存在: {detector_file}")
        return {"success": False, "message": f"检测器文件不存在: {detector_file}"}
    
    # 确保输出目录存在
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    # 构建命令
    cmd = [
        "python",
        os.path.join(os.environ.get("SUMO_HOME", ""), "tools", "detector", "mapDetectors.py"),
        "-n", net_file,
        "-d", detector_file,
        "-o", output_file,
        "--detector-output", detector_output_file,
        "--id-column", id_column,
        "--lon-column", longitude_column,
        "--lat-column", latitude_column,
        "--delimiter", delimiter,
        "--radius", str(max_radius),
        "--vclass", vehicle_class,
        "--interval", str(interval)
    ]
    
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
        
        result = {
            "success": process.returncode == 0,
            "message": "检测器坐标映射成功" if process.returncode == 0 else "检测器坐标映射失败",
            "stdout": process.stdout,
            "stderr": process.stderr,
            "command": " ".join(cmd)
        }
        
        if process.returncode == 0:
            if os.path.exists(output_file):
                result["output_file"] = output_file
                result["file_size"] = os.path.getsize(output_file)
            if os.path.exists(detector_output_file):
                result["detector_output_file"] = detector_output_file
        
        return result
        
    except Exception as e:
        if ctx:
            ctx.error(f"执行检测器坐标映射异常: {str(e)}")
        return {
            "success": False,
            "message": f"执行异常: {str(e)}",
            "traceback": traceback.format_exc()
        }

# ────────────────────────────────────────────────────────────────────────────────
# TOOL 4: 流量聚合
# ────────────────────────────────────────────────────────────────────────────────
@detector_mcp.tool()
async def aggregate_flows(
    flow_files: List[str],
    output_file: str,
    detector_file: str = None,
    flow_column: str = "qPKW",
    begin_time: int = 0,
    end_time: int = None,
    interval: int = 60,
    ctx: Context = None
) -> Dict[str, Any]:
    """基于SUMO的aggregateFlows.py脚本聚合多个流量文件
    
    此工具将多个流量文件聚合为单个输出文件，支持时间间隔聚合。
    
    参数:
    flow_files: 要聚合的流量文件路径列表
    output_file: 输出的聚合流量文件路径
    detector_file: 检测器定义文件路径（可选）
    flow_column: 要聚合的流量数据列名
    begin_time: 开始时间（分钟）
    end_time: 结束时间（分钟），如果为None则处理所有数据
    interval: 聚合时间间隔（分钟）
    """
    
    # 检查输入文件
    missing_files = [f for f in flow_files if not os.path.exists(f)]
    if missing_files:
        if ctx:
            ctx.error(f"以下文件不存在: {missing_files}")
        return {"success": False, "message": f"以下文件不存在: {missing_files}"}
    
    # 确保输出目录存在
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    # 构建命令
    cmd = [
        "python",
        os.path.join(os.environ.get("SUMO_HOME", ""), "tools", "detector", "aggregateFlows.py"),
        "-o", output_file,
        "--flow-column", flow_column,
        "--begin", str(begin_time),
        "--interval", str(interval)
    ]
    
    # 添加输入文件
    for flow_file in flow_files:
        cmd.extend(["-f", flow_file])
    
    if detector_file:
        cmd.extend(["-d", detector_file])
    if end_time is not None:
        cmd.extend(["--end", str(end_time)])
    
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
        
        result = {
            "success": process.returncode == 0,
            "message": "流量聚合成功" if process.returncode == 0 else "流量聚合失败",
            "stdout": process.stdout,
            "stderr": process.stderr,
            "command": " ".join(cmd),
            "input_files_count": len(flow_files)
        }
        
        if process.returncode == 0 and os.path.exists(output_file):
            result["output_file"] = output_file
            result["file_size"] = os.path.getsize(output_file)
        
        return result
        
    except Exception as e:
        if ctx:
            ctx.error(f"执行流量聚合异常: {str(e)}")
        return {
            "success": False,
            "message": f"执行异常: {str(e)}",
            "traceback": traceback.format_exc()
        }

# ────────────────────────────────────────────────────────────────────────────────
# 检测器资源
# ────────────────────────────────────────────────────────────────────────────────
@detector_mcp.resource("data://detector/config")
def get_detector_config() -> Dict[str, Any]:
    """获取检测器工具配置信息"""
    return {
        "version": "1.0.0",
        "name": "SUMO Detector Tools",
        "description": "SUMO检测器工具包，用于处理交通流量检测、数据转换和分析",
        "tools": [
            "convert_flow_to_edge_data",
            "convert_edge_data_to_flow",
            "map_detector_coordinates",
            "aggregate_flows"
        ],
        "supported_formats": {
            "input": ["CSV", "XML"],
            "output": ["CSV", "XML"]
        }
    }

@detector_mcp.resource("data://detector/help")
def get_detector_help() -> Dict[str, str]:
    """获取检测器工具帮助信息"""
    return {
        "convert_flow_to_edge_data": "将CSV流量数据转换为SUMO的edgeData XML格式",
        "convert_edge_data_to_flow": "将SUMO的edgeData XML格式转换为CSV流量数据",
        "map_detector_coordinates": "通过地图匹配将坐标点映射到SUMO网络中的车道",
        "aggregate_flows": "聚合多个流量文件为单个输出文件"
    }

# 如果直接运行此文件，启动检测器工具服务器
if __name__ == "__main__":
    print("启动SUMO检测器工具服务器...")
    detector_mcp.run(transport="sse", host="127.0.0.1", port=8018)