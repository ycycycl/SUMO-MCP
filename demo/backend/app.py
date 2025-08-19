#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
SUMO-MCP 后端API服务
"""

import os
import json
import logging
import requests
import re
from collections import defaultdict
from flask import Flask, request, Response, jsonify, send_file
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from qwen_client import QwenClient

# 加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # 如果没有安装python-dotenv，跳过
    pass

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# 配置
SUMO_SERVER_URL = os.getenv("SUMO_SERVER_URL", "http://127.0.0.1:8014")
qwen_client = QwenClient()

# 全局变量存储todolist
current_todos = []

def broadcast_todos():
    """通过WebSocket广播当前todolist"""
    socketio.emit('todos_updated', {'todos': current_todos})

@app.route("/api/chat", methods=["POST"])
def chat_stream():
    global current_todos
    try:
        data = request.get_json()
        user_input = data.get("message", "")
        
        if not user_input:
            return jsonify({"error": "消息不能为空"}), 400
        
        def generate():
            try:
                messages = [{'role': 'user', 'content': [{'text': user_input}]}]
                
                from qwen_agent.utils.output_beautify import typewriter_print
                previous_text = ""
                section_markers = ["[THINK]", "[TOOL_CALL]", "[TOOL_RESPONSE]", "[ANSWER]"]
                current_section = None  # 当前正在处理的section
                last_marker_pos = -1    # 上一个标记的位置
                last_sent_content = ""  # 上一次发送的内容
                section_counters = {}   # 记录每种section类型的出现次数
                
                # 运行模型并流式输出
                for response in qwen_client.bot.run(messages):
                    previous_text = typewriter_print(response, previous_text)
                    
                    # 查找下一个标记
                    next_marker = None
                    next_marker_pos = len(previous_text)
                    
                    for marker in section_markers:
                        # 从上一个标记位置之后开始查找
                        pos = previous_text.find(marker, last_marker_pos + 1)
                        if pos != -1 and pos < next_marker_pos:
                            next_marker = marker
                            next_marker_pos = pos
                    
                    # 如果发现新标记
                    if next_marker and next_marker_pos > last_marker_pos:
                        # 完成上一个section（如果存在）
                        if current_section:
                            # 在section完成时检测TodoWrite工具调用
                            if current_section.startswith('tool-calls') or current_section.startswith('tool-responses'):
                                # 提取当前section的内容来检测TodoWrite
                                section_start = last_marker_pos
                                section_end = next_marker_pos
                                section_content = previous_text[section_start:section_end]
                                
                                # 检测TodoWrite工具调用
                                if "TodoWrite" in section_content:
                                    try:
                                        import re
                                        # 更精确的正则表达式来提取JSON数据
                                        todo_pattern = r'TodoWrite.*?(\{.*?"todos".*?\[.*?\].*?\})'
                                        match = re.search(todo_pattern, section_content, re.DOTALL)
                                        if match:
                                            todo_json_str = match.group(1)
                                            todo_data = json.loads(todo_json_str)
                                            todos = todo_data.get('todos', [])
                                            if todos:
                                                # 更新全局todolist
                                                current_todos = todos
                                                # 通过WebSocket推送更新
                                                broadcast_todos()
                                    except Exception as e:
                                        pass
                                
                                # 检测mount_module工具调用
                                if "sumo_server-mount_module" in section_content or "mount_module" in section_content:
                                    try:
                                        logger.info("检测到mount_module工具调用，准备刷新工具列表")
                                        # 刷新QwenClient的工具列表
                                        refresh_success = qwen_client.refresh_tools()
                                        if refresh_success:
                                            logger.info("工具列表刷新成功")
                                        else:
                                            logger.warning("工具列表刷新失败")
                                    except Exception as e:
                                        logger.error(f"刷新工具列表时发生错误: {str(e)}")
                            
                            yield f"data: {json.dumps({'type': 'section_complete', 'section': current_section})}\n\n"
                        
                        # 开始新的section
                        base_section_name = next_marker.lower().replace('[', '').replace(']', '').replace('_', '-')
                        if base_section_name == "tool-call":
                            base_section_name = "tool-calls"
                        elif base_section_name == "tool-response":
                            base_section_name = "tool-responses"
                        
                        # 更新计数器
                        section_counters[base_section_name] = section_counters.get(base_section_name, 0) + 1
                        counter = section_counters[base_section_name]
                        
                        # 为重复的section添加编号
                        if counter > 1:
                            section_name = f"{base_section_name}-{counter}"
                        else:
                            section_name = base_section_name
                        
                        current_section = section_name
                        last_marker_pos = next_marker_pos
                        last_sent_content = ""
                        
                        yield f"data: {json.dumps({'type': 'section_start', 'section': section_name})}\n\n"
                    
                    # 如果还没有找到任何section，但text中包含标记，初始化第一个section
                    elif current_section is None:
                        for marker in section_markers:
                            pos = previous_text.find(marker)
                            if pos != -1:
                                base_section_name = marker.lower().replace('[', '').replace(']', '').replace('_', '-')
                                if base_section_name == "tool-call":
                                    base_section_name = "tool-calls"
                                elif base_section_name == "tool-response":
                                    base_section_name = "tool-responses"
                                
                                section_counters[base_section_name] = 1
                                current_section = base_section_name
                                last_marker_pos = pos
                                last_sent_content = ""
                                
                                yield f"data: {json.dumps({'type': 'section_start', 'section': base_section_name})}\n\n"
                                break
                    
                    # 更新当前section的内容（无论是否找到新标记都要处理）
                    if current_section and last_marker_pos >= 0:
                        # 找到当前标记
                        current_marker = None
                        for marker in section_markers:
                            if previous_text[last_marker_pos:].startswith(marker):
                                current_marker = marker
                                break
                        
                        if current_marker:
                            # 提取内容：从标记结束到下一个标记开始（或文本结尾）
                            start_pos = last_marker_pos + len(current_marker)
                            
                            # 找到下一个标记的位置作为结束位置
                            end_pos = len(previous_text)
                            for marker in section_markers:
                                pos = previous_text.find(marker, start_pos)
                                if pos != -1:
                                    end_pos = min(end_pos, pos)
                            
                            content = previous_text[start_pos:end_pos].strip()
                            
                            # 只有内容发生变化时才发送
                            if content and content != last_sent_content:
                                yield f"data: {json.dumps({'type': 'content', 'section': current_section, 'content': content})}\n\n"
                                last_sent_content = content
                
                # 完成最后一个section
                if current_section:
                    # 在最后一个section完成时也检测TodoWrite
                    if current_section.startswith('tool-calls') or current_section.startswith('tool-responses'):
                        # 从当前section开始位置到文本结尾
                        section_content = previous_text[last_marker_pos:]
                        
                        if "TodoWrite" in section_content:
                            try:
                                import re
                                todo_pattern = r'TodoWrite.*?(\{.*?"todos".*?\[.*?\].*?\})'
                                match = re.search(todo_pattern, section_content, re.DOTALL)
                                if match:
                                    todo_json_str = match.group(1)
                                    todo_data = json.loads(todo_json_str)
                                    todos = todo_data.get('todos', [])
                                    if todos:
                                        # 更新全局todolist
                                        current_todos = todos
                                        # 通过WebSocket推送更新
                                        broadcast_todos()
                            except Exception as e:
                                pass
                    
                    yield f"data: {json.dumps({'type': 'section_complete', 'section': current_section})}\n\n"
                
                yield f"data: {json.dumps({'type': 'complete'})}\n\n"
                
            except Exception as e:
                logger.error(f"生成响应时出错: {e}")
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        
        return Response(
            generate(),
            mimetype='text/event-stream',
            headers={
                'Content-Type': 'text/event-stream; charset=utf-8',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'POST'
            }
        )
        
    except Exception as e:
        logger.error(f"处理请求时出错: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/test", methods=["GET"])
def test():
    return jsonify({
        "message": "SUMO-MCP API 正常运行中",
        "sumo_server_url": SUMO_SERVER_URL
    })

@app.route('/api/show_picture', methods=['POST'])
def show_picture():
    """接收MCP服务器的图片显示请求"""
    
    try:
        data = request.get_json()
        image_path = data.get('image_path')
        title = data.get('title', '图片')
        description = data.get('description', '')
        timestamp = data.get('timestamp', 0)
        
        if not image_path or not os.path.exists(image_path):
            return jsonify({"success": False, "message": "图片文件不存在"}), 400
        
        # 创建图片信息
        image_info = {
            "image_path": image_path,
            "title": title,
            "description": description,
            "timestamp": timestamp
        }
        
        # 通过WebSocket立即推送图片
        socketio.emit('new_image', image_info)
        
        return jsonify({"success": True, "message": "图片显示请求已接收并推送"})
    
    except Exception as e:
        logger.error(f"处理图片显示请求失败: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/image/<path:filename>')
def serve_image(filename):
    """提供图片文件服务"""
    try:
        # 安全检查：确保文件路径在允许的目录内
        # 这里简化处理，实际部署时需要更严格的安全检查
        if os.path.exists(filename):
            return send_file(filename)
        
        # 如果直接路径不存在，尝试在data目录下查找
        data_path = os.path.join('..', 'data', filename)
        if os.path.exists(data_path):
            return send_file(data_path)
        
        return jsonify({"error": "图片文件不存在"}), 404
    
    except Exception as e:
        logger.error(f"提供图片文件失败: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/todos', methods=['POST'])
def update_todos():
    """更新todolist"""
    global current_todos
    
    try:
        data = request.get_json()
        if data is None:
            return jsonify({"success": False, "message": "请求数据为空"}), 400
        
        todos = data.get('todos', [])
        
        # 验证todos格式
        for todo in todos:
            if not all(key in todo for key in ['id', 'content', 'status']):
                return jsonify({"success": False, "message": "Todo格式错误"}), 400
            if todo['status'] not in ['pending', 'in_progress', 'completed']:
                return jsonify({"success": False, "message": "状态值无效"}), 400
        
        current_todos = todos
        # 通过WebSocket推送更新
        broadcast_todos()
        return jsonify({"success": True, "message": "Todolist更新成功"})
    
    except Exception as e:
        logger.error(f"更新todolist失败: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/todos', methods=['DELETE'])
def clear_todos():
    """清空todolist"""
    global current_todos
    
    try:
        current_todos = []
        # 通过WebSocket推送更新
        broadcast_todos()
        return jsonify({"success": True, "message": "Todolist已清空"})
    
    except Exception as e:
        logger.error(f"清空todolist失败: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/todos/update', methods=['POST'])
def update_single_todo():
    """增量更新单个todo"""
    global current_todos
    
    try:
        data = request.get_json()
        if data is None:
            return jsonify({"success": False, "message": "请求数据为空"}), 400
        
        update = data.get('update', {})
        
        if not update or 'id' not in update or 'status' not in update:
            return jsonify({"success": False, "message": "update参数格式错误"}), 400
        
        # 查找并更新对应的todo项
        todo_found = False
        for todo in current_todos:
            if todo['id'] == update['id']:
                # 更新状态
                todo['status'] = update['status']
                # 可选更新内容
                if 'content' in update:
                    todo['content'] = update['content']
                todo_found = True
                break
        
        if not todo_found:
            return jsonify({"success": False, "message": f"未找到ID为 {update['id']} 的任务"}), 404
        
        # 通过WebSocket推送更新
        broadcast_todos()
        return jsonify({"success": True, "message": "任务状态更新成功"})
    
    except Exception as e:
        logger.error(f"增量更新todolist失败: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@socketio.on('connect')
def handle_connect():
    """处理WebSocket连接"""
    # 新客户端连接时，立即发送当前todolist
    emit('todos_updated', {'todos': current_todos})

@socketio.on('disconnect')
def handle_disconnect():
    """处理WebSocket断开连接"""
    pass

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=False) 