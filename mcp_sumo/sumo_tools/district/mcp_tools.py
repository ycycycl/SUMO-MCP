#!/usr/bin/env python3
"""
SUMO区域工具模块 - 独立的FastMCP服务器
处理交通分析区(TAZ)的生成、过滤和分析功能
"""

import os
import subprocess
import traceback
from typing import Dict, Any, List

from fastmcp import FastMCP, Context

# 设置环境变量
os.environ["SUMO_HOME"] = "D:\Program Files\SUMO"

# ────────────────────────────────────────────────────────────────────────────────
# 创建区域工具服务器
# ────────────────────────────────────────────────────────────────────────────────
district_mcp = FastMCP(name="SUMO_District_Tools")

# ────────────────────────────────────────────────────────────────────────────────
# TOOL 1: 按车辆类型过滤区域
# ────────────────────────────────────────────────────────────────────────────────
@district_mcp.tool()
async def filter_districts_by_vehicle_class(
        net_file: str,
        taz_file: str,
        vehicle_class: str,
        output_file: str = "taz_filtered.add.xml",
        ctx: Context = None
    ) -> Dict[str, Any]:
        """基于SUMO的filterDistricts.py脚本过滤交通分析区(TAZ)文件
        
        此工具根据指定的车辆类型过滤TAZ文件中的边缘，只保留允许该车辆类型通行的边缘。
        
        参数:
        net_file: SUMO网络文件路径
        taz_file: 要过滤的TAZ(交通分析区)文件路径
        vehicle_class: 用于过滤的车辆类型
        output_file: 过滤后的TAZ文件输出路径
        """
        
        if not os.path.exists(net_file):
            if ctx:
                ctx.error(f"网络文件不存在: {net_file}")
            return {"success": False, "message": f"网络文件不存在: {net_file}"}
        
        if not os.path.exists(taz_file):
            if ctx:
                ctx.error(f"TAZ文件不存在: {taz_file}")
            return {"success": False, "message": f"TAZ文件不存在: {taz_file}"}
        
        # 确保输出目录存在
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        # 构建命令
        cmd = [
            "python", os.path.join(os.environ.get("SUMO_HOME", ""), "tools", "district", "filterDistricts.py"),
            "-n", net_file,
            "-t", taz_file,
            "-o", output_file,
            "--vclass", vehicle_class
        ]
        
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
                    ctx.error(f"filterDistricts.py执行失败: {process.stderr}")
                return {
                    "success": False,
                    "message": f"filterDistricts.py执行失败，返回码: {process.returncode}",
                    "stderr": process.stderr,
                    "stdout": process.stdout
                }
            
            if not os.path.exists(output_file):
                if ctx:
                    ctx.error(f"输出文件未生成: {output_file}")
                return {
                    "success": False,
                    "message": f"输出文件未生成: {output_file}",
                    "stderr": process.stderr,
                    "stdout": process.stdout
                }
            
            # 统计过滤后的TAZ数量
            taz_count = 0
            edge_count = 0
            try:
                with open(output_file, 'r') as f:
                    for line in f:
                        if '<taz ' in line:
                            taz_count += 1
                        if 'edges=' in line:
                            # 粗略估计边缘数量
                            edges_part = line.split('edges="')[1].split('"')[0]
                            edge_count += len(edges_part.split())
            except Exception as e:
                if ctx:
                    ctx.warning(f"无法统计过滤后的TAZ数量: {str(e)}")
            
            return {
                "success": True,
                "message": f"成功过滤TAZ文件，保留了{taz_count}个TAZ区域，包含{edge_count}条边",
                "files": {
                    "filtered_taz": output_file
                },
                "statistics": {
                    "taz_count": taz_count,
                    "edge_count": edge_count
                }
            }
            
        except Exception as e:
            if ctx:
                ctx.error(f"执行TAZ过滤异常: {str(e)}")
            import traceback
            return {
                "success": False,
                "message": f"执行异常: {str(e)}",
                "traceback": traceback.format_exc()
            }

