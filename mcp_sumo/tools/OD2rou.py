import pandas as pd
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
import os
import traci
import sumolib

def create_taz_file_with_traci(net_file_path, taz_ids, output_taz_path):
    """
    使用traci创建SUMO的taz.xml文件
    
    参数:
    net_file_path: SUMO网络文件路径
    taz_ids: TAZ ID集合（交叉口ID）
    output_taz_path: 输出的taz.xml文件路径
    """
    # 转换为绝对路径
    net_file_path = os.path.abspath(net_file_path)
    output_taz_path = os.path.abspath(output_taz_path)
    
    # 启动SUMO以加载网络
    sumoBinary = "sumo"
    sumoCmd = [sumoBinary, "-n", net_file_path, "--start", "--no-step-log", "--no-warnings"]
    
    # 创建根节点
    root = ET.Element('tazs')
    
    try:
        # 启动traci
        traci.start(sumoCmd)
        
        # 获取所有交叉口
        for taz_id in taz_ids:
            # 创建TAZ元素
            taz = ET.SubElement(root, 'taz', {'id': str(taz_id)})
            
            try:
                # 获取进入边（用作tazSink）
                incoming_edges = traci.junction.getIncomingEdges(str(taz_id))
                # 过滤掉内部边（以":"开头的边）
                incoming_edges = [edge for edge in incoming_edges if not edge.startswith(":")]
                
                # 获取出口边（用作tazSource）
                outgoing_edges = traci.junction.getOutgoingEdges(str(taz_id))
                # 过滤掉内部边（以":"开头的边）
                outgoing_edges = [edge for edge in outgoing_edges if not edge.startswith(":")]
                
                # 添加tazSource（出口边）
                for edge in outgoing_edges:
                    ET.SubElement(taz, 'tazSource', {'id': edge, 'weight': "1.0"})
                
                # 添加tazSink（进入边）
                for edge in incoming_edges:
                    ET.SubElement(taz, 'tazSink', {'id': edge, 'weight': "1.0"})
            
            except traci.TraCIException as e:
                print(f"警告: 处理交叉口 {taz_id} 时出错: {e}")
                # 如果找不到交叉口，尝试使用sumolib找到最近的边
                net = sumolib.net.readNet(net_file_path)
                
                # 假设taz_id格式为"字母+数字"，例如"C2"，我们可以尝试将其解释为坐标
                try:
                    col = ord(taz_id[0]) - ord('A')  # A->0, B->1, ...
                    row = int(taz_id[1:])
                    # 假设网格大小为500m
                    x, y = col * 500, row * 500
                    
                    # 找到最近的边
                    radius = 200  # 搜索半径
                    edges = net.getNeighboringEdges(x, y, radius)
                    edges.sort(key=lambda x: x[1])  # 按距离排序
                    
                    # 使用最近的几条边
                    for edge, _ in edges[:5]:
                        ET.SubElement(taz, 'tazSource', {'id': edge.getID(), 'weight': "1.0"})
                        ET.SubElement(taz, 'tazSink', {'id': edge.getID(), 'weight': "1.0"})
                    
                    print(f"TAZ {taz_id}: 使用了 {min(5, len(edges))} 条最近的边")
                except:
                    print(f"无法为TAZ {taz_id} 找到合适的边")
        
    finally:
        # 关闭traci连接
        traci.close()
    
    # 美化XML输出
    rough_string = ET.tostring(root, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    pretty_xml = reparsed.toprettyxml(indent="  ")
    
    # 写入文件
    with open(output_taz_path, 'w', encoding='utf-8') as f:
        f.write(pretty_xml)
    
    return output_taz_path

def create_taz_relation_file(od_csv_path, output_file_path):
    """
    将OD矩阵CSV文件转换为SUMO的tazRelation.xml文件
    
    参数:
    od_csv_path: OD矩阵CSV文件路径
    output_file_path: 输出的tazRelation.xml文件路径
    """
    # 转换为绝对路径
    od_csv_path = os.path.abspath(od_csv_path)
    output_file_path = os.path.abspath(output_file_path)
    
    # 读取OD矩阵，使用制表符作为分隔符
    df = pd.read_csv(od_csv_path, sep='\t')
    
    # 创建根节点
    root = ET.Element('data')
    root.set('xmlns:xsi', "https://www.w3.org/2001/XMLSchema-instance")
    root.set('xsi:noNamespaceSchemaLocation', "https://sumo.dlr.de/xsd/datamode_file.xsd")
    
    # 创建间隔元素
    interval = ET.SubElement(root, 'interval')
    interval.set('begin', "0")
    interval.set('end', "3600")  
    
    # 添加每个OD对的关系
    for _, row in df.iterrows():
        relation = ET.SubElement(interval, 'tazRelation')
        relation.set('count', str(int(row['Value'])))
        relation.set('from', str(row['Row']))
        relation.set('to', str(row['Col']))
    
    # 美化XML输出
    rough_string = ET.tostring(root, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    pretty_xml = reparsed.toprettyxml(indent="  ")
    
    # 写入文件
    with open(output_file_path, 'w', encoding='utf-8') as f:
        f.write(pretty_xml)
    
    return output_file_path

def generate_traffic_from_od(net_file_path, od_csv_path, output_dir="./output"):
    """
    完整的流程：从OD矩阵生成SUMO交通流
    
    参数:
    net_file_path: SUMO网络文件路径
    od_csv_path: OD矩阵CSV文件路径
    output_dir: 输出目录
    
    返回:
    生成的routes文件路径
    """
    # 转换为绝对路径
    net_file_path = os.path.abspath(net_file_path)
    od_csv_path = os.path.abspath(od_csv_path)
    output_dir = os.path.abspath(output_dir)
    
    # 创建输出目录（如果不存在）
    os.makedirs(output_dir, exist_ok=True)
    
    # 读取OD数据，获取所有TAZ ID
    df = pd.read_csv(od_csv_path, sep='\t')
    taz_ids = set(list(df['Row'].unique()) + list(df['Col'].unique()))
    
    # 生成TAZ文件
    taz_file_path = os.path.join(output_dir, "taz.xml")
    create_taz_file_with_traci(net_file_path, taz_ids, taz_file_path)
    
    # 生成TAZ关系文件
    taz_relation_path = os.path.join(output_dir, "tazRelation.xml")
    create_taz_relation_file(od_csv_path, taz_relation_path)
    
    # 生成车辆出行
    trips_file_path = os.path.join(output_dir, "trips.xml")
    
    # 使用od2trips命令生成trips文件
    command = f"od2trips -n \"{taz_file_path}\" -z \"{taz_relation_path}\" --flow-output \"{trips_file_path}\" --ignore-errors true --flow-output.probability true"
    os.system(command)
    
    # 使用duarouter生成routes文件
    routes_file_path = os.path.join(output_dir, "routes.xml")
    command = f"duarouter -n \"{net_file_path}\" --route-files \"{trips_file_path}\" -o \"{routes_file_path}\" --ignore-errors --junction-taz true"
    os.system(command)
    
    return routes_file_path
