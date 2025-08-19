#!/usr/bin/env python3
"""
SUMO可视化工具模块 - 独立的FastMCP服务器
处理SUMO仿真结果的图表生成和可视化功能
"""

import os
import subprocess
from typing import Dict, Any

from fastmcp import FastMCP, Context

# 设置环境变量
os.environ["SUMO_HOME"] = "D:\Program Files\SUMO"

# ────────────────────────────────────────────────────────────────────────────────
# 创建可视化工具服务器
# ────────────────────────────────────────────────────────────────────────────────
visualization_mcp = FastMCP(name="SUMO_Visualization_Tools")

# ────────────────────────────────────────────────────────────────────────────────
# TOOL 1: CSV条形图
# ────────────────────────────────────────────────────────────────────────────────
@visualization_mcp.tool()
async def plot_csv_bars(
        csv_file: str,
        output_file: str,
        column: int = 1,
        revert: bool = False,
        width: float = 0.8,
        space: float = 0.2,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """基于SUMO的plot_csv_bars.py脚本将CSV数据绘制为条形图"""
        
        cmd = [
            "python",
            os.path.join(os.environ.get("SUMO_HOME", ""), "tools", "visualization", "plot_csv_bars.py"),
            "-i", csv_file,
            "-o", output_file,
            "--column", str(column),
            "--width", str(width),
            "--space", str(space)
        ]
        
        if revert:
            cmd.append("--revert")
        
        if ctx:
            ctx.info(f"执行命令: {' '.join(cmd)}")
        
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        return {
            "success": process.returncode == 0,
            "message": "条形图生成成功" if process.returncode == 0 else "条形图生成失败",
            "stdout": process.stdout,
            "stderr": process.stderr,
            "file": output_file if os.path.exists(output_file) else None
        }
    
# ────────────────────────────────────────────────────────────────────────────────
# TOOL 2: CSV饼图
# ────────────────────────────────────────────────────────────────────────────────
@visualization_mcp.tool()
async def plot_csv_pie(
        csv_file: str,
        output_file: str,
        percentage: bool = False,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """基于SUMO的plot_csv_pie.py脚本将CSV数据绘制为饼图"""
        
        cmd = [
            "python",
            os.path.join(os.environ.get("SUMO_HOME", ""), "tools", "visualization", "plot_csv_pie.py"),
            "-i", csv_file,
            "-o", output_file
        ]
        
        if percentage:
            cmd.append("-p")
        
        if ctx:
            ctx.info(f"执行命令: {' '.join(cmd)}")
        
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        return {
            "success": process.returncode == 0,
            "message": "饼图生成成功" if process.returncode == 0 else "饼图生成失败",
            "stdout": process.stdout,
            "stderr": process.stderr,
            "file": output_file if os.path.exists(output_file) else None
        }
    
# ────────────────────────────────────────────────────────────────────────────────
# TOOL 3: CSV时间线图
# ────────────────────────────────────────────────────────────────────────────────
@visualization_mcp.tool()
async def plot_csv_timeline(
        csv_file: str,
        output_file: str,
        columns: str = None,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """基于SUMO的plot_csv_timeline.py脚本将CSV数据绘制为时间线图"""
        
        cmd = [
            "python",
            os.path.join(os.environ.get("SUMO_HOME", ""), "tools", "visualization", "plot_csv_timeline.py"),
            "-i", csv_file,
            "-o", output_file
        ]
        
        if columns:
            cmd.extend(["--columns", columns])
        
        if ctx:
            ctx.info(f"执行命令: {' '.join(cmd)}")
        
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        return {
            "success": process.returncode == 0,
            "message": "时间线图生成成功" if process.returncode == 0 else "时间线图生成失败",
            "stdout": process.stdout,
            "stderr": process.stderr,
            "file": output_file if os.path.exists(output_file) else None
        }

# ────────────────────────────────────────────────────────────────────────────────
# TOOL 4: 网络转储可视化
# ────────────────────────────────────────────────────────────────────────────────
@visualization_mcp.tool()
async def plot_net_dump(
        net_file: str,
        dump_files: str,
        output_file: str = None,
        measures: str = "speed,entered",
        min_width: float = 0.5,
        max_width: float = 3,
        log_colors: bool = False,
        log_widths: bool = False,
        min_color_value: float = None,
        max_color_value: float = None,
        min_width_value: float = None,
        max_width_value: float = None,
        color_bar_label: str = "",
        internal: bool = False,
        verbose: bool = False,
        size: str = None,
        dpi: int = None,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """基于SUMO的plot_net_dump.py脚本将网络和边缘数据可视化
        
        参数:
        net_file: SUMO网络文件路径
        dump_files: 边缘数据文件路径，多个文件用逗号分隔
        output_file: 输出图像文件路径
        measures: 要绘制的指标，格式为"颜色指标,宽度指标"
        min_width: 最小边缘宽度
        max_width: 最大边缘宽度
        log_colors: 是否对颜色进行对数缩放
        log_widths: 是否对宽度进行对数缩放
        min_color_value: 颜色值的最小值
        max_color_value: 颜色值的最大值
        min_width_value: 宽度值的最小值
        max_width_value: 宽度值的最大值
        color_bar_label: 颜色条的标签
        internal: 是否包含内部边缘
        verbose: 是否输出详细信息
        size: 图像大小，格式为"宽度,高度"
        dpi: 图像分辨率
        """
        
        cmd = [
            "python",
            os.path.join(os.environ.get("SUMO_HOME", ""), "tools", "visualization", "plot_net_dump.py"),
            "-n", net_file,
            "-i", dump_files,
            "-m", measures,
            "--min-width", str(min_width),
            "--max-width", str(max_width),
            "--color-bar-label", color_bar_label
        ]
        
        if output_file:
            cmd.extend(["-o", output_file])
        
        if log_colors:
            cmd.append("--log-colors")
        
        if log_widths:
            cmd.append("--log-widths")
        
        if min_color_value is not None:
            cmd.extend(["--min-color-value", str(min_color_value)])
        
        if max_color_value is not None:
            cmd.extend(["--max-color-value", str(max_color_value)])
        
        if min_width_value is not None:
            cmd.extend(["--min-width-value", str(min_width_value)])
        
        if max_width_value is not None:
            cmd.extend(["--max-width-value", str(max_width_value)])
        
        if internal:
            cmd.append("--internal")
        
        if verbose:
            cmd.append("-v")
        
        if size:
            cmd.extend(["--size", size])
        
        if dpi:
            cmd.extend(["--dpi", str(dpi)])
        
        if ctx:
            ctx.info(f"执行命令: {' '.join(cmd)}")
        
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        return {
            "success": process.returncode == 0,
            "message": "网络数据可视化成功" if process.returncode == 0 else "网络数据可视化失败",
            "stdout": process.stdout,
            "stderr": process.stderr,
            "file": output_file if output_file and os.path.exists(output_file) else None
        }

# ────────────────────────────────────────────────────────────────────────────────
# TOOL 5: 网络选择可视化
# ────────────────────────────────────────────────────────────────────────────────
@visualization_mcp.tool()
async def plot_net_selection(
        net_file: str,
        selection_file: str,
        output_file: str = None,
        selected_width: float = 1,
        selected_color: str = 'r',
        edge_width: float = 0.2,
        edge_color: str = '#606060',
        verbose: bool = False,
        size: str = None,
        dpi: int = None,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """基于SUMO的plot_net_selection.py脚本将网络选择可视化
        
        参数:
        net_file: SUMO网络文件路径
        selection_file: 选择文件路径
        output_file: 输出图像文件路径
        selected_width: 选中边缘的宽度
        selected_color: 选中边缘的颜色
        edge_width: 未选中边缘的宽度
        edge_color: 未选中边缘的颜色
        verbose: 是否输出详细信息
        size: 图像大小，格式为"宽度,高度"
        dpi: 图像分辨率
        """
        
        cmd = [
            "python",
            os.path.join(os.environ.get("SUMO_HOME", ""), "tools", "visualization", "plot_net_selection.py"),
            "-n", net_file,
            "-i", selection_file,
            "--selected-width", str(selected_width),
            "--color", selected_color,
            "--edge-width", str(edge_width),
            "--edge-color", edge_color
        ]
        
        if output_file:
            cmd.extend(["-o", output_file])
        
        if verbose:
            cmd.append("-v")
        
        if size:
            cmd.extend(["--size", size])
        
        if dpi:
            cmd.extend(["--dpi", str(dpi)])
        
        if ctx:
            ctx.info(f"执行命令: {' '.join(cmd)}")
        
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        return {
            "success": process.returncode == 0,
            "message": "网络选择可视化成功" if process.returncode == 0 else "网络选择可视化失败",
            "stdout": process.stdout,
            "stderr": process.stderr,
            "file": output_file if output_file and os.path.exists(output_file) else None
        }

# ────────────────────────────────────────────────────────────────────────────────
# TOOL 6: 网络速度可视化
# ────────────────────────────────────────────────────────────────────────────────
@visualization_mcp.tool()
async def plot_net_speeds(
        net_file: str,
        output_file: str = None,
        edge_width: float = 1,
        edge_color: str = 'k',
        min_v: float = None,
        max_v: float = None,
        verbose: bool = False,
        size: str = None,
        dpi: int = None,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """基于SUMO的plot_net_speeds.py脚本将网络速度可视化
        
        参数:
        net_file: SUMO网络文件路径
        output_file: 输出图像文件路径
        edge_width: 边缘宽度
        edge_color: 边缘颜色
        min_v: 最小速度值
        max_v: 最大速度值
        verbose: 是否输出详细信息
        size: 图像大小，格式为"宽度,高度"
        dpi: 图像分辨率
        """
        
        cmd = [
            "python",
            os.path.join(os.environ.get("SUMO_HOME", ""), "tools", "visualization", "plot_net_speeds.py"),
            "-n", net_file,
            "--edge-width", str(edge_width),
            "--edge-color", edge_color
        ]
        
        if output_file:
            cmd.extend(["-o", output_file])
        
        if min_v is not None:
            cmd.extend(["--minV", str(min_v)])
        
        if max_v is not None:
            cmd.extend(["--maxV", str(max_v)])
        
        if verbose:
            cmd.append("-v")
        
        if size:
            cmd.extend(["--size", size])
        
        if dpi:
            cmd.extend(["--dpi", str(dpi)])
        
        if ctx:
            ctx.info(f"执行命令: {' '.join(cmd)}")
        
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        return {
            "success": process.returncode == 0,
            "message": "网络速度可视化成功" if process.returncode == 0 else "网络速度可视化失败",
            "stdout": process.stdout,
            "stderr": process.stderr,
            "file": output_file if output_file and os.path.exists(output_file) else None
        }

# ────────────────────────────────────────────────────────────────────────────────
# TOOL 7: 交通信号灯可视化
# ────────────────────────────────────────────────────────────────────────────────
@visualization_mcp.tool()
async def plot_net_traffic_lights(
        net_file: str,
        output_file: str = None,
        width: float = 20,
        color: str = 'r',
        edge_width: float = 1,
        edge_color: str = 'k',
        verbose: bool = False,
        size: str = None,
        dpi: int = None,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """基于SUMO的plot_net_trafficLights.py脚本将网络交通信号灯可视化
        
        参数:
        net_file: SUMO网络文件路径
        output_file: 输出图像文件路径
        width: 点的宽度
        color: 点的颜色
        edge_width: 边缘宽度
        edge_color: 边缘颜色
        verbose: 是否输出详细信息
        size: 图像大小，格式为"宽度,高度"
        dpi: 图像分辨率
        """
        
        cmd = [
            "python",
            os.path.join(os.environ.get("SUMO_HOME", ""), "tools", "visualization", "plot_net_trafficLights.py"),
            "-n", net_file,
            "-w", str(width),
            "--color", color,
            "--edge-width", str(edge_width),
            "--edge-color", edge_color
        ]
        
        if output_file:
            cmd.extend(["-o", output_file])
        
        if verbose:
            cmd.append("-v")
        
        if size:
            cmd.extend(["--size", size])
        
        if dpi:
            cmd.extend(["--dpi", str(dpi)])
        
        if ctx:
            ctx.info(f"执行命令: {' '.join(cmd)}")
        
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        return {
            "success": process.returncode == 0,
            "message": "交通信号灯可视化成功" if process.returncode == 0 else "交通信号灯可视化失败",
            "stdout": process.stdout,
            "stderr": process.stderr,
            "file": output_file if output_file and os.path.exists(output_file) else None
        }

# ────────────────────────────────────────────────────────────────────────────────
# TOOL 8: 仿真摘要可视化
# ────────────────────────────────────────────────────────────────────────────────
@visualization_mcp.tool()
async def plot_summary(
        summary_inputs: str,
        output_file: str = None,
        measure: str = "running",
        verbose: bool = False,
        size: str = None,
        dpi: int = None,
        marker: str = None,
        linestyle: str = "-",
        ctx: Context = None
    ) -> Dict[str, Any]:
        """基于SUMO的plot_summary.py脚本将摘要输出文件可视化
        
        参数:
        summary_inputs: 摘要输出文件路径，多个文件用逗号分隔
        output_file: 输出图像文件路径
        measure: 要绘制的指标
        verbose: 是否输出详细信息
        size: 图像大小，格式为"宽度,高度"
        dpi: 图像分辨率
        marker: 数据点标记样式
        linestyle: 线条样式
        """
        
        cmd = [
            "python",
            os.path.join(os.environ.get("SUMO_HOME", ""), "tools", "visualization", "plot_summary.py"),
            "-i", summary_inputs,
            "-m", measure,
            "--linestyle", linestyle
        ]
        
        if output_file:
            cmd.extend(["-o", output_file])
        
        if verbose:
            cmd.append("-v")
        
        if size:
            cmd.extend(["--size", size])
        
        if dpi:
            cmd.extend(["--dpi", str(dpi)])
        
        if marker:
            cmd.extend(["--marker", marker])
        
        if ctx:
            ctx.info(f"执行命令: {' '.join(cmd)}")
        
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        return {
            "success": process.returncode == 0,
            "message": "摘要数据可视化成功" if process.returncode == 0 else "摘要数据可视化失败",
            "stdout": process.stdout,
            "stderr": process.stderr,
            "file": output_file if output_file and os.path.exists(output_file) else None
        }

# ────────────────────────────────────────────────────────────────────────────────
# TOOL 9: XML属性可视化
# ────────────────────────────────────────────────────────────────────────────────
@visualization_mcp.tool()
async def plot_xml_attributes(
        xml_files: str,
        output_file: str = None,
        xattr: str = None,
        yattr: str = None,
        idattr: str = "id",
        xelem: str = None,
        yelem: str = None,
        idelem: str = None,
        csv_output: str = None,
        filter_ids: str = None,
        pick_distance: float = 1,
        label: str = None,
        join_files: bool = False,
        join_x: bool = False,
        join_y: bool = False,
        xfactor: float = 1,
        yfactor: float = 1,
        xbin: float = None,
        ybin: float = None,
        xclamp: str = None,
        yclamp: str = None,
        invert_yaxis: bool = False,
        scatterplot: bool = False,
        barplot: bool = False,
        hbarplot: bool = False,
        legend: bool = False,
        robust_parser: bool = False,
        verbose: bool = False,
        size: str = None,
        dpi: int = None,
        marker: str = None,
        linestyle: str = "-",
        ctx: Context = None
    ) -> Dict[str, Any]:
        """基于SUMO的plotXMLAttributes.py脚本将XML属性可视化
        
        参数:
        xml_files: XML文件路径，多个文件用逗号分隔
        output_file: 输出图像文件路径
        xattr: X轴属性
        yattr: Y轴属性
        idattr: 用于分组数据点的ID属性
        xelem: X轴元素
        yelem: Y轴元素
        idelem: ID元素
        csv_output: CSV输出文件路径
        filter_ids: 仅绘制指定ID列表的数据点
        pick_distance: 交互式绘图模式下的拾取距离
        label: 绘图标签
        join_files: 不区分不同文件的数据点
        join_x: 如果xattr是列表，则连接值
        join_y: 如果yattr是列表，则连接值
        xfactor: X数据的乘数
        yfactor: Y数据的乘数
        xbin: X数据的分箱大小
        ybin: Y数据的分箱大小
        xclamp: 将X值限制在范围A:B或半范围A:/：B内
        yclamp: 将Y值限制在范围A:B或半范围A:/：B内
        invert_yaxis: 反转Y轴
        scatterplot: 绘制散点图而不是线图
        barplot: 绘制平行于Y轴的条形图
        hbarplot: 绘制平行于X轴的条形图
        legend: 添加图例
        robust_parser: 使用标准XML解析器而不是基于正则表达式的解析器
        verbose: 是否输出详细信息
        size: 图像大小，格式为"宽度,高度"
        dpi: 图像分辨率
        marker: 数据点标记样式
        linestyle: 线条样式
        """
        
        cmd = [
            "python",
            os.path.join(os.environ.get("SUMO_HOME", ""), "tools", "visualization", "plotXMLAttributes.py"),
            "-x", xattr,
            "-y", yattr,
            "-i", idattr,
            "--linestyle", linestyle
        ]
        
        # 添加文件参数
        for file in xml_files.split(","):
            cmd.append(file.strip())
        
        if output_file:
            cmd.extend(["-o", output_file])
        
        if xelem:
            cmd.extend(["--xelem", xelem])
        
        if yelem:
            cmd.extend(["--yelem", yelem])
        
        if idelem:
            cmd.extend(["--idelem", idelem])
        
        if csv_output:
            cmd.extend(["--csv-output", csv_output])
        
        if filter_ids:
            cmd.extend(["--filter-ids", filter_ids])
        
        if pick_distance != 1:
            cmd.extend(["-p", str(pick_distance)])
        
        if label:
            cmd.extend(["--label", label])
        
        if join_files:
            cmd.append("-j")
        
        if join_x:
            cmd.append("--join-x")
        
        if join_y:
            cmd.append("--join-y")
        
        if xfactor != 1:
            cmd.extend(["--xfactor", str(xfactor)])
        
        if yfactor != 1:
            cmd.extend(["--yfactor", str(yfactor)])
        
        if xbin:
            cmd.extend(["--xbin", str(xbin)])
        
        if ybin:
            cmd.extend(["--ybin", str(ybin)])
        
        if xclamp:
            cmd.extend(["--xclamp", xclamp])
        
        if yclamp:
            cmd.extend(["--yclamp", yclamp])
        
        if invert_yaxis:
            cmd.append("--invert-yaxis")
        
        if scatterplot:
            cmd.append("--scatterplot")
        
        if barplot:
            cmd.append("--barplot")
        
        if hbarplot:
            cmd.append("--hbarplot")
        
        if legend:
            cmd.append("--legend")
        
        if robust_parser:
            cmd.append("--robust-parser")
        
        if verbose:
            cmd.append("-v")
        
        if size:
            cmd.extend(["--size", size])
        
        if dpi:
            cmd.extend(["--dpi", str(dpi)])
        
        if marker:
            cmd.extend(["--marker", marker])
        
        if ctx:
            ctx.info(f"执行命令: {' '.join(cmd)}")
        
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        return {
            "success": process.returncode == 0,
            "message": "XML属性可视化成功" if process.returncode == 0 else "XML属性可视化失败",
            "stdout": process.stdout,
            "stderr": process.stderr,
            "file": output_file if output_file and os.path.exists(output_file) else None
        }

# ────────────────────────────────────────────────────────────────────────────────
# 可视化工具资源
# ────────────────────────────────────────────────────────────────────────────────
@visualization_mcp.resource("data://visualization/config")
def get_visualization_config() -> Dict[str, Any]:
    """获取可视化工具配置信息"""
    return {
        "version": "1.0.0",
        "name": "SUMO Visualization Tools",
        "description": "SUMO仿真结果可视化工具包，支持多种图表类型和数据源",
        "tools": [
            "plot_csv_bars",
            "plot_csv_pie", 
            "plot_csv_timeline",
            "plot_net_dump",
            "plot_net_selection",
            "plot_net_speeds",
            "plot_net_traffic_lights",
            "plot_summary",
            "plot_xml_attributes"
        ],
        "supported_formats": [
            "CSV",
            "XML",
            "SUMO dump files",
            "SUMO summary files"
        ],
        "chart_types": [
            "条形图",
            "饼图",
            "时间线图",
            "网络可视化",
            "散点图",
            "热力图"
        ]
    }

@visualization_mcp.resource("data://visualization/help")
def get_visualization_help() -> Dict[str, str]:
    """获取可视化工具帮助信息"""
    return {
        "plot_csv_bars": "将CSV数据绘制为条形图，支持多种样式和配置选项",
        "plot_csv_pie": "将CSV数据绘制为饼图，适用于比例数据的可视化",
        "plot_csv_timeline": "将CSV数据绘制为时间线图，显示数据随时间的变化",
        "plot_net_dump": "可视化SUMO网络转储数据，支持多种属性和过滤选项",
        "plot_net_selection": "可视化网络中的选定元素，用于突出显示特定区域",
        "plot_net_speeds": "可视化网络中的速度分布，显示交通流速度情况",
        "plot_net_traffic_lights": "可视化交通信号灯在网络中的分布和状态",
        "plot_summary": "可视化SUMO仿真摘要数据，提供整体性能概览",
        "plot_xml_attributes": "可视化XML文件中的属性数据，支持多种图表类型"
    }

@visualization_mcp.resource("data://visualization/examples")
def get_visualization_examples() -> Dict[str, Any]:
    """获取可视化工具使用示例"""
    return {
        "basic_csv_chart": {
            "description": "基本CSV图表生成",
            "tools": ["plot_csv_bars", "plot_csv_pie"],
            "parameters": {
                "csv_file": "data/simulation_results.csv",
                "output_file": "output/chart.png"
            }
        },
        "network_visualization": {
            "description": "网络可视化",
            "tools": ["plot_net_dump", "plot_net_speeds"],
            "parameters": {
                "net_file": "network.net.xml",
                "dump_file": "network_dump.xml",
                "output_file": "network_vis.png"
            }
        },
        "time_series_analysis": {
            "description": "时间序列分析",
            "tools": ["plot_csv_timeline", "plot_summary"],
            "parameters": {
                "csv_file": "time_series.csv",
                "summary_file": "summary.xml",
                "output_file": "timeline.png"
            }
        }
    }

# 如果直接运行此文件，启动可视化工具服务器
if __name__ == "__main__":
    print("启动SUMO可视化工具服务器...")
    visualization_mcp.run(transport="sse", host="127.0.0.1", port=8022)
