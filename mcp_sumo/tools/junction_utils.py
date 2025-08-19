import xml.etree.ElementTree as ET
import os
import sumolib
import traci
import math
from collections import defaultdict
import pandas as pd
import xml.dom.minidom as minidom
import tempfile
import subprocess

def _get_lane_angle(lane_shape):
    """计算车道角度（0-360度）。内部使用。"""
    if len(lane_shape) < 2: return None
    p1, p2 = lane_shape[-2], lane_shape[-1]
    angle_rad = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
    angle_deg = math.degrees(angle_rad)
    return (angle_deg + 360) % 360

def _angle_to_direction(angle_deg):
    """将角度（度）映射到基本方向。内部使用。"""
    if angle_deg is None: return "Unknown"
    if 45 <= angle_deg < 135: return "South"
    elif 135 <= angle_deg < 225: return "East"
    elif 225 <= angle_deg < 315: return "North"
    else: return "West"

def _analyze_single_tl_directions_internal(net_dir, target_id):
    """
    内部分析单个交通灯的函数。假设TraCI正在运行。
    返回元组：(direction_mapping, state_length, error_message)
    """
    lane_directions = {}
    controlled_incoming_lanes = []
    state_length = 0
    direction_mapping = defaultdict(list)

    # 加载sumolib网络
    try:
        net = sumolib.net.readNet(net_dir)
    except Exception: 
        return None, 0, "无法加载网络文件"

    # 启动TraCI
    sumo_running = False
    try:
        sumo_cmd = ["sumo", "-n", net_dir, "--duration-log.disable", "true", "--no-step-log", "true", "--no-warnings", "true"]
        traci.start(sumo_cmd)
        sumo_running = True
    except Exception as e:
        if sumo_running: traci.close()
        return None, 0, f"TraCI启动错误: {e}"

    try:
        junction = net.getNode(target_id)
        if not junction: raise ValueError(f"找不到交叉口ID '{target_id}'。")
        for edge in junction.getIncoming():
            for lane in edge.getLanes():
                angle = _get_lane_angle(lane.getShape())
                lane_directions[lane.getID()] = _angle_to_direction(angle)
    except Exception as e:
        if sumo_running: traci.close()
        return None, 0, f"获取车道方向时出错: {e}"

    try:
        if target_id not in traci.trafficlight.getIDList():
             if net.getNode(target_id) and net.getNode(target_id).getType() != 'traffic_light':
                 return None, 0, f"节点 '{target_id}' 存在但不是交通灯类型。"
             else:
                return None, 0, f"TraCI找不到交通灯ID '{target_id}'。"

        controlled_links_raw = traci.trafficlight.getControlledLinks(target_id)
        if controlled_links_raw is None:
             return None, 0, f"TraCI无法获取'{target_id}'的控制链接。"

        controlled_incoming_lanes = [link[0][0] for link in controlled_links_raw if link]
        state_length = len(controlled_incoming_lanes)

        if state_length == 0:
             return None, 0, f"交通灯 '{target_id}' 没有有效的控制链接。"

    except Exception as e:
        if sumo_running: traci.close()
        return None, 0, f"查询控制链接时出现TraCI错误: {e}"

    for index in range(state_length):
         lane_id = controlled_incoming_lanes[index]
         direction = lane_directions.get(lane_id, "Unknown")
         direction_mapping[direction].append({'index': index, 'lane_id': lane_id})
    
    if sumo_running: traci.close()
    return direction_mapping, state_length, None

