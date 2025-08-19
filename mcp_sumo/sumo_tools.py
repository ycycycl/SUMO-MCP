import os
os.environ["SUMO_HOME"] = "D:\Program Files\SUMO"
from typing import Any, Dict, List

import importlib
import subprocess
import time
from datetime import datetime
from fastmcp import FastMCP, Context

# ────────────────────────────────────────────────────────────────────────────────
# 初始化 FastMCP
# ────────────────────────────────────────────────────────────────────────────────
mcp = FastMCP(name = "sumo_tools")

# ==================== 子模块动态导入 ====================
# 可用的子模块配置
AVAILABLE_MODULES = {
    "auxiliary": {
        "module_name": "auxiliary_tools",
        "server_var": "auxiliary_mcp", 
        "description": "辅助工具模块 - 包含OSM下载、随机行程生成、交通信号灯优化、仿真配置、仿真运行、结果对比等功能",
        "tools": ["osm_download_by_place", "generate_random_trips", "tls_cycle_adaptation", "tls_coordinator", "create_sumo_config", "show_picture", "run_simulation", "compare_simulation_results"]
    },
    "detector": {
        "module_name": "sumo_tools.detector.mcp_tools",
        "server_var": "detector_mcp",
        "description": "检测器工具模块 - 处理交通流量检测、数据转换和分析",
        "tools": ["convert_flow_to_edge_data", "convert_edge_data_to_flow", "map_detector_coordinates", "aggregate_flows"]
    },
    "district": {
        "module_name": "sumo_tools.district.mcp_tools",
        "server_var": "district_mcp",
        "description": "区域工具模块 - 处理交通分析区(TAZ)的生成、过滤和分析",
        "tools": ["filter_districts_by_vehicle_class", "generate_grid_districts", "generate_station_districts"]
    },
    "drt": {
        "module_name": "sumo_tools.drt.mcp_tools",
        "server_var": "drt_mcp",
        "description": "需求响应交通(DRT)工具模块 - 按需交通路线优化和调度",
        "tools": ["optimize_drt_routes"]
    },
    "xml": {
        "module_name": "sumo_tools.xml.mcp_tools",
        "server_var": "xml_mcp",
        "description": "XML处理工具模块 - XML文件处理和转换",
        "tools": ["convert_csv_to_xml", "convert_xml_to_csv", "change_xml_attribute", "filter_xml_elements"]
    },
    "visualization": {
        "module_name": "sumo_tools.visualization.mcp_tools",
        "server_var": "visualization_mcp",
        "description": "可视化工具模块 - 生成图表和可视化结果",
        "tools": ["plot_csv_bars", "plot_csv_pie", "plot_csv_timeline", "plot_net_dump", "plot_net_selection", "plot_net_speeds", "plot_net_traffic_lights", "plot_summary", "plot_xml_attributes"]
    },
    "tls": {
        "module_name": "sumo_tools.tls.mcp_tools",
        "server_var": "tls_mcp",
        "description": "交通信号灯工具模块 - 信号灯配置和优化",
        "tools": ["create_tls_csv", "tls_csv_signal_groups"]
    },
    "turn_defs": {
        "module_name": "sumo_tools.turn_defs.mcp_tools",
        "server_var": "turn_defs_mcp",
        "description": "转向定义工具模块 - 处理交通转向规则",
        "tools": ["generate_turn_ratios", "turn_count_to_edge_count", "turn_file_to_edge_relations"]
    },
    "importtool": {
        "module_name": "sumo_tools.importtool.mcp_tools",
        "server_var": "importtool_mcp",
        "description": "导入工具模块 - 支持多种外部数据格式转换",
        "tools": ["citybrain_flow_import", "citybrain_infostep_import", "citybrain_road_import", "gtfs2fcd_import", "gtfs2pt_import", "vissim_parse_routes", "visum_convert_edge_types", "dxf2jupedsim_import"]
    },
    "bin": {
        "module_name": "sumo_tools.bin.mcp_tools",
        "server_var": "bin_mcp",
        "description": "路网工具模块 - 路网生成、路网转换和OD生成",
        "tools": ["netconvert", "netgenerate", "od2trips"]
    }
}

# 已挂载的模块记录
mounted_modules = set()

