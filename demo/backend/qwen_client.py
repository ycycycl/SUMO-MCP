#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
QWEN API 客户端
"""

import os
import re
import json
import logging
import requests
from typing import Dict, Any

# 加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # 如果没有安装python-dotenv，跳过
    pass

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from qwen_agent.agents import Assistant
from qwen_agent.utils.output_beautify import typewriter_print

# 导入TodoWrite工具
import todo_write_tool

class QwenClient:
    """QWEN API客户端"""
    
    def __init__(self, api_key=None):
        """
        初始化QWEN客户端
        
        Args:
            api_key: QWEN API密钥，如果不提供则从环境变量获取
        """
        self.api_key = api_key or os.getenv("QWEN_API_KEY")
        if not self.api_key:
            raise ValueError("QWEN API密钥未配置！请设置环境变量 QWEN_API_KEY 或传入 api_key 参数")
        self.bot = self._init_agent()
    
    def _init_agent(self):
        """
        初始化QWEN代理
        
        Returns:
            初始化好的Assistant对象
        """
        # llm_cfg = {
        #     'model': 'qwen3-30b-a3b-thinking-2507',
        #     'model_server': 'dashscope',
        #     'api_key': self.api_key,
        #     'generate_cfg': {
        #         'top_p': 0.8
        #     }
        # }
        llm_cfg = {
            'model': '/data/ycl/HuggingFaceData/Qwen3-8B',
            'model_server': 'http://localhost:14514/v1',
            'generate_cfg': {
                'top_p': 0.8
            }
        }

        # 定义MCP服务配置和工具列表
        tools = [
            {
                "mcpServers": {
                    "sumo_server": {
                        "url": "http://127.0.0.1:8014/sse"
                    }
                }
            },
            'TodoWrite'  # 使用注册的工具名称
        ]

        bot = Assistant(
            llm=llm_cfg,
            name='SUMO仿真操作员',
            description='你是一位SUMO仿真操作员，具有对SUMO仿真进行操作的能力。你必须对所有用户请求都首先使用TodoWrite工具创建任务列表，然后执行任务。',
            system_message='''你是一个专业的SUMO交通仿真助手，能够帮助用户完成各种交通仿真任务。

🚨 **强制要求：永远使用"中文"进行思考**
🚨 **强制要求：对于所有用户请求，你必须首先使用TodoWrite工具创建任务列表！**

🎯 **核心工作原则**：

1. **任务规划优先**: 接到任务后，首先分析需求，制定详细的执行计划，使用TodoWrite工具创建任务列表（输出以[TOOL_CALL]包裹的块）
2. **模块化管理**: 根据任务需求动态加载相应的功能模块
3. **过程透明化**: 使用TodoWrite工具让用户清楚了解任务进展
4. **结果导向**: 确保每个步骤都有明确的输出和验证

📋 **标准工作流程**：

**第1步：任务分析与规划（必须）**
- 仔细分析用户需求，理解任务目标和约束条件
- 将复杂任务分解为具体、可执行的子任务
- 使用TodoWrite工具创建任务列表，让用户了解整个执行计划
- 任务分解应该基于实际需求，不要使用模板化的内容

**第2步：动态模块加载**
- 使用MCP prompt获取完整的工具使用指南
- 根据任务需求智能选择并加载所需的功能模块
- 确保工具链的完整性和有效性

**第3步：逐步执行与反馈**
- 按照计划逐步执行任务
- 及时更新任务状态，保持用户知情
- 遇到问题时主动说明并寻求解决方案

🔧 **TodoWrite工具使用原则**：

**智能任务规划**：
- 根据用户的具体需求动态生成任务列表
- 每个任务项应该具体、可执行、有明确的完成标准
- 避免使用固定模板，要根据实际情况灵活调整

**示例格式**：
```
TodoWrite({"todos": [
    {"id": "1", "content": "根据用户需求制定的具体任务", "status": "pending"},
    {"id": "2", "content": "另一个基于实际需求的任务", "status": "pending"}
]})
```

**状态更新**：
```
TodoWrite({"update": {"id": "1", "status": "in_progress"}})
TodoWrite({"update": {"id": "1", "status": "completed"}})
```

⚠️ **重要：如果你没有首先调用TodoWrite工具，用户将无法看到任务进展，这是不被允许的！**

🔧 **SUMO工具系统**：

**智能工具选择**：
- 通过MCP prompt机制获取完整的工具使用指南
- 根据任务类型智能选择合适的模块和工具
- 支持动态模块加载，按需获取功能

**核心能力领域**：
- 🗺️ **地图数据处理**: OSM下载、格式转换、路网生成
- 🚗 **交通仿真**: 流量生成、信号控制、仿真执行
- 📊 **结果分析**: 数据可视化、性能对比、报告生成
- 🔧 **工具集成**: 多种外部工具的统一调用

💡 **重要提醒**：
- 首次接到任务必须使用TodoWrite创建任务计划
- 使用MCP prompt获取详细的使用指南和模块说明
- 保持任务执行的透明度和可追踪性
- 确保每个步骤都有明确的输出和验证
- 任务规划要基于实际需求，不要死板套用模板

状态说明：
- pending: 待处理
- in_progress: 正在执行  
- completed: 已完成''',
            function_list=tools,
        )
        
        return bot
    
    def refresh_tools(self):
        """刷新工具列表，重新初始化MCP连接"""
        try:
            # 重新初始化MCP工具连接
            tool_config = {
                "mcpServers": {
                    "sumo_server": {
                        "url": "http://127.0.0.1:8014/sse"
                    }
                }
            }
            self.bot._init_tool(tool_config)
            logger.info("工具列表刷新成功")
            return True
        except Exception as e:
            logger.error(f"工具列表刷新失败: {str(e)}")
            return False
    
    def process_query(self, user_input):
        """处理用户查询并返回结构化结果"""
        
        sections = {
            "think": "",
            "toolCalls": [],
            "answer": "",
            "raw_responses": []
        }
        
        messages = [{'role': 'user', 'content': [{'text': user_input}]}]
        
        # 运行模型并处理流式输出
        try:
            # 使用typewriter_print方式处理响应
            previous_text = ""
            full_response = "" # This will accumulate all string parts
            current_section = None
            current_content = ""
            
            # 标记列表
            section_markers = ["[THINK]", "[TOOL_CALL]", "[TOOL_RESPONSE]", "[ANSWER]"]
            
            for response in self.bot.run(messages):
                # Use typewriter_print to accumulate text, as in qwen_test.py
                previous_text = typewriter_print(response, previous_text)
                
                # If the response is a string, add it to full_response for parsing
                if isinstance(response, str):
                    full_response += response
                elif isinstance(response, list): # Handle list responses from Qwen
                    for item in response:
                        if isinstance(item, dict) and 'content' in item:
                            full_response += item.get('content', '')
                else:
                    full_response += str(response) # Convert other types to string
                
                # 检查是否出现了新的标记
                for marker in section_markers:
                    if marker in full_response and (current_section is None or marker != current_section):
                        # 如果有当前正在处理的section，先处理它
                        if current_section and current_content.strip():
                            self._process_completed_section(current_section, current_content, sections)
                        
                        # 开始新的section
                        current_section = marker
                        # 提取当前section的内容
                        section_start = full_response.find(marker)
                        next_marker_pos = len(full_response)
                        for next_marker in section_markers:
                            if next_marker != marker:
                                pos = full_response.find(next_marker, section_start + len(marker))
                                if pos != -1 and pos < next_marker_pos:
                                    next_marker_pos = pos
                        
                        current_content = full_response[section_start + len(marker):next_marker_pos].strip()
                        break
            
            # 处理最后一个section
            if current_section and current_content.strip():
                self._process_completed_section(current_section, current_content, sections)
            
            # 如果没有找到任何内容，使用完整响应作为回答
            if not sections["think"] and not sections["toolCalls"] and not sections["answer"]:
                sections["answer"] = full_response
            
        except Exception as e:
            logger.error(f"处理QWEN API响应时出错: {e}", exc_info=True)
            sections["answer"] = f"处理响应时出错: {str(e)}"
        
        return sections
    
    def _process_completed_section(self, section_marker, content, sections):
        """处理完成的section"""
        if section_marker == "[THINK]":
            sections["think"] = content
        elif section_marker == "[TOOL_CALL]":
            # 解析工具调用
            lines = content.strip().split('\n')
            if len(lines) >= 2:
                tool_name = lines[0].strip()
                try:
                    tool_params = json.loads(lines[1])
                except:
                    tool_params = lines[1]
                
                sections["toolCalls"].append({
                    "name": tool_name,
                    "params": tool_params
                })
        elif section_marker == "[TOOL_RESPONSE]":
            # 解析工具响应
            lines = content.strip().split('\n')
            if len(lines) >= 2:
                tool_name = lines[0].strip()
                try:
                    tool_result = json.loads(lines[1])
                except:
                    tool_result = lines[1]
                
                # 找到对应的tool call并添加响应
                for tool_call in sections["toolCalls"]:
                    if tool_call["name"] == tool_name and "result" not in tool_call:
                        tool_call["result"] = tool_result
                        break
        elif section_marker == "[ANSWER]":
            sections["answer"] = content 