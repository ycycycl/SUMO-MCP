'''
用于获取各种评价指标
'''
import os
import csv
import ast
import matplotlib as mpl
import matplotlib.pyplot as plt
import xml.etree.ElementTree as ET
# 正常显示中文标签
mpl.rcParams['font.sans-serif'] = ['SimHei']

def queue_junction(csv_path):
    '''
        fun: 获取各个路口的排队长度, 排序后返回
        input: metrics.csv文件
        return: 字典, key为路口id, value为该路口排队长度
    '''
    # 获取各个路口的排队长度, 排序后返回
    queue = dict()
    with open(csv_path, 'r') as file:
        csv_reader = csv.reader(file)
        for row in csv_reader:
            line = ""
            for col in row:
                line += col
                line += ","
            line = line[:line.rfind("{")]
            left = line.rfind("{")
            right = line.rfind("}")
            if left < right:
                dict_obj = ast.literal_eval(line[left:right+1])
                for key, value in dict_obj.items():
                    if key in queue:
                        queue[key] += value
                    else:
                        queue[key] = value
    # 按照排队长度从大到小排序
    queue = dict(sorted(queue.items(), key=lambda item: item[1], reverse=True))
    return queue

def queue_road(csv_path):
    '''
        fun: 获取路段的排队长度, 求和后返回, 统计的交叉口可以在下面的junction_set中指定
        input: metrics.csv文件
        return: 数值, 路段上各交叉口排队长度之和
    '''
    # 获取路段的排队长度, 求和后返回，只统计乐民街上的交叉口
    road_queue = 0
    junction_set = {'302', '303', '304', '305', '306', '307', '308'}
    with open(csv_path, 'r') as file:
        csv_reader = csv.reader(file)
        for row in csv_reader:
            line = ""
            for col in row:
                line += col
                line += ","
            line = line[:line.rfind("{")]
            left = line.rfind("{")
            right = line.rfind("}")
            if left < right:
                dict_obj = ast.literal_eval(line[left:right+1])
                for key, value in dict_obj.items():
                    if key in junction_set:
                        road_queue += value
    return road_queue

def queue_network(csv_path):
    '''
        fun: 获取路网的平均排队长度, 统计所有交叉口
        input: metrics.csv文件
        return: 数值, 路段上各交叉口排队长度之和
    '''
    network_queue = 0.0
    junction_count = 0
    with open(csv_path, 'r') as file:
        csv_reader = csv.reader(file)
        for row in csv_reader:
            line = ""
            for col in row:
                line += col
                line += ","
            line = line[:line.rfind("{")]
            left = line.rfind("{")
            right = line.rfind("}")
            if left < right:
                dict_obj = ast.literal_eval(line[left:right+1])
                junction_count = len(dict_obj)
                for _, value in dict_obj.items():
                    network_queue += value
    if junction_count != 0:
        network_queue = network_queue/float(junction_count)
    else:
        network_queue = 0
    return network_queue

def draw_queue_junction(csv_path):
    '''
        fun: 取排队长度最大的前十个交叉口绘图
        input: metrics.csv文件
    '''
    queue_length = queue_junction(csv_path)
    top_ten = dict(list(queue_length.items())[:10])
    keys = list(top_ten.keys())
    values = list(top_ten.values())
    plt.bar(keys, values)
    plt.title('排队长度最大的十个路口')
    plt.xlabel('路口id')
    plt.ylabel('排队长度(veh)')
    plt.show()

def maxWait_junction(xml_path, junction_id):
    '''
        fun: 获取某个路口的最大等待时间
        input: dector输出的.xml文件
        return: 数值, 最大等待时间
    '''
    if not os.path.exists(xml_path):
        return
    # 加载XML文件
    tree = ET.parse(xml_path)
    root = tree.getroot()
    maxWait = 0
    for interval in root.findall("interval"):
        id = interval.get("id")
        if id is None:
            continue
        if id.split("_")[0] != "E2":
            continue
        jun_id = id.split("_")[1]
        if jun_id != junction_id:
            continue
        maxWait = max(maxWait, float(interval.get("maxHaltingDuration")))
    return maxWait

def haltRate_junction(xml_path, junction_id):
    '''
        fun: 获取某个路口的平均停车率
        input: dector输出的.xml文件
        return: 数值, 平均停车率
    '''
    if not os.path.exists(xml_path):
        return
    # 加载XML文件
    tree = ET.parse(xml_path)
    root = tree.getroot()
    total_veh = 0
    total_halt = 0
    for interval in root.findall("interval"):
        id = interval.get("id")
        if id is None:
            continue
        if id.split("_")[0] != "E2":
            continue
        jun_id = id.split("_")[1]
        if jun_id != junction_id:
            continue
        total_veh += int(interval.get("nVehEntered"))
        total_halt += float(interval.get("startedHalts"))
    if total_veh == 0:
        return 0
    return float(total_halt)/float(total_veh)