@mcp.tool()
async def list_available_modules() -> Dict[str, Any]:
    """列出所有可用的子模块及其状态
    
    Returns:
        包含模块信息和挂载状态的字典
    """
    modules_info = {}
    for module_id, config in AVAILABLE_MODULES.items():
        is_mounted = module_id in mounted_modules
        
        # 如果模块已挂载，生成实际的工具调用名称
        actual_tool_names = []
        if is_mounted:
            actual_tool_names = [f"sumo_server-{module_id}_{tool}" for tool in config["tools"]]
        
        modules_info[module_id] = {
            "description": config["description"],
            "tools": config["tools"],
            "actual_tool_names": actual_tool_names if is_mounted else [],
            "is_mounted": is_mounted,
            "mount_status": "已挂载" if is_mounted else "未挂载",
            "tool_call_format": f"sumo_server-{module_id}_{{tool_name}}" if is_mounted else f"需要先挂载模块"
        }
    
    usage_instruction = """
📋 工具调用说明:
挂载模块后，工具调用格式为: sumo_server-{module_id}_{tool_name}
例如:
- auxiliary模块的osm_download_by_place工具 → sumo_server-auxiliary_osm_download_by_place
- detector模块的convert_flow_to_edge_data工具 → sumo_server-detector_convert_flow_to_edge_data
- xml模块的convert_csv_to_xml工具 → sumo_server-xml_convert_csv_to_xml
"""
    
    return {
        "usage_instruction": usage_instruction,
        "available_modules": modules_info,
        "total_modules": len(AVAILABLE_MODULES),
        "mounted_count": len(mounted_modules),
        "unmounted_count": len(AVAILABLE_MODULES) - len(mounted_modules)
    }

