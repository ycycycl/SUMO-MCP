#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
TodoWrite工具 - 用于管理任务列表
"""

import json
import logging
import requests
from typing import Union

from qwen_agent.tools.base import BaseTool, register_tool

# 配置日志
logger = logging.getLogger(__name__)


@register_tool('TodoWrite')
class TodoWriteTool(BaseTool):
    description = '【必须使用】管理任务列表。首次规划时传入完整todos列表，后续更新时只传入变化的任务。'
    parameters = [
        {
            'name': 'todos',
            'type': 'array',
            'description': '完整的待办事项列表，用于首次创建todolist',
            'required': False,
            'items': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'string', 'description': '任务的唯一标识符'},
                    'content': {'type': 'string', 'description': '任务的具体内容描述'},
                    'status': {'type': 'string', 'enum': ['pending', 'in_progress', 'completed'], 'description': '任务状态'}
                },
                'required': ['id', 'content', 'status']
            }
        },
        {
            'name': 'update',
            'type': 'object',
            'description': '增量更新单个任务，用于更新任务状态',
            'required': False,
            'properties': {
                'id': {'type': 'string', 'description': '要更新的任务ID'},
                'status': {'type': 'string', 'enum': ['pending', 'in_progress', 'completed'], 'description': '新的任务状态'},
                'content': {'type': 'string', 'description': '可选：更新任务内容'}
            }
        }
    ]

    def call(self, params: Union[str, dict], **kwargs) -> str:
        """
        调用TodoWrite工具更新任务列表
        
        Args:
            params: 包含todos列表的参数
            
        Returns:
            str: 操作结果消息
        """
        try:
            # 验证并解析参数
            params = self._verify_json_format_args(params)
            
            todos = params.get('todos', [])
            update = params.get('update', None)
            
            # 必须提供todos或update其中一个参数
            if not todos and not update:
                return "错误：必须提供todos（完整列表）或update（增量更新）参数"
            
            if todos and update:
                return "错误：不能同时提供todos和update参数，请选择其中一种方式"
            
            # 处理完整列表更新
            if todos:
                if not isinstance(todos, list):
                    return "错误：todos参数必须是一个列表"
                
                # 验证每个todo项的格式
                for i, todo in enumerate(todos):
                    if not isinstance(todo, dict):
                        return f"错误：第{i+1}个todo项必须是字典格式"
                    
                    required_fields = ['id', 'content', 'status']
                    for field in required_fields:
                        if field not in todo:
                            return f"错误：第{i+1}个todo项缺少必需字段：{field}"
                    
                    # 验证status值
                    if todo['status'] not in ['pending', 'in_progress', 'completed']:
                        return f"错误：第{i+1}个todo项的status值无效：{todo['status']}"
                
                return self._update_full_todos(todos)
            
            # 处理增量更新
            if update:
                if not isinstance(update, dict):
                    return "错误：update参数必须是字典格式"
                
                # 验证必需字段
                if 'id' not in update:
                    return "错误：update参数缺少必需的id字段"
                
                if 'status' not in update:
                    return "错误：update参数缺少必需的status字段"
                
                # 验证status值
                if update['status'] not in ['pending', 'in_progress', 'completed']:
                    return f"错误：update参数的status值无效：{update['status']}"
                
                return self._update_single_todo(update)
                
        except requests.exceptions.RequestException as e:
            logger.error(f"TodoWrite网络请求失败: {e}")
            return f"❌ 网络连接失败，无法更新TodoList: {str(e)}"
        except json.JSONDecodeError as e:
            logger.error(f"TodoWrite参数解析失败: {e}")
            return f"❌ 参数格式错误: {str(e)}"
        except Exception as e:
            logger.error(f"TodoWrite工具调用失败: {e}")
            return f"❌ TodoWrite工具调用失败: {str(e)}"
    
    def _update_full_todos(self, todos):
        """完整更新todolist"""
        try:
            response = requests.post(
                'http://localhost:5000/api/todos',
                json={'todos': todos},
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    return f"✅ TodoList已创建，共{len(todos)}项任务"
                else:
                    error_msg = result.get('message', '未知错误')
                    logger.error(f"TodoList完整更新失败: {error_msg}")
                    return f"❌ TodoList更新失败: {error_msg}"
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"TodoList API调用失败: {error_msg}")
                return f"❌ API调用失败: {error_msg}"
        except Exception as e:
            logger.error(f"完整更新失败: {e}")
            return f"❌ 更新失败: {str(e)}"
    
    def _update_single_todo(self, update):
        """增量更新单个todo"""
        try:
            response = requests.post(
                'http://localhost:5000/api/todos/update',
                json={'update': update},
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    return f"✅ 任务 {update['id']} 已更新为 {update['status']}"
                else:
                    error_msg = result.get('message', '未知错误')
                    logger.error(f"TodoList增量更新失败: {error_msg}")
                    return f"❌ 任务更新失败: {error_msg}"
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"增量更新API调用失败: {error_msg}")
                return f"❌ API调用失败: {error_msg}"
        except Exception as e:
            logger.error(f"增量更新失败: {e}")
            return f"❌ 增量更新失败: {str(e)}"