def overflowRate_juntcion(xml_path, junction_id):
    '''
        fun: 获取某个路口的平均溢出率
        input: dector输出的.xml文件
        return: 数值, 平均溢出率
    '''
    if not os.path.exists(xml_path):
        return
    # 加载XML文件
    tree = ET.parse(xml_path)
    root = tree.getroot()
    time_overflow = dict()
    max_occ = 0
    for interval in root.findall("interval"):
        id = interval.get("id")
        if id is None:
            continue
        if id.split("_")[0] != "E2":
            continue
        jun_id = id.split("_")[1]
        if jun_id != junction_id:
            continue
        if interval.get("begin") not in time_overflow:
            time_overflow[interval.get("begin")] = 0
        max_occ = max(float(interval.get("maxOccupancy")), max_occ)
        if float(interval.get("maxOccupancy")) > 40.0:      # 这里的max_occ是会把车辆间距算进去，就算堵死也就60左右
            time_overflow[interval.get("begin")] = 1
    # 统计发生溢出的时长
    count_overflow = sum(1 for key in time_overflow if time_overflow[key] == 1)
    # 计算占比
    if len(time_overflow) == 0:
        return 0
    percentage = (count_overflow / len(time_overflow))
    print(max_occ)
    return percentage

# draw_queue_junction("results/adaptive_opt/FIXED-tr3-rongdong_2_phase-0-mplight-wait/metrics_100.csv")
    
def metrics_network(xml_path):
    '''
        fun: 获取路网平均行程时间、平均等待时间、平均延误指标
        input: tripinfo.xml文件
        output: 平均延误(s)
    '''
    if not os.path.exists(xml_path):
        return

    # 加载XML文件
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # 初始化指标
    ret = {}
    ret['avg_duration'] = 0.0
    ret['avg_waitingTime'] = 0.0
    ret['avg_timeLoss'] = 0.0

    # 遍历tripinfo节点, 读取信息
    for tripinfo in root.findall('tripinfo'):
        # 获取id属性并添加到列表中
        ret['avg_duration'] += float(tripinfo.get('duration'))
        ret['avg_waitingTime'] += float(tripinfo.get('waitingTime'))
        ret['avg_timeLoss'] += float(tripinfo.get('timeLoss'))

    # 取平均
    car_count = len(root.findall('tripinfo'))
    ret['avg_duration'] /= float(car_count)
    ret['avg_waitingTime'] /= float(car_count)
    ret['avg_timeLoss'] /= float(car_count)

    return ret

def metrics_road(xml_path):
    '''
        fun: 获取路段中的平均停车次数、平均行程时间和平均延误, 需要在要调查的路段布设e3检测器
        input: 检测器的输出文件
        return: [路段中车辆数, 路段中的平均停车次数、平均行程时间和平均延误]
    '''
    if not os.path.exists(xml_path):
        return
    
    ret = dict()
    ret['avg_stopcount'] = 0.0
    ret['avg_duration'] = 0.0
    ret['avg_timeLoss'] = 0.0

    # 加载XML文件
    tree = ET.parse(xml_path)
    root = tree.getroot()
    carcount1 = 0
    carcount2 = 0
    for interval in root.findall("interval"):
        if 'E2' in interval.get("id"):
            continue
        ret['avg_stopcount'] += round(float(interval.get("meanHaltsPerVehicle")) * float(interval.get("vehicleSum")))
        # ret['avg_stopcount'] += round(float(interval.get("meanHaltsPerVehicleWithin")) * float(interval.get("vehicleSumWithin")))
        ret['avg_duration'] += float(interval.get("meanTravelTime")) * float(interval.get("vehicleSum"))
        # ret['avg_duration'] += float(interval.get("meanDurationWithin")) * float(interval.get("vehicleSumWithin"))
        ret['avg_timeLoss'] += float(interval.get("meanTimeLoss")) * float(interval.get("vehicleSum"))
        # ret['avg_timeLoss'] += float(interval.get("meanTimeLossWithin")) * float(interval.get("vehicleSumWithin"))
        carcount1 += int(interval.get("vehicleSum"))
        # carcount2 += int(interval.get("vehicleSumWithin"))
    if carcount1 + carcount2 != 0:
        ret['avg_stopcount'] = ret['avg_stopcount'] / float(carcount1 + carcount2)
        ret['avg_duration'] = ret['avg_duration'] / float(carcount1 + carcount2)
        ret['avg_timeLoss'] = ret['avg_timeLoss'] / float(carcount1 + carcount2)
    else:
        ret['avg_stopcount'] = 0
        ret['avg_duration'] = 0
        ret['avg_timeLoss'] = 0
    return carcount1+carcount2, ret