@mcp.tool()
async def mount_module(module_ids: List[str]) -> Dict[str, Any]:
    """动态挂载子模块（支持单个或多个）
    
    Args:
        module_ids: 要挂载的模块ID列表，支持单个模块或多个模块
    
    Returns:
        挂载结果信息
    """
    import importlib
    from datetime import datetime
    
    # 输入验证
    if not module_ids:
        return {
            "success": False,
            "message": "模块ID列表不能为空",
            "error_type": "ValidationError"
        }
    
    # 如果传入的是字符串，转换为列表
    if isinstance(module_ids, str):
        module_ids = [module_ids]
    elif not isinstance(module_ids, list):
        return {
            "success": False,
            "message": "模块ID必须是字符串或字符串列表",
            "error_type": "ValidationError"
        }
    
    start_time = datetime.now()
    results = []
    success_count = 0
    failed_count = 0
    
    def _mount_single_module(module_id: str) -> Dict[str, Any]:
        """挂载单个模块的内部函数"""
        # 输入验证
        if not module_id or not isinstance(module_id, str):
            return {
                "success": False,
                "message": "模块ID不能为空且必须是字符串",
                "error_type": "ValidationError"
            }
        
        if module_id not in AVAILABLE_MODULES:
            return {
                "success": False,
                "message": f"模块 '{module_id}' 不存在",
                "available_modules": list(AVAILABLE_MODULES.keys()),
                "suggestion": f"请使用 list_available_modules() 查看所有可用模块"
            }
        
        # 检查是否已挂载
        if module_id in mounted_modules:
            return {
                "success": False,
                "message": f"模块 '{module_id}' 已经挂载，无法重复挂载",
                "mounted_modules": list(mounted_modules)
            }
        
        config = AVAILABLE_MODULES[module_id]
        prefix = module_id  # FastMCP会自动添加下划线
        
        module_start_time = datetime.now()
        
        try:
            # 动态导入模块
            module = importlib.import_module(config["module_name"])
            
            # 只处理现代化模块（使用FastMCP服务器挂载）
            if "server_var" not in config:
                return {
                    "success": False,
                    "message": f"模块 '{module_id}' 配置无效：缺少 'server_var'",
                    "error_type": "ConfigurationError",
                    "suggestion": "请检查 AVAILABLE_MODULES 配置中的模块定义"
                }
                
            if not hasattr(module, config["server_var"]):
                return {
                    "success": False,
                    "message": f"模块 '{module_id}' 中未找到服务器变量 '{config['server_var']}'",
                    "error_type": "AttributeError",
                    "suggestion": f"请检查 {config['module_name']} 文件中是否定义了 {config['server_var']}"
                }
            
            server = getattr(module, config["server_var"])
            
            # 验证服务器对象
            if not hasattr(server, 'mount') and not hasattr(server, '_tools'):
                return {
                    "success": False,
                    "message": f"'{config['server_var']}' 不是有效的FastMCP服务器对象",
                    "error_type": "ValidationError"
                }
            
            # 执行挂载
            mcp.mount(server, prefix=prefix)
            mounted_modules.add(module_id)
            
            # 统计工具数量
            tools_count = len(server._tools) if hasattr(server, '_tools') else len(config.get("tools", []))
            
            module_end_time = datetime.now()
            load_time = (module_end_time - module_start_time).total_seconds()
        
            return {
                "success": True, 
                "message": f"成功挂载模块 '{module_id}'",
                "module_info": {
                    "id": module_id,
                    "name": server.name,
                    "prefix": prefix,
                    "tools_count": tools_count,
                    "tools": config["tools"],
                    "description": config["description"],
                    "load_time_seconds": round(load_time, 3),
                    "mounted_at": module_end_time.isoformat()
                }
            }
                
        except ImportError as e:
            return {
                "success": False,
                "message": f"导入模块 '{module_id}' 失败: {str(e)}",
                "error_type": "ImportError",
                "module_path": config["module_name"],
                "suggestion": f"请检查模块文件 {config['module_name'].replace('.', '/')} 是否存在且语法正确"
            }
        except AttributeError as e:
            return {
                "success": False,
                "message": f"模块 '{module_id}' 缺少必要的属性: {str(e)}",
                "error_type": "AttributeError",
                "suggestion": "请检查模块文件中是否正确定义了所需的变量或函数"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"挂载模块 '{module_id}' 时发生未预期的错误: {str(e)}",
                "error_type": type(e).__name__,
                "suggestion": "这可能是一个系统级错误，请检查日志或联系开发者"
            }
    
    # 处理每个模块
    for module_id in module_ids:
        result = _mount_single_module(module_id)
        results.append({
            "module_id": module_id,
            "success": result["success"],
            "message": result["message"],
            "details": result.get("module_info") if result["success"] else result
        })
        
        if result["success"]:
            success_count += 1
        else:
            failed_count += 1
    
    end_time = datetime.now()
    total_time = (end_time - start_time).total_seconds()
    
    return {
        "success": failed_count == 0,
        "message": f"批量挂载完成：成功 {success_count} 个，失败 {failed_count} 个",
        "summary": {
            "total_requested": len(module_ids),
            "success_count": success_count,
            "failed_count": failed_count,
            "total_time_seconds": round(total_time, 3),
            "completed_at": end_time.isoformat()
        },
        "details": results,
        "system_status": {
            "total_mounted": len(mounted_modules),
            "available_modules": len(AVAILABLE_MODULES)
        }
    }

@mcp.tool()
async def get_module_status(module_id: str = None) -> Dict[str, Any]:
    """获取模块状态信息
    
    Args:
        module_id: 可选的模块ID，如果不提供则返回所有模块状态
    
    Returns:
        模块状态信息
    """
    if module_id:
        # 获取单个模块状态
        if module_id not in AVAILABLE_MODULES:
            return {
                "success": False,
                "message": f"模块 '{module_id}' 不存在",
                "available_modules": list(AVAILABLE_MODULES.keys())
            }
        
        config = AVAILABLE_MODULES[module_id]
        is_mounted = module_id in mounted_modules
        
        return {
            "success": True,
            "module_info": {
                "id": module_id,
                "description": config["description"],
                "tools": config["tools"],
                "tools_count": len(config["tools"]),
                "module_type": "modern" if "server_var" in config else "legacy",
                "is_mounted": is_mounted,
                "status": "已挂载" if is_mounted else "未挂载"
            }
        }
    else:
        # 获取所有模块状态
        modules_status = {}
        for mid, config in AVAILABLE_MODULES.items():
            is_mounted = mid in mounted_modules
            modules_status[mid] = {
                "description": config["description"],
                "tools_count": len(config["tools"]),
                "module_type": "modern" if "server_var" in config else "legacy",
                "is_mounted": is_mounted,
                "status": "已挂载" if is_mounted else "未挂载"
            }
        
        return {
            "success": True,
            "system_overview": {
                "total_modules": len(AVAILABLE_MODULES),
                "mounted_modules": len(mounted_modules),
                "unmounted_modules": len(AVAILABLE_MODULES) - len(mounted_modules),
                "mounted_list": list(mounted_modules),
                "unmounted_list": [mid for mid in AVAILABLE_MODULES.keys() if mid not in mounted_modules]
            },
            "modules_status": modules_status
        }

