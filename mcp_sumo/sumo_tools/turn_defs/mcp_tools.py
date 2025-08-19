#!/usr/bin/env python3
"""
SUMO转向定义工具模块 - 独立的FastMCP服务器
处理交通转向规则、转向比例和转向定义的生成与分析
"""

import os
import subprocess
import traceback
from typing import Dict, Any, List

from fastmcp import FastMCP, Context

# 设置环境变量
os.environ["SUMO_HOME"] = "D:\Program Files\SUMO"

# ────────────────────────────────────────────────────────────────────────────────
# 创建转向定义工具服务器
# ────────────────────────────────────────────────────────────────────────────────
turn_defs_mcp = FastMCP(name="SUMO_TurnDefs_Tools")

# ────────────────────────────────────────────────────────────────────────────────
# TOOL 1: 生成转向比例
# ────────────────────────────────────────────────────────────────────────────────
@turn_defs_mcp.tool()
async def generate_turn_ratios(
        route_files: str,
        output_file: str = "turnRatios.add.xml",
        probabilities: bool = False,
        id: str = "generated",
        begin: str = "0",
        end: str = None,
        interval: str = None,
        verbose: bool = False,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """基于SUMO的generateTurnRatios.py脚本生成转向比例
        
        参数:
        route_files: 路由文件路径，多个文件用逗号分隔
        output_file: 输出文件路径
        probabilities: 是否计算转向概率而不是交通量
        id: 定义间隔ID
        begin: 自定义开始时间（秒或H:M:S格式）
        end: 自定义结束时间（秒或H:M:S格式）
        interval: 自定义聚合间隔（秒或H:M:S格式）
        verbose: 是否输出详细信息
        """
        
        cmd = [
            "python",
            os.path.join(os.environ.get("SUMO_HOME", ""), "tools", "turn-defs", "generateTurnRatios.py"),
            "-r", route_files,
            "-o", output_file,
            "--id", id,
            "-b", begin
        ]
        
        if probabilities:
            cmd.append("-p")
        
        if end:
            cmd.extend(["-e", end])
        
        if interval:
            cmd.extend(["-i", interval])
        
        if verbose:
            cmd.append("-v")
        
        if ctx:
            ctx.info(f"执行命令: {' '.join(cmd)}")
        
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        return {
            "success": process.returncode == 0,
            "message": "转向比例生成成功" if process.returncode == 0 else "转向比例生成失败",
            "stdout": process.stdout,
            "stderr": process.stderr,
            "file": output_file if os.path.exists(output_file) else None
        }
    
# ────────────────────────────────────────────────────────────────────────────────
# TOOL 2: 转向计数转边缘计数
# ────────────────────────────────────────────────────────────────────────────────
@turn_defs_mcp.tool()
async def turn_count_to_edge_count(
        turn_file: str,
        output_file: str,
        edgedata_attribute: str = "entered",
        turn_attribute: str = "count",
        ctx: Context = None
    ) -> Dict[str, Any]:
        """基于SUMO的turnCount2EdgeCount.py脚本将转向计数数据转换为边缘数据
        
        参数:
        turn_file: 输入转向计数文件路径
        output_file: 输出的边缘数据文件路径
        edgedata_attribute: 使用指定属性写入边缘数据计数
        turn_attribute: 从指定属性读取转向计数
        """
        
        cmd = [
            "python",
            os.path.join(os.environ.get("SUMO_HOME", ""), "tools", "turn-defs", "turnCount2EdgeCount.py"),
            "-t", turn_file,
            "-o", output_file,
            "--edgedata-attribute", edgedata_attribute,
            "--turn-attribute", turn_attribute
        ]
        
        if ctx:
            ctx.info(f"执行命令: {' '.join(cmd)}")
        
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        return {
            "success": process.returncode == 0,
            "message": "转向计数转换为边缘数据成功" if process.returncode == 0 else "转向计数转换为边缘数据失败",
            "stdout": process.stdout,
            "stderr": process.stderr,
            "file": output_file if os.path.exists(output_file) else None
        }
    
# ────────────────────────────────────────────────────────────────────────────────
# TOOL 3: 转向文件转边缘关系
# ────────────────────────────────────────────────────────────────────────────────
@turn_defs_mcp.tool()
async def turn_file_to_edge_relations(
        turn_file: str,
        output_file: str,
        turn_attribute: str = "probability",
        ctx: Context = None
    ) -> Dict[str, Any]:
        """基于SUMO的turnFile2EdgeRelations.py脚本将转向文件转换为边缘关系
        
        参数:
        turn_file: 输入转向计数文件路径
        output_file: 输出的边缘关系文件路径
        turn_attribute: 将转向'probability'写入指定属性
        """
        
        cmd = [
            "python",
            os.path.join(os.environ.get("SUMO_HOME", ""), "tools", "turn-defs", "turnFile2EdgeRelations.py"),
            "-t", turn_file,
            "-o", output_file,
            "--turn-attribute", turn_attribute
        ]
        
        if ctx:
            ctx.info(f"执行命令: {' '.join(cmd)}")
        
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        return {
            "success": process.returncode == 0,
            "message": "转向文件转换为边缘关系成功" if process.returncode == 0 else "转向文件转换为边缘关系失败",
            "stdout": process.stdout,
            "stderr": process.stderr,
            "file": output_file if os.path.exists(output_file) else None
        }

# ────────────────────────────────────────────────────────────────────────────────
# 转向定义工具资源
# ────────────────────────────────────────────────────────────────────────────────
@turn_defs_mcp.resource("data://turn_defs/config")
def get_turn_defs_config() -> Dict[str, Any]:
    """获取转向定义工具配置信息"""
    return {
        "version": "1.0.0",
        "name": "SUMO Turn Definitions Tools",
        "description": "SUMO转向定义工具包，用于处理交通转向规则、转向比例和转向定义的生成与分析",
        "tools": [
            "generate_turn_ratios",
            "turn_count_to_edge_count",
            "turn_file_to_edge_relations"
        ],
        "supported_formats": [
            "路由文件 (.rou.xml)",
            "转向文件 (.turns.xml)",
            "边缘关系文件 (.xml)"
        ],
        "analysis_types": [
            "转向比例生成",
            "转向计数转换",
            "边缘关系提取"
        ]
    }

@turn_defs_mcp.resource("data://turn_defs/help")
def get_turn_defs_help() -> Dict[str, str]:
    """获取转向定义工具帮助信息"""
    return {
        "generate_turn_ratios": "基于路由文件生成转向比例，支持概率计算和时间间隔聚合",
        "turn_count_to_edge_count": "将转向计数数据转换为边缘计数数据，用于交通流量分析",
        "turn_file_to_edge_relations": "从转向文件中提取边缘关系，生成网络连接信息"
    }

@turn_defs_mcp.resource("data://turn_defs/examples")
def get_turn_defs_examples() -> Dict[str, Any]:
    """获取转向定义工具使用示例"""
    return {
        "generate_ratios": {
            "description": "生成转向比例",
            "parameters": {
                "route_files": "routes.rou.xml",
                "output_file": "turnRatios.add.xml",
                "probabilities": True,
                "begin": "0",
                "end": "3600"
            }
        },
        "count_conversion": {
            "description": "转向计数转换",
            "parameters": {
                "turn_count_file": "turnCounts.xml",
                "output_file": "edgeCounts.xml",
                "net_file": "network.net.xml"
            }
        },
        "edge_relations": {
            "description": "提取边缘关系",
            "parameters": {
                "turn_file": "turns.add.xml",
                "output_file": "edgeRelations.xml",
                "turn_attribute": "probability"
            }
        }
    }

# 如果直接运行此文件，启动转向定义工具服务器
if __name__ == "__main__":
    print("启动SUMO转向定义工具服务器...")
    turn_defs_mcp.run(transport="sse", host="127.0.0.1", port=8023)