def analyze_traffic_light_phases(net_file, tls_file, tl_id):
    """
    分析交通灯相位，确定每个相位放行的车道和方向
    
    参数:
    net_file: 网络文件路径
    tls_file: 信号灯配时文件路径
    tl_id: 交通灯ID
    
    返回:
    包含每个相位信息的字典列表
    """
    # 获取方向映射
    direction_mapping, state_length, error = _analyze_single_tl_directions_internal(net_file, tl_id)
    
    if error:
        print(f"错误: {error}")
        return None
    
    # 解析XML文件获取交通灯相位
    tree = ET.parse(tls_file)
    root = tree.getroot()
    
    # 查找指定ID的交通灯
    tl_logic = None
    
    # 在tls文件中，交通灯元素可能是tlLogic或直接是additionals下的子元素
    if tls_file:
        for tl in root.findall(".//tlLogic"):
            if tl.get("id") == tl_id:
                tl_logic = tl
                break
        # 如果没找到，尝试其他可能的路径
        if tl_logic is None:
            for tl in root.findall("./tlLogic"):
                if tl.get("id") == tl_id:
                    tl_logic = tl
                    break
    else:
        # 在网络文件中查找
        for tl in root.findall(".//tlLogic"):
            if tl.get("id") == tl_id:
                tl_logic = tl
                break
    
    if tl_logic is None:
        print(f"在文件中找不到ID为{tl_id}的交通灯")
        return None
    
    # 获取所有相位
    phases_info = []
    for phase in tl_logic.findall("phase"):
        state = phase.get("state")
        duration = int(phase.get("duration"))
        
        # 检查每个方向的车道是否放行
        allowed_lanes = defaultdict(list)
        
        # 首先按车道ID分组所有索引
        lane_indices = defaultdict(list)
        for direction, lanes in direction_mapping.items():
            for lane_info in lanes:
                lane_id = lane_info["lane_id"]
                index = lane_info["index"]
                if lane_id not in lane_indices:
                    lane_indices[lane_id] = {"direction": direction, "indices": []}
                lane_indices[lane_id]["indices"].append(index)
        
        # 检查每个车道的所有索引是否都放行
        all_allowed_lanes = set()  # 所有放行车道的集合
        for lane_id, info in lane_indices.items():
            direction = info["direction"]
            all_green = True
            for index in info["indices"]:
                if index >= len(state) or state[index] not in ["G", "g"]:
                    all_green = False
                    break
            
            if all_green:
                allowed_lanes[direction].append(lane_id)
                all_allowed_lanes.add(lane_id)  # 添加到总集合中
        
        # 生成自然语言描述
        direction_zh_map = {"North": "北", "South": "南", "East": "东", "West": "西"}
        description_parts = []
        
        for direction, lanes in allowed_lanes.items():
            if lanes:  # 确保该方向有放行的车道
                direction_zh = direction_zh_map.get(direction, direction)
                description_parts.append(direction_zh)
        
        description = "".join(description_parts) if description_parts else "无"
        
        # 添加到相位信息列表
        phases_info.append({
            "duration": duration,
            "allowed_lanes": all_allowed_lanes,  # 使用合并后的集合
            "description": description
        })
    
    return phases_info

def get_all_tl_phases(net_file):
    """
    获取网络中所有交通灯的相位信息
    
    参数:
    net_file: 网络文件路径
    
    返回:
    包含所有交通灯相位信息的字典
    """
    # 解析XML文件获取所有交通灯ID
    tree = ET.parse(net_file)
    root = tree.getroot()
    tl_ids = [tl.get("id") for tl in root.findall(".//tlLogic")]
    
    # 分析每个交通灯的相位
    all_tl_phases = {}
    for tl_id in tl_ids:
        phases = analyze_traffic_light_phases(net_file, tl_id)
        if phases:
            all_tl_phases[tl_id] = phases
    
    return all_tl_phases

# 示例使用
if __name__ == "__main__":
    net_file = r"K:\scientific\MCPforSUMO\mcp_for_claude\data\simulation\luoyang\net.net.xml"
    tls_file = r"K:\scientific\MCPforSUMO\mcp_for_claude\data\simulation\luoyang\tls.add.xml"
    tl_id = "C2"  # 示例交通灯ID
    
    # 分析单个交通灯
    phases = analyze_traffic_light_phases(net_file, tls_file, tl_id)
    if phases:
        print(f"交通灯 {tl_id} 的相位信息:")
        print(phases)
        # for i, phase in enumerate(phases):
        #     print(f"相位 {i+1}:")
        #     print(f"  持续时间: {phase['duration']}秒")
        #     print(f"  放行方向: {phase['description']}")
        #     print(f"  放行车道: {phase['allowed_lanes']}")
    
    # # 获取所有交通灯的相位信息
    # all_phases = get_all_tl_phases(net_file)
    # print(f"网络中共有 {len(all_phases)} 个交通灯")
    # print(all_phases)