@mcp.prompt()
def get_guidance() -> str:
    """
    SUMO工具使用指南 - 为LLM提供完整的使用说明
    
    Returns:
        完整的SUMO工具使用指南
    """
    return """# SUMO工具使用指南

## 🎯 核心原则
1. **路径使用绝对路径** - 避免相对路径导致的错误
2. **按需加载模块** - 根据任务需求动态加载功能模块
3. **先规划后执行** - 了解任务需求后再选择合适的工具

## 📦 动态模块管理系统

### 第1步：查看可用模块
```
list_available_modules()
```

### 第2步：根据任务需求，批量加载模块
```
mount_module(["detector"])      # 流量检测、数据转换和分析
mount_module(["auxiliary"])     # OSM下载、随机行程生成、交通信号灯优化
mount_module(["xml"])          # XML文件处理和转换
mount_module(["visualization"]) # 图表生成和可视化
mount_module(["tls"])          # 交通信号灯配置和优化
mount_module(["district"])     # 交通分析区(TAZ)处理
mount_module(["drt"])          # 需求响应交通路线优化
mount_module(["turn_defs"])    # 交通转向规则处理
mount_module(["importtool"])   # 外部数据格式转换
mount_module(["bin"])          # 路网生成和转换
```

### 第3步：调用模块工具
**重要：工具调用格式为 sumo_server-{module_id}_{tool_name}**
```
# auxiliary模块工具调用示例
sumo_server-auxiliary_osm_download_by_place(place_name="北京市")
sumo_server-auxiliary_generate_random_trips(net_file="network.net.xml")
sumo_server-auxiliary_run_simulation(net_file="network.net.xml", route_file="routes.rou.xml", control_type="webster")
sumo_server-auxiliary_compare_simulation_results(tripinfo_files='["fixed/tripinfo.xml","webster/tripinfo.xml"]', labels='["固定配时","Webster优化"]')
```

## 🔧 各模块功能说明

### 🚦 auxiliary - 辅助工具
- `osm_download_by_place`: 从OpenStreetMap下载指定地点的地图数据
- `generate_random_trips`: 生成随机交通流量
- `tls_cycle_adaptation`: 交通信号灯周期自适应优化
- `tls_coordinator`: 交通信号灯协调优化
- `create_sumo_config`: 创建SUMO仿真配置文件
- `show_picture`: 向用户显示图片
- `run_simulation`: 运行SUMO交通仿真（支持固定配时、感应控制、Webster优化、绿波协调）
- `compare_simulation_results`: 对比多个仿真结果的性能指标并生成图表

### 📊 detector - 流量检测
- `convert_flow_to_edge_data`: 将流量数据转换为边数据
- `convert_edge_data_to_flow`: 将边数据转换为流量数据
- `map_detector_coordinates`: 映射检测器坐标
- `aggregate_flows`: 聚合流量数据

### 📝 xml - XML处理
- `convert_csv_to_xml`: CSV转XML格式
- `convert_xml_to_csv`: XML转CSV格式
- `change_xml_attribute`: 修改XML属性
- `filter_xml_elements`: 过滤XML元素

### 📈 visualization - 可视化
- `plot_csv_bars`: 生成柱状图
- `plot_csv_pie`: 生成饼图
- `plot_csv_timeline`: 生成时间线图
- `plot_net_*`: 各种路网可视化

### 🏗️ bin - 路网工具
- `netconvert`: 路网格式转换
- `netgenerate`: 生成路网
- `od2trips`: OD矩阵转行程文件

### 错误处理
- 如果模块加载失败，检查模块ID是否正确
- 如果工具不可用，确保相关模块已加载
- 遇到路径问题时，使用绝对路径

记住：高效的模块管理是成功完成SUMO任务的关键！"""

if __name__ == "__main__":
    # 启动组合MCP服务器Base Module
    try:
        mcp.run(
            transport="sse",
            host="127.0.0.1", 
            port=8014
        )
    except Exception as e:
        print(f"服务器启动失败: {str(e)}")
        print("尝试默认传输方法...")
        mcp.run()