def cal_edge_metrics(xml_path: str):
    """
    从edgedata.xml输出文件提取各道路边的性能指标
    
    Args:
        xml_path: edgedata.xml文件路径
    
    Returns:
        字典，包含各道路边的旅行时间、时间损失和速度指标
    """
    if not os.path.exists(xml_path):
        return None
        
    # 加载XML文件
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    # 初始化结果字典
    edge_metrics = {}
    
    # 遍历所有时间间隔
    for interval in root.findall("interval"):
        # 遍历该时间间隔内的所有边
        for edge in interval.findall("edge"):
            edge_id = edge.get("id")
            
            # 提取需要的指标
            travel_time = float(edge.get("traveltime"))
            time_loss = float(edge.get("timeLoss"))
            speed = float(edge.get("speed"))
            
            # 存储指标到字典中
            edge_metrics[edge_id] = {
                "travel_time": travel_time,
                "time_loss": time_loss,
                "speed": speed
            }
    
    return edge_metrics

def cal_junction_metrics(xml_path: str):
    """
    从queue.xml输出文件计算各路口的排队指标
    
    Args:
        xml_path: queue.xml文件路径
    
    Returns:
        字典，包含各路口的平均排队时间和排队长度
    """
    if not os.path.exists(xml_path):
        return None
        
    # 加载XML文件
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    # 初始化计数器和结果字典
    junction_metrics = {}
    max_timestep = 0
    
    # 遍历所有时间步的数据
    for data in root.findall("data"):
        timestep = float(data.get("timestep"))
        max_timestep = max(max_timestep, timestep)
        
        # 每个时间步的路口临时聚合数据
        timestep_junction_data = {}
        
        # 遍历该时间步的所有车道
        for lane in data.find("lanes").findall("lane"):
            lane_id = lane.get("id")
            
            # 跳过以":"开头的车道（内部车道）
            if lane_id.startswith(":"):
                continue
                
            # 获取排队时间和长度
            queue_time = float(lane.get("queueing_time"))
            queue_length = float(lane.get("queueing_length"))
            
            # 提取路口ID: 例如"A1A2_0"对应的路口为A2
            # 假设车道ID格式为"起点终点_车道号"
            if "_" in lane_id:
                edge_id = lane_id.split("_")[0]
                # 找到终点节点作为路口ID
                if len(edge_id) >= 2:
                    junction_id = edge_id[-2:]  # 取最后两个字符作为路口ID
                    
                    # 初始化路口数据
                    if junction_id not in timestep_junction_data:
                        timestep_junction_data[junction_id] = {
                            "queue_time": 0.0,
                            "queue_length": 0.0
                        }
                    
                    # 累加当前时间步的路口数据
                    timestep_junction_data[junction_id]["queue_time"] += queue_time
                    timestep_junction_data[junction_id]["queue_length"] += queue_length
        
        # 将该时间步的路口数据累加到总数据中
        for junction_id, metrics in timestep_junction_data.items():
            if junction_id not in junction_metrics:
                junction_metrics[junction_id] = {
                    "total_queue_time": 0.0,
                    "total_queue_length": 0.0
                }
            
            # 直接累加排队时间和长度
            junction_metrics[junction_id]["total_queue_time"] += metrics["queue_time"]
            junction_metrics[junction_id]["total_queue_length"] += metrics["queue_length"]
    
    # 计算仿真总时长（时间步数）
    simulation_timesteps = max_timestep + 1
    
    # 计算每个路口的平均值
    result = {}
    for junction_id, metrics in junction_metrics.items():
        result[junction_id] = {
            "avg_queue_time": metrics["total_queue_time"] / simulation_timesteps,
            "avg_queue_length": metrics["total_queue_length"] / simulation_timesteps
        }
    
    return result

def cal_network_metrics(xml_path: str):
    """
    从tripinfo.xml文件中提取路网级别的指标
    
    Args:
        xml_path: tripinfo.xml文件路径
    
    Returns:
        字典，包含平均行程时间、平均等待时间、平均等待次数和总车辆数
    """
    if not os.path.exists(xml_path):
        return None

    # 加载XML文件
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # 初始化指标累加器
    total_duration = 0.0
    total_waiting_time = 0.0
    total_waiting_count = 0
    vehicle_count = 0

    # 遍历tripinfo节点，读取每辆车的信息
    for tripinfo in root.findall('tripinfo'):
        duration = float(tripinfo.get('duration'))
        waiting_time = float(tripinfo.get('waitingTime'))
        waiting_count = int(tripinfo.get('waitingCount'))
        
        total_duration += duration
        total_waiting_time += waiting_time
        total_waiting_count += waiting_count
        vehicle_count += 1

    # 如果没有车辆信息，返回0值
    if vehicle_count == 0:
        return {
            "avg_duration": 0.0,
            "avg_waiting_time": 0.0,
            "avg_waiting_count": 0.0
        }
        
    # 计算平均值
    return {
        "avg_duration": total_duration / vehicle_count,
        "avg_waiting_time": total_waiting_time / vehicle_count,
        "avg_waiting_count": total_waiting_count / vehicle_count,
        "vehicle_count": vehicle_count
    }

# print(metrics_road(r"adaptive_control\environments\rongdong\results\IDQN.xml"))