# ────────────────────────────────────────────────────────────────────────────────
# TOOL 2: 生成网格区域
# ────────────────────────────────────────────────────────────────────────────────
@district_mcp.tool()
async def generate_grid_districts(
        net_file: str,
        output_file: str,
        grid_width: float = 100.0,
        vehicle_class: str = None,
        hue: str = "random",
        saturation: float = 1,
        brightness: float = 1,
        seed: int = 42,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """基于SUMO的gridDistricts.py脚本生成基于网格的交通分析区(TAZ)
        
        此工具在网络上创建均匀的网格，并将每个网格单元定义为一个TAZ区域，包含其中的所有边缘。
        
        参数:
        net_file: SUMO网络文件路径
        output_file: 生成的TAZ文件输出路径
        grid_width: 网格单元的宽度（米）
        vehicle_class: 仅包含允许指定车辆类型的边缘
        hue: TAZ颜色的色调值（0-1之间的浮点数或'random'）
        saturation: TAZ颜色的饱和度（0-1之间的浮点数或'random'）
        brightness: TAZ颜色的亮度（0-1之间的浮点数或'random'）
        seed: 随机数种子
        """
        
        if not os.path.exists(net_file):
            if ctx:
                ctx.error(f"网络文件不存在: {net_file}")
            return {"success": False, "message": f"网络文件不存在: {net_file}"}
        
        # 确保输出目录存在
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        # 构建命令
        cmd = [
            "python", os.path.join(os.environ.get("SUMO_HOME", ""), "tools", "district", "gridDistricts.py"),
            "-n", net_file,
            "-o", output_file,
            "-w", str(grid_width),
            "-u", str(hue),
            "-s", str(saturation),
            "-b", str(brightness),
            "--seed", str(seed)
        ]
        
        if vehicle_class:
            cmd.extend(["--vclass", vehicle_class])
        
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
                    ctx.error(f"gridDistricts.py执行失败: {process.stderr}")
                return {
                    "success": False,
                    "message": f"gridDistricts.py执行失败，返回码: {process.returncode}",
                    "stderr": process.stderr,
                    "stdout": process.stdout
                }
            
            if not os.path.exists(output_file):
                if ctx:
                    ctx.error(f"输出文件未生成: {output_file}")
                return {
                    "success": False,
                    "message": f"输出文件未生成: {output_file}",
                    "stderr": process.stderr,
                    "stdout": process.stdout
                }
            
            # 统计生成的TAZ数量
            taz_count = 0
            edge_count = 0
            try:
                with open(output_file, 'r') as f:
                    for line in f:
                        if '<taz ' in line:
                            taz_count += 1
                            if 'edges=' in line:
                                edges_part = line.split('edges="')[1].split('"')[0]
                                edge_count += len(edges_part.split())
            except Exception as e:
                if ctx:
                    ctx.warning(f"无法统计生成的TAZ数量: {str(e)}")
            
            # 计算网格尺寸
            grid_size = "未知"
            try:
                import sumolib
                net = sumolib.net.readNet(net_file)
                xmin, ymin, xmax, ymax = net.getBoundary()
                width = xmax - xmin
                height = ymax - ymin
                cols = int(width / grid_width) + 1
                rows = int(height / grid_width) + 1
                grid_size = f"{cols}x{rows}"
            except Exception as e:
                if ctx:
                    ctx.warning(f"无法计算网格尺寸: {str(e)}")
            
            return {
                "success": True,
                "message": f"成功生成网格TAZ，创建了{taz_count}个TAZ区域，包含{edge_count}条边",
                "files": {
                    "taz_file": output_file
                },
                "statistics": {
                    "taz_count": taz_count,
                    "edge_count": edge_count,
                    "grid_size": grid_size,
                    "grid_width": grid_width
                }
            }
            
        except Exception as e:
            if ctx:
                ctx.error(f"执行网格TAZ生成异常: {str(e)}")
            import traceback
            return {
                "success": False,
                "message": f"执行异常: {str(e)}",
                "traceback": traceback.format_exc()
            }

# ────────────────────────────────────────────────────────────────────────────────
# TOOL 3: 生成车站区域
# ────────────────────────────────────────────────────────────────────────────────
@district_mcp.tool()
async def generate_station_districts(
        net_file: str,
        stop_file: str,
        output_file: str,
        vehicle_classes: str = "rail,rail_urban,subway",
        parallel_radius: float = 100.0,
        merge_stations: bool = False,
        split_output_file: str = None,
        poi_output_file: str = None,
        hue: str = "random",
        saturation: float = 1,
        brightness: float = 1,
        seed: int = 42,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """基于SUMO的stationDistricts.py脚本根据车站位置生成交通分析区(TAZ)
        
        此工具基于车站位置将网络分割成多个区域，每个区域包含与特定车站最近的边缘。
        主要用于铁路网络的分区，但也可用于其他类型的网络。
        
        参数:
        net_file: SUMO网络文件路径
        stop_file: 包含车站/站点定义的附加文件路径
        output_file: 生成的TAZ文件输出路径
        vehicle_classes: 要考虑的车辆类型（以逗号分隔）
        parallel_radius: 查找平行边缘的搜索半径（米）
        merge_stations: 是否合并有共同边缘的车站
        split_output_file: 如果提供，生成用于分割多个车站共享边缘的文件
        poi_output_file: 如果提供，为每个车站生成一个兴趣点文件
        hue: TAZ颜色的色调值（0-1之间的浮点数或'random'）
        saturation: TAZ颜色的饱和度（0-1之间的浮点数或'random'）
        brightness: TAZ颜色的亮度（0-1之间的浮点数或'random'）
        seed: 随机数种子
        """
        
        if not os.path.exists(net_file):
            if ctx:
                ctx.error(f"网络文件不存在: {net_file}")
            return {"success": False, "message": f"网络文件不存在: {net_file}"}
        
        if not os.path.exists(stop_file):
            if ctx:
                ctx.error(f"站点文件不存在: {stop_file}")
            return {"success": False, "message": f"站点文件不存在: {stop_file}"}
        
        # 确保输出目录存在
        for file_path in [output_file, split_output_file, poi_output_file]:
            if file_path:
                output_dir = os.path.dirname(file_path)
                if output_dir and not os.path.exists(output_dir):
                    os.makedirs(output_dir, exist_ok=True)
        
        # 构建命令
        cmd = [
            "python", os.path.join(os.environ.get("SUMO_HOME", ""), "tools", "district", "stationDistricts.py"),
            "-n", net_file,
            "-s", stop_file,
            "-o", output_file,
            "--vclasses", vehicle_classes,
            "--parallel-radius", str(parallel_radius),
            "--hue", str(hue),
            "--saturation", str(saturation),
            "--brightness", str(brightness),
            "--seed", str(seed)
        ]
        
        if merge_stations:
            cmd.append("--merge")
        
        if split_output_file:
            cmd.extend(["--split-output", split_output_file])
        
        if poi_output_file:
            cmd.extend(["--poi-output", poi_output_file])
        
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
                    ctx.error(f"stationDistricts.py执行失败: {process.stderr}")
                return {
                    "success": False,
                    "message": f"stationDistricts.py执行失败，返回码: {process.returncode}",
                    "stderr": process.stderr,
                    "stdout": process.stdout
                }
            
            if not os.path.exists(output_file):
                if ctx:
                    ctx.error(f"输出文件未生成: {output_file}")
                return {
                    "success": False,
                    "message": f"输出文件未生成: {output_file}",
                    "stderr": process.stderr,
                    "stdout": process.stdout
                }
            
            # 统计生成的TAZ数量和站点数量
            taz_count = 0
            edge_count = 0
            try:
                with open(output_file, 'r') as f:
                    for line in f:
                        if '<taz ' in line:
                            taz_count += 1
                            if 'edges=' in line:
                                edges_part = line.split('edges="')[1].split('"')[0]
                                edge_count += len(edges_part.split())
            except Exception as e:
                if ctx:
                    ctx.warning(f"无法统计生成的TAZ数量: {str(e)}")
            
            result = {
                "success": True,
                "message": f"成功生成基于站点的TAZ，创建了{taz_count}个TAZ区域，包含{edge_count}条边",
                "files": {
                    "taz_file": output_file
                },
                "statistics": {
                    "taz_count": taz_count,
                    "edge_count": edge_count
                }
            }
            
            if split_output_file and os.path.exists(split_output_file):
                result["files"]["split_file"] = split_output_file
            
            if poi_output_file and os.path.exists(poi_output_file):
                result["files"]["poi_file"] = poi_output_file
                
                # 统计POI数量
                poi_count = 0
                try:
                    with open(poi_output_file, 'r') as f:
                        for line in f:
                            if '<poi ' in line:
                                poi_count += 1
                    result["statistics"]["poi_count"] = poi_count
                except Exception as e:
                    if ctx:
                        ctx.warning(f"无法统计生成的POI数量: {str(e)}")
            
            return result
            
        except Exception as e:
            if ctx:
                ctx.error(f"执行站点TAZ生成异常: {str(e)}")
            import traceback
            return {
                "success": False,
                "message": f"执行异常: {str(e)}",
                "traceback": traceback.format_exc()
            }

# ────────────────────────────────────────────────────────────────────────────────
# 区域工具资源
# ────────────────────────────────────────────────────────────────────────────────
@district_mcp.resource("data://district/config")
def get_district_config() -> Dict[str, Any]:
    """获取区域工具配置信息"""
    return {
        "version": "1.0.0",
        "name": "SUMO District Tools",
        "description": "SUMO区域工具包，用于交通分析区(TAZ)的生成、过滤和分析",
        "tools": [
            "filter_districts_by_vehicle_class",
            "generate_grid_districts",
            "generate_station_districts"
        ],
        "supported_formats": {
            "input": ["XML", "NET"],
            "output": ["XML", "TAZ"]
        }
    }

@district_mcp.resource("data://district/help")
def get_district_help() -> Dict[str, str]:
    """获取区域工具帮助信息"""
    return {
        "filter_districts_by_vehicle_class": "根据车辆类型过滤交通分析区(TAZ)文件",
        "generate_grid_districts": "基于网格模式生成交通分析区",
        "generate_station_districts": "基于车站位置生成交通分析区"
    }

# 如果直接运行此文件，启动区域工具服务器
if __name__ == "__main__":
    print("启动SUMO区域工具服务器...")
    district_mcp.run(transport="sse", host="127.0.0.1", port=8020)
