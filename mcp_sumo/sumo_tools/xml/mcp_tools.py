#!/usr/bin/env python3
"""
SUMO XML工具模块 - 独立的FastMCP服务器
处理XML文件转换、验证和处理功能
"""

import os
import subprocess
import traceback
from typing import Dict, Any, List

from fastmcp import FastMCP, Context

# 设置环境变量
os.environ["SUMO_HOME"] = "D:\Program Files\SUMO"

# ────────────────────────────────────────────────────────────────────────────────
# 创建XML工具服务器
# ────────────────────────────────────────────────────────────────────────────────
xml_mcp = FastMCP(name="SUMO_XML_Tools")

# ────────────────────────────────────────────────────────────────────────────────
# TOOL 1: CSV转XML
# ────────────────────────────────────────────────────────────────────────────────
@xml_mcp.tool()
async def convert_csv_to_xml(
        csv_file: str,
        output_file: str,
        format_type: str = None,
        xsd_schema: str = None,
        delimiter: str = ";",
        quotechar: str = "",
        skip_root: bool = False,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """基于SUMO的csv2xml.py脚本将CSV文件转换为XML格式
        
        此工具将CSV格式的数据转换为SUMO使用的XML格式，支持多种预定义格式或通过XSD架构自定义格式。
        
        参数:
        csv_file: 输入的CSV文件路径
        output_file: 输出的XML文件路径
        format_type: 预定义的转换格式类型，可选值：
                     "nodes"/"node"/"nod" - 节点格式
                     "edges"/"edge"/"edg" - 边缘格式
                     "connections"/"connection"/"con" - 连接格式
                     "routes"/"vehicles"/"vehicle"/"rou" - 车辆和路线格式
                     "flows"/"flow" - 流量格式
        xsd_schema: XSD架构文件路径，用于自定义格式（与format_type互斥）
        delimiter: CSV文件的字段分隔符
        quotechar: CSV文件的引用字符
        skip_root: 是否省略根元素
        """
        
        if not os.path.exists(csv_file):
            if ctx:
                ctx.error(f"CSV文件不存在: {csv_file}")
            return {"success": False, "message": f"CSV文件不存在: {csv_file}"}
        
        if not format_type and not xsd_schema:
            if ctx:
                ctx.error("必须提供format_type或xsd_schema中的一个")
            return {"success": False, "message": "必须提供format_type或xsd_schema中的一个"}
        
        if format_type and xsd_schema:
            if ctx:
                ctx.error("format_type和xsd_schema不能同时提供")
            return {"success": False, "message": "format_type和xsd_schema不能同时提供"}
        
        if xsd_schema and not os.path.exists(xsd_schema):
            if ctx:
                ctx.error(f"XSD架构文件不存在: {xsd_schema}")
            return {"success": False, "message": f"XSD架构文件不存在: {xsd_schema}"}
        
        # 确保输出目录存在
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        # 构建命令
        cmd = [
            "python",
            os.path.join(os.environ.get("SUMO_HOME", ""), "tools", "xml", "csv2xml.py"),
            csv_file,
            "-o", output_file,
            "-d", delimiter
        ]
        
        if format_type:
            cmd.extend(["-t", format_type])
        
        if xsd_schema:
            cmd.extend(["-x", xsd_schema])
        
        if quotechar:
            cmd.extend(["-q", quotechar])
        
        if skip_root:
            cmd.append("-p")
        
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
                    ctx.error(f"csv2xml.py执行失败: {process.stderr}")
                return {
                    "success": False,
                    "message": f"csv2xml.py执行失败，返回码: {process.returncode}",
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
            
            # 统计XML文件中的元素数量
            element_count = 0
            try:
                with open(output_file, 'r') as f:
                    content = f.read()
                    # 简单估计元素数量（不是精确的XML解析）
                    element_count = content.count('<') - content.count('</') - content.count('/>') - 1
            except Exception as e:
                if ctx:
                    ctx.warning(f"无法统计XML元素数量: {str(e)}")
            
            return {
                "success": True,
                "message": f"CSV成功转换为XML，包含约{element_count}个元素",
                "files": {
                    "output": output_file
                },
                "statistics": {
                    "element_count": element_count
                }
            }
            
        except Exception as e:
            if ctx:
                ctx.error(f"执行CSV转XML异常: {str(e)}")
            import traceback
            return {
                "success": False,
                "message": f"执行异常: {str(e)}",
                "traceback": traceback.format_exc()
            }
    
# ────────────────────────────────────────────────────────────────────────────────
# TOOL 2: XML转CSV  
# ────────────────────────────────────────────────────────────────────────────────
@xml_mcp.tool()
async def convert_xml_to_csv(
        xml_file: str,
        output_file: str = None,
        separator: str = ";",
        quotechar: str = "",
        xsd_schema: str = None,
        validate: bool = False,
        split: bool = False,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """基于SUMO的xml2csv.py脚本将XML文件转换为CSV格式
        
        此工具将SUMO使用的XML格式数据转换为CSV格式，便于数据分析和处理。
        
        参数:
        xml_file: 输入的XML文件路径
        output_file: 输出的CSV文件路径，如果不提供则使用输入文件名加上.csv后缀
        separator: CSV文件的字段分隔符
        quotechar: CSV文件的引用字符
        xsd_schema: XSD架构文件路径，用于确定XML结构
        validate: 是否启用XSD架构验证（需要lxml库支持）
        split: 是否按第一层级分割为多个文件（不能与流输出一起使用）
        """
        
        if not os.path.exists(xml_file):
            if ctx:
                ctx.error(f"XML文件不存在: {xml_file}")
            return {"success": False, "message": f"XML文件不存在: {xml_file}"}
        
        if xsd_schema and not os.path.exists(xsd_schema):
            if ctx:
                ctx.error(f"XSD架构文件不存在: {xsd_schema}")
            return {"success": False, "message": f"XSD架构文件不存在: {xsd_schema}"}
        
        # 如果未提供输出文件，则使用输入文件名加上.csv后缀
        if not output_file:
            output_file = os.path.splitext(xml_file)[0] + ".csv"
        
        # 确保输出目录存在
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        # 构建命令
        cmd = [
            "python",
            os.path.join(os.environ.get("SUMO_HOME", ""), "tools", "xml", "xml2csv.py"),
            xml_file,
            "-o", output_file,
            "-s", separator
        ]
        
        if quotechar:
            cmd.extend(["-q", quotechar])
        
        if xsd_schema:
            cmd.extend(["-x", xsd_schema])
        
        if validate:
            cmd.append("-a")
        
        if split:
            cmd.append("-p")
        
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
                    ctx.error(f"xml2csv.py执行失败: {process.stderr}")
                return {
                    "success": False,
                    "message": f"xml2csv.py执行失败，返回码: {process.returncode}",
                    "stderr": process.stderr,
                    "stdout": process.stdout
                }
            
            # 检查输出文件是否存在
            output_files = []
            if split:
                # 如果使用了分割选项，可能会生成多个文件
                base_dir = os.path.dirname(output_file)
                base_name = os.path.basename(output_file)
                if not base_name.endswith(".csv"):
                    base_name += ".csv"
                
                # 尝试查找生成的文件
                for file in os.listdir(base_dir):
                    if file.startswith(base_name.replace(".csv", "")) and file.endswith(".csv"):
                        output_files.append(os.path.join(base_dir, file))
            else:
                # 单个输出文件
                if os.path.exists(output_file):
                    output_files.append(output_file)
                else:
                    # 检查是否自动添加了.csv后缀
                    csv_output = output_file if output_file.endswith(".csv") else output_file + ".csv"
                    if os.path.exists(csv_output):
                        output_files.append(csv_output)
            
            if not output_files:
                if ctx:
                    ctx.error(f"未找到输出文件")
                return {
                    "success": False,
                    "message": f"未找到输出文件",
                    "stderr": process.stderr,
                    "stdout": process.stdout
                }
            
            # 统计CSV文件的行数和列数
            statistics = {}
            for file in output_files:
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        if lines:
                            row_count = len(lines)
                            col_count = len(lines[0].split(separator))
                            file_name = os.path.basename(file)
                            statistics[file_name] = {
                                "row_count": row_count,
                                "column_count": col_count
                            }
                except Exception as e:
                    if ctx:
                        ctx.warning(f"无法统计CSV文件 {file} 的行列数: {str(e)}")
            
            return {
                "success": True,
                "message": f"XML成功转换为CSV，生成了{len(output_files)}个文件",
                "files": output_files,
                "statistics": statistics
            }
            
        except Exception as e:
            if ctx:
                ctx.error(f"执行XML转CSV异常: {str(e)}")
            import traceback
            return {
                "success": False,
                "message": f"执行异常: {str(e)}",
                "traceback": traceback.format_exc()
            }

# ────────────────────────────────────────────────────────────────────────────────
# TOOL 3: 修改XML属性
# ────────────────────────────────────────────────────────────────────────────────
@xml_mcp.tool()
async def change_xml_attribute(
        xml_file: str,
        output_file: str,
        attribute: str,
        value: str = None,
        tag: str = None,
        upper_limit: float = None,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """基于SUMO的changeAttribute.py脚本修改XML文件中的属性
        
        此工具可以设置、修改或删除XML文件中指定元素的属性值。
        
        参数:
        xml_file: 输入的XML文件路径
        output_file: 修改后的XML输出文件路径
        attribute: 要修改的属性名称
        value: 要设置的新属性值，如果不提供则删除该属性
        tag: 要修改的XML标签名称，如果不提供则修改所有包含该属性的元素
        upper_limit: 属性值的上限，如果当前值大于此上限则将其设为上限值
        """
        
        if not os.path.exists(xml_file):
            if ctx:
                ctx.error(f"XML文件不存在: {xml_file}")
            return {"success": False, "message": f"XML文件不存在: {xml_file}"}
        
        # 确保输出目录存在
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        # 构建命令
        cmd = [
            "python",
            os.path.join(os.environ.get("SUMO_HOME", ""), "tools", "xml", "changeAttribute.py"),
            "-f", xml_file,
            "-o", output_file,
            "-a", attribute
        ]
        
        if tag:
            cmd.extend(["-t", tag])
        
        if value is not None:
            cmd.extend(["-v", value])
        
        if upper_limit is not None:
            cmd.extend(["-u", str(upper_limit)])
        
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
                    ctx.error(f"changeAttribute.py执行失败: {process.stderr}")
                return {
                    "success": False,
                    "message": f"changeAttribute.py执行失败，返回码: {process.returncode}",
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
            
            # 统计修改的元素数量
            changes_count = 0
            try:
                import xml.etree.ElementTree as ET
                
                # 解析原始文件和修改后的文件
                tree_original = ET.parse(xml_file)
                tree_modified = ET.parse(output_file)
                
                # 获取原始和修改后的属性值
                original_values = {}
                modified_values = {}
                
                # 如果指定了标签，只检查该标签的元素
                tag_filter = tag if tag else "*"
                
                # 统计原始文件中的属性
                for elem in tree_original.findall(f".//{tag_filter}"):
                    elem_id = elem.get("id", "")  # 使用id属性作为元素标识，如果有的话
                    if attribute in elem.attrib:
                        original_values[elem_id] = elem.get(attribute)
                
                # 统计修改后文件中的属性
                for elem in tree_modified.findall(f".//{tag_filter}"):
                    elem_id = elem.get("id", "")  # 使用id属性作为元素标识，如果有的话
                    if attribute in elem.attrib:
                        modified_values[elem_id] = elem.get(attribute)
                        
                # 统计变化
                for elem_id in set(original_values.keys()) | set(modified_values.keys()):
                    orig_val = original_values.get(elem_id)
                    mod_val = modified_values.get(elem_id)
                    
                    if orig_val != mod_val:
                        changes_count += 1
                        
            except Exception as e:
                if ctx:
                    ctx.warning(f"无法统计修改的元素数量: {str(e)}")
            
            operation = "设置" if value is not None else "删除" if upper_limit is None else "限制"
            
            return {
                "success": True,
                "message": f"成功{operation} XML 属性 {attribute}，影响了约 {changes_count} 个元素",
                "files": {
                    "output": output_file
                },
                "statistics": {
                    "changes_count": changes_count
                }
            }
            
        except Exception as e:
            if ctx:
                ctx.error(f"执行XML属性修改异常: {str(e)}")
            import traceback
            return {
                "success": False,
                "message": f"执行异常: {str(e)}",
                "traceback": traceback.format_exc()
            }

    # ────────────────────────────────────────────────────────────────────────────────
# TOOL 4: 过滤XML元素
# ────────────────────────────────────────────────────────────────────────────────
@xml_mcp.tool()
async def filter_xml_elements(
        xml_file: str,
        output_file: str,
        tag: str,
        attribute: str = None,
        remove_values: str = None,
        keep_values: str = None,
        remove_interval: str = None,
        keep_interval: str = None,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """基于SUMO的filterElements.py脚本过滤XML文件中的元素
        
        此工具可以根据属性值从XML文件中删除特定元素。
        
        参数:
        xml_file: 输入的XML文件路径
        output_file: 过滤后的XML输出文件路径
        tag: 要过滤的XML标签名称
        attribute: 用于过滤的属性名称，如果不提供则删除所有指定标签的元素
        remove_values: 要删除的属性值列表，以逗号分隔
        keep_values: 要保留的属性值列表，以逗号分隔（与remove_values互斥）
        remove_interval: 要删除的属性值区间，格式为"最小值,最大值"
        keep_interval: 要保留的属性值区间，格式为"最小值,最大值"（与remove_interval互斥）
        """
        
        if not os.path.exists(xml_file):
            if ctx:
                ctx.error(f"XML文件不存在: {xml_file}")
            return {"success": False, "message": f"XML文件不存在: {xml_file}"}
        
        # 检查互斥参数
        if remove_values and keep_values:
            if ctx:
                ctx.error("remove_values和keep_values不能同时提供")
            return {"success": False, "message": "remove_values和keep_values不能同时提供"}
        
        if remove_interval and keep_interval:
            if ctx:
                ctx.error("remove_interval和keep_interval不能同时提供")
            return {"success": False, "message": "remove_interval和keep_interval不能同时提供"}
        
        # 确保输出目录存在
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        # 构建命令
        cmd = [
            "python",
            os.path.join(os.environ.get("SUMO_HOME", ""), "tools", "xml", "filterElements.py"),
            "-f", xml_file,
            "-o", output_file,
            "-t", tag
        ]
        
        if attribute:
            cmd.extend(["-a", attribute])
        
        if remove_values:
            cmd.extend(["-r", remove_values])
        
        if keep_values:
            cmd.extend(["-k", keep_values])
        
        if remove_interval:
            cmd.extend(["-x", remove_interval])
        
        if keep_interval:
            cmd.extend(["-i", keep_interval])
        
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
                    ctx.error(f"filterElements.py执行失败: {process.stderr}")
                return {
                    "success": False,
                    "message": f"filterElements.py执行失败，返回码: {process.returncode}",
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
            
            # 统计过滤前后的元素数量
            original_count = 0
            filtered_count = 0
            removed_count = 0
            
            try:
                import xml.etree.ElementTree as ET
                
                # 解析原始文件和过滤后的文件
                tree_original = ET.parse(xml_file)
                tree_filtered = ET.parse(output_file)
                
                # 统计原始文件中指定标签的元素数量
                for elem in tree_original.findall(f".//{tag}"):
                    original_count += 1
                
                # 统计过滤后文件中指定标签的元素数量
                for elem in tree_filtered.findall(f".//{tag}"):
                    filtered_count += 1
                
                # 计算被移除的元素数量
                removed_count = original_count - filtered_count
                
            except Exception as e:
                if ctx:
                    ctx.warning(f"无法统计过滤的元素数量: {str(e)}")
            
            filter_type = ""
            if attribute:
                if remove_values:
                    filter_type = f"删除属性 {attribute} 值为 {remove_values} 的元素"
                elif keep_values:
                    filter_type = f"保留属性 {attribute} 值为 {keep_values} 的元素"
                elif remove_interval:
                    filter_type = f"删除属性 {attribute} 值在区间 {remove_interval} 内的元素"
                elif keep_interval:
                    filter_type = f"保留属性 {attribute} 值在区间 {keep_interval} 内的元素"
                else:
                    filter_type = f"删除所有具有属性 {attribute} 的元素"
            else:
                filter_type = f"删除所有 {tag} 元素"
            
            return {
                "success": True,
                "message": f"成功过滤XML元素，{filter_type}，共移除 {removed_count} 个元素",
                "files": {
                    "output": output_file
                },
                "statistics": {
                    "original_count": original_count,
                    "filtered_count": filtered_count,
                    "removed_count": removed_count
                }
            }
            
        except Exception as e:
            if ctx:
                ctx.error(f"执行XML元素过滤异常: {str(e)}")
            import traceback
            return {
                "success": False,
                "message": f"执行异常: {str(e)}",
                "traceback": traceback.format_exc()
            }

# ────────────────────────────────────────────────────────────────────────────────
# XML工具资源
# ────────────────────────────────────────────────────────────────────────────────
@xml_mcp.resource("data://xml/config")
def get_xml_config() -> Dict[str, Any]:
    """获取XML工具配置信息"""
    return {
        "version": "1.0.0",
        "name": "SUMO XML Tools",
        "description": "SUMO XML工具包，用于XML文件转换、验证和处理",
        "tools": [
            "convert_csv_to_xml",
            "convert_xml_to_csv", 
            "change_xml_attribute",
            "filter_xml_elements"
        ],
        "supported_formats": {
            "input": ["CSV", "XML"],
            "output": ["CSV", "XML"]
        }
    }

@xml_mcp.resource("data://xml/help")
def get_xml_help() -> Dict[str, str]:
    """获取XML工具帮助信息"""
    return {
        "convert_csv_to_xml": "将CSV文件转换为SUMO使用的XML格式",
        "convert_xml_to_csv": "将SUMO的XML格式数据转换为CSV格式",
        "change_xml_attribute": "修改XML文件中元素的属性值",
        "filter_xml_elements": "根据条件过滤XML文件中的元素"
    }

# 如果直接运行此文件，启动XML工具服务器
if __name__ == "__main__":
    print("启动SUMO XML工具服务器...")
    xml_mcp.run(transport="sse", host="127.0.0.1", port=8019)
