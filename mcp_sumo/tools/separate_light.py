import xml.etree.ElementTree as ET

def separate_traffic_lights(net_xml_path, tls_xml_path, program_id='a'):
    # 解析原始的net.xml文件
    tree = ET.parse(net_xml_path)
    root = tree.getroot()

    # 创建一个新的XML根元素，用于存储信号灯信息
    traffic_light_root = ET.Element('additional')

    # 查找所有的tlLogic元素
    tlLogic_elements = root.findall('.//tlLogic')

    # 将tlLogic元素从原始XML中移除，并添加到新的XML中
    for tlLogic in tlLogic_elements:
        # add文件的programID需要与net的不一样
        tlLogic.set('programID', program_id)
        root.remove(tlLogic)
        traffic_light_root.append(tlLogic)

    # 创建新的XML树
    traffic_light_tree = ET.ElementTree(traffic_light_root)

    # 保存只有信号灯的XML文件
    traffic_light_tree.write(tls_xml_path, encoding='utf-8', xml_declaration=True)

