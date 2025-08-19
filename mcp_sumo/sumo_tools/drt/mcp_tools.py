#!/usr/bin/env python3
"""
SUMO需求响应交通(DRT)工具模块 - 独立的FastMCP服务器
处理按需响应交通的路线优化和调度功能
"""

import os
import subprocess
import traceback
from typing import Dict, Any, List

from fastmcp import FastMCP, Context

# 设置环境变量
os.environ["SUMO_HOME"] = "D:\Program Files\SUMO"

# ────────────────────────────────────────────────────────────────────────────────
# 创建DRT工具服务器
# ────────────────────────────────────────────────────────────────────────────────
drt_mcp = FastMCP(name="SUMO_DRT_Tools")

# ────────────────────────────────────────────────────────────────────────────────
# TOOL 1: DRT路线优化
# ────────────────────────────────────────────────────────────────────────────────
@drt_mcp.tool()
async def optimize_drt_routes(
        sumo_config: str,
        end_time: int = None,
        interval: int = 30,
        time_limit: float = 10,
        cost_type: str = "distance",
        direct_route_factor: float = 1.5,
        waiting_time: int = 900,
        fix_allocation: bool = False,
        penalty_factor: str = "dynamic",
        nogui: bool = False,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """基于SUMO的drtOrtools.py脚本优化按需响应交通(DRT)路线
        
        此工具使用Google OR-Tools求解器优化DRT车辆的路线，以响应动态出行请求。
        
        参数:
        sumo_config: SUMO配置文件路径
        end_time: 模拟结束时间（秒），默认为配置文件中的结束时间或90000秒
        interval: 调度间隔（秒）
        time_limit: 求解器的时间限制（秒）
        cost_type: 成本类型，可选"distance"或"time"
        direct_route_factor: 直接路线因子，用于计算单个接送路线的最大成本（设为-1表示不使用）
        waiting_time: 服务请求的最大等待时间（秒）
        fix_allocation: 是否在第一次解决方案后固定预约分配给车辆
        penalty_factor: 拒绝请求的惩罚因子，可以是"dynamic"或整数
        nogui: 是否使用无界面版本的SUMO运行
        """
        
        if not os.path.exists(sumo_config):
            if ctx:
                ctx.error(f"SUMO配置文件不存在: {sumo_config}")
            return {"success": False, "message": f"SUMO配置文件不存在: {sumo_config}"}
        
        # 设置SUMO二进制文件路径
        sumo_binary = "sumo" if nogui else "sumo-gui"
        sumo_binary_path = os.path.join(os.environ.get("SUMO_HOME", ""), "bin", sumo_binary)
        
        if not os.path.exists(sumo_binary_path):
            if ctx:
                ctx.error(f"SUMO二进制文件不存在: {sumo_binary_path}")
            return {"success": False, "message": f"SUMO二进制文件不存在: {sumo_binary_path}"}
        
        # 转换cost_type为枚举类型
        if cost_type == "distance":
            cost_type_enum = "orToolsDataModel.CostType.DISTANCE"
        elif cost_type == "time":
            cost_type_enum = "orToolsDataModel.CostType.TIME"
        else:
            if ctx:
                ctx.error(f"无效的成本类型: {cost_type}，只允许'distance'或'time'")
            return {"success": False, "message": f"无效的成本类型: {cost_type}，只允许'distance'或'time'"}
        
        # 验证直接路线因子
        if direct_route_factor < 1 and direct_route_factor != -1:
            if ctx:
                ctx.error(f"直接路线因子值无效: {direct_route_factor}，必须大于等于1或为-1")
            return {"success": False, "message": f"直接路线因子值无效: {direct_route_factor}，必须大于等于1或为-1"}
        
        # 验证等待时间
        if waiting_time < 0:
            if ctx:
                ctx.error(f"等待时间值无效: {waiting_time}，必须大于等于0")
            return {"success": False, "message": f"等待时间值无效: {waiting_time}，必须大于等于0"}
        
        # 构建命令
        cmd = [
            "python",
            os.path.join(os.environ.get("SUMO_HOME", ""), "tools", "drt", "drtOrtools.py"),
            "-s", sumo_config,
            "-i", str(interval),
            "-t", str(time_limit),
            "-d", cost_type,
            "-f", str(direct_route_factor),
            "-w", str(waiting_time),
            "-p", str(penalty_factor)
        ]
        
        if end_time is not None:
            cmd.extend(["-e", str(end_time)])
        
        if fix_allocation:
            cmd.append("-a")
        
        if nogui:
            cmd.append("-n")
        
        if ctx:
            cmd.append("-v")
        
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
                    ctx.error(f"drtOrtools.py执行失败: {process.stderr}")
                return {
                    "success": False,
                    "message": f"drtOrtools.py执行失败，返回码: {process.returncode}",
                    "stderr": process.stderr,
                    "stdout": process.stdout
                }
            
            # 解析输出以获取统计信息
            statistics = {}
            try:
                output_lines = process.stdout.split('\n')
                for line in output_lines:
                    if "Reservations waiting" in line:
                        statistics["waiting_reservations"] = line.split(": ")[1]
                    elif "Reservations being picked up" in line:
                        statistics["pickup_reservations"] = line.split(": ")[1]
                    elif "Reservations en route" in line:
                        statistics["enroute_reservations"] = line.split(": ")[1]
            except Exception as e:
                if ctx:
                    ctx.warning(f"无法解析输出统计信息: {str(e)}")
            
            return {
                "success": True,
                "message": "DRT路线优化完成",
                "statistics": statistics,
                "stdout": process.stdout,
                "stderr": process.stderr
            }
            
        except Exception as e:
            if ctx:
                ctx.error(f"执行DRT优化异常: {str(e)}")
            import traceback
            return {
                "success": False,
                "message": f"执行异常: {str(e)}",
                "traceback": traceback.format_exc()
            }

# ────────────────────────────────────────────────────────────────────────────────
# DRT工具资源
# ────────────────────────────────────────────────────────────────────────────────
@drt_mcp.resource("data://drt/config")
def get_drt_config() -> Dict[str, Any]:
    """获取DRT工具配置信息"""
    return {
        "version": "1.0.0",
        "name": "SUMO DRT Tools",
        "description": "SUMO需求响应交通(DRT)工具包，用于按需交通的路线优化和调度",
        "tools": [
            "optimize_drt_routes"
        ],
        "supported_algorithms": [
            "OR-Tools",
            "Google OR-Tools求解器"
        ],
        "cost_types": [
            "distance",
            "time"
        ]
    }

@drt_mcp.resource("data://drt/help")
def get_drt_help() -> Dict[str, str]:
    """获取DRT工具帮助信息"""
    return {
        "optimize_drt_routes": "使用Google OR-Tools求解器优化按需响应交通(DRT)车辆路线，支持动态出行请求调度"
    }

@drt_mcp.resource("data://drt/examples")
def get_drt_examples() -> Dict[str, Any]:
    """获取DRT工具使用示例"""
    return {
        "basic_optimization": {
            "description": "基本DRT路线优化",
            "parameters": {
                "sumo_config": "path/to/drt.sumocfg",
                "interval": 30,
                "time_limit": 10,
                "cost_type": "distance"
            }
        },
        "advanced_optimization": {
            "description": "高级DRT优化（包含等待时间和直接路线因子）",
            "parameters": {
                "sumo_config": "path/to/drt.sumocfg",
                "interval": 60,
                "time_limit": 20,
                "cost_type": "time",
                "direct_route_factor": 2.0,
                "waiting_time": 600,
                "fix_allocation": True
            }
        }
    }

# 如果直接运行此文件，启动DRT工具服务器
if __name__ == "__main__":
    print("启动SUMO DRT工具服务器...")
    drt_mcp.run(transport="sse", host="127.0.0.1", port=8021)
