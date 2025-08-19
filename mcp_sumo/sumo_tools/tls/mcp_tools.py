#!/usr/bin/env python3
"""
SUMO交通信号灯工具模块 - 独立的FastMCP服务器
处理交通信号灯配置、优化和管理功能
"""

import os
import subprocess
from typing import Dict, Any, List

from fastmcp import FastMCP, Context

# 设置环境变量
os.environ["SUMO_HOME"] = "D:\Program Files\SUMO"

# ────────────────────────────────────────────────────────────────────────────────
# 创建交通信号灯工具服务器
# ────────────────────────────────────────────────────────────────────────────────
tls_mcp = FastMCP(name="SUMO_TLS_Tools")

# ────────────────────────────────────────────────────────────────────────────────
# TOOL 1: 创建TLS链接CSV
# ────────────────────────────────────────────────────────────────────────────────
@tls_mcp.tool()
async def create_tls_csv(
        net_file: str,
        output_file: str = None,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """基于SUMO的createTlsCsv.py脚本创建TLS链接CSV
        
        参数:
        net_file: SUMO网络文件路径
        output_file: 输出CSV文件路径，如不提供则返回标准输出
        """
        
        cmd = [
            "python",
            os.path.join(os.environ.get("SUMO_HOME", ""), "tools", "tls", "createTlsCsv.py"),
            "-n", net_file
        ]
        
        if ctx:
            ctx.info(f"执行命令: {' '.join(cmd)}")
        
        if output_file:
            # 将输出重定向到文件
            with open(output_file, 'w') as f:
                process = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
            
            return {
                "success": process.returncode == 0,
                "message": "TLS链接CSV创建成功" if process.returncode == 0 else "TLS链接CSV创建失败",
                "stderr": process.stderr,
                "file": output_file if os.path.exists(output_file) else None
            }
        else:
            # 返回标准输出
            process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            return {
                "success": process.returncode == 0,
                "message": "TLS链接CSV创建成功" if process.returncode == 0 else "TLS链接CSV创建失败",
                "stdout": process.stdout,
                "stderr": process.stderr
            }

# ────────────────────────────────────────────────────────────────────────────────
# TOOL 2: TLS CSV信号组处理
# ────────────────────────────────────────────────────────────────────────────────
@tls_mcp.tool()
async def tls_csv_signal_groups(
        net_file: str,
        input_files: str = "",
        output_file: str = "tls.add.xml",
        reverse: bool = False,
        group: bool = False,
        tls_from_net: bool = False,
        tls_filter: str = "",
        delimiter: str = ";",
        make_input_dir: str = "",
        debug: bool = False,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """基于SUMO的tls_csvSignalGroups.py脚本处理信号灯组
        
        参数:
        net_file: SUMO网络文件路径
        input_files: 输入CSV或TLL文件路径，多个文件用逗号分隔
        output_file: 输出文件路径（TLL格式）或生成的CSV文件前缀
        reverse: 是否将TLL格式转换为CSV格式
        group: 转换为CSV格式时，是否将具有相同状态的信号组合并
        tls_from_net: 是否从网络文件中转换TL程序到CSV格式
        tls_filter: 从TLL转换为CSV时限制处理的交通灯列表，逗号分隔
        delimiter: CSV分隔符
        make_input_dir: 从SUMO网络文件创建输入文件模板的目录
        debug: 是否输出调试信息
        """
        
        cmd = [
            "python",
            os.path.join(os.environ.get("SUMO_HOME", ""), "tools", "tls", "tls_csvSignalGroups.py"),
            "-n", net_file,
            "-o", output_file,
            "--delimiter", delimiter
        ]
        
        if input_files:
            cmd.extend(["-i", input_files])
        
        if reverse:
            cmd.append("-r")
        
        if group:
            cmd.append("-g")
        
        if tls_from_net:
            cmd.append("--tls-from-net")
        
        if tls_filter:
            cmd.extend(["--tls-filter", tls_filter])
        
        if make_input_dir:
            cmd.extend(["-m", make_input_dir])
        
        if debug:
            cmd.append("-d")
        
        if ctx:
            ctx.info(f"执行命令: {' '.join(cmd)}")
        
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        result = {
            "success": process.returncode == 0,
            "stdout": process.stdout,
            "stderr": process.stderr
        }
        
        if reverse:
            # 对于反向转换，我们需要检查生成的CSV文件
            if process.returncode == 0:
                if tls_filter:
                    tls_ids = tls_filter.split(",")
                else:
                    # 尝试从网络文件中获取所有交通灯ID
                    try:
                        import sumolib
                        net = sumolib.net.readNet(net_file)
                        tls_ids = [tls.getID() for tls in net.getTrafficLights()]
                    except:
                        tls_ids = []
                
                # 检查生成的CSV文件
                prefix = output_file if output_file else ""
                csv_files = []
                for tls_id in tls_ids:
                    # 注意：这里我们不知道programID，所以只能检查前缀
                    potential_files = [f for f in os.listdir(os.path.dirname(prefix) or ".") 
                                      if f.startswith(f"{tls_id}_") and f.endswith(".csv")]
                    csv_files.extend(potential_files)
                
                result["message"] = "成功将TLL转换为CSV格式" if csv_files else "转换成功，但未找到生成的CSV文件"
                result["files"] = csv_files
            else:
                result["message"] = "TLL转换为CSV格式失败"
        else:
            # 对于正向转换，检查输出文件
            if process.returncode == 0:
                result["message"] = "成功将CSV转换为TLL格式"
                result["file"] = output_file if os.path.exists(output_file) else None
            else:
                result["message"] = "CSV转换为TLL格式失败"
        
        return result

# ────────────────────────────────────────────────────────────────────────────────
# 交通信号灯工具资源
# ────────────────────────────────────────────────────────────────────────────────
@tls_mcp.resource("data://tls/config")
def get_tls_config() -> Dict[str, Any]:
    """获取交通信号灯工具配置信息"""
    return {
        "version": "1.0.0",
        "name": "SUMO Traffic Light Systems Tools",
        "description": "SUMO交通信号灯系统工具包，用于信号灯配置、优化和管理",
        "tools": [
            "create_tls_csv",
            "tls_csv_signal_groups"
        ],
        "supported_formats": [
            "网络文件 (.net.xml)",
            "CSV文件 (.csv)",
            "信号灯配置文件 (.add.xml)"
        ],
        "features": [
            "TLS链接CSV生成",
            "信号组处理",
            "信号灯配置导出",
            "网络分析"
        ]
    }

@tls_mcp.resource("data://tls/help")
def get_tls_help() -> Dict[str, str]:
    """获取交通信号灯工具帮助信息"""
    return {
        "create_tls_csv": "从SUMO网络文件创建交通信号灯链接的CSV文件，用于分析信号灯配置",
        "tls_csv_signal_groups": "处理TLS CSV文件中的信号组，支持多种输出格式和配置选项"
    }

@tls_mcp.resource("data://tls/examples")
def get_tls_examples() -> Dict[str, Any]:
    """获取交通信号灯工具使用示例"""
    return {
        "create_csv": {
            "description": "创建TLS链接CSV",
            "parameters": {
                "net_file": "network.net.xml",
                "output_file": "tls_links.csv"
            }
        },
        "process_signal_groups": {
            "description": "处理信号组",
            "parameters": {
                "csv_file": "tls_data.csv",
                "output_file": "signal_groups.csv",
                "net_file": "network.net.xml",
                "output_dir": "output/"
            }
        },
        "advanced_processing": {
            "description": "高级信号灯处理",
            "parameters": {
                "csv_file": "tls_data.csv",
                "net_file": "network.net.xml",
                "output_dir": "results/",
                "program_id": "custom_program",
                "verbose": True
            }
        }
    }

# 如果直接运行此文件，启动交通信号灯工具服务器
if __name__ == "__main__":
    print("启动SUMO交通信号灯工具服务器...")
    tls_mcp.run(transport="sse", host="127.0.0.1", port=8024)
