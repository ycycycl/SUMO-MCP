#!/usr/bin/env python3
"""
SUMO二进制工具模块 - 独立的FastMCP服务器
处理SUMO核心二进制工具的封装和调用功能
"""

import os
import subprocess
from typing import Dict, Any, List, Optional

from fastmcp import FastMCP, Context

# 设置环境变量
os.environ["SUMO_HOME"] = "D:\Program Files\SUMO"

# ────────────────────────────────────────────────────────────────────────────────
# 创建二进制工具服务器
# ────────────────────────────────────────────────────────────────────────────────
bin_mcp = FastMCP(name="SUMO_Bin_Tools")

# ────────────────────────────────────────────────────────────────────────────────
# TOOL 1: 网络转换器 (netconvert)
# ────────────────────────────────────────────────────────────────────────────────
@bin_mcp.tool()
async def netconvert(
        # 输入选项
        sumo_net_file: str = None,
        node_files: str = None,
        edge_files: str = None,
        connection_files: str = None,
        tllogic_files: str = None,
        type_files: str = None,
        ptstop_files: str = None,
        ptline_files: str = None,
        polygon_files: str = None,
        shapefile_prefix: str = None,
        dlr_navteq_prefix: str = None,
        osm_files: str = None,
        opendrive_files: str = None,
        visum_file: str = None,
        vissim_file: str = None,
        robocup_dir: str = None,
        matsim_files: str = None,
        itsumo_files: str = None,
        heightmap_shapefiles: str = None,
        heightmap_geotiff: str = None,
        
        # 输出选项
        write_license: bool = False,
        output_prefix: str = None,
        precision: int = None,
        precision_geo: int = None,
        human_readable_time: bool = False,
        output_file: str = None,
        plain_output_prefix: str = None,
        plain_output_lanes: bool = False,
        junctions_join_output: str = None,
        prefix: str = None,
        amitran_output: str = None,
        matsim_output: str = None,
        opendrive_output: str = None,
        dlr_navteq_output: str = None,
        dlr_navteq_version: str = None,
        dlr_navteq_precision: int = None,
        output_street_names: bool = False,
        output_original_names: bool = False,
        street_sign_output: str = None,
        ptstop_output: str = None,
        ptline_output: str = None,
        ptline_clean_up: bool = False,
        parking_output: str = None,
        railway_topology_output: str = None,
        polygon_output: str = None,
        opendrive_output_straight_threshold: float = None,
        opendrive_output_lefthand_left: bool = False,
        opendrive_output_shape_match_dist: float = None,
        
        ctx: Context = None
    ) -> Dict[str, Any]:
        """使用netconvert将各种网络格式转换为SUMO网络
        
        参数:
        # 输入选项
        sumo_net_file: 从文件读取SUMO网络
        node_files: 从文件读取XML节点定义
        edge_files: 从文件读取XML边定义
        connection_files: 从文件读取XML连接定义
        tllogic_files: 从文件读取XML交通信号灯定义
        type_files: 从文件读取XML类型定义
        ptstop_files: 从文件读取公共交通站点
        ptline_files: 从文件读取公共交通线路
        polygon_files: 从文件读取多边形以嵌入网络
        shapefile_prefix: 从以'FILE'开头的文件读取shapefiles
        dlr_navteq_prefix: 从路径读取转换后的Navteq GDF数据
        osm_files: 从路径读取OSM网络
        opendrive_files: 从文件读取OpenDRIVE网络
        visum_file: 从文件读取VISUM网络
        vissim_file: 从文件读取VISSIM网络
        robocup_dir: 从目录读取RoboCup网络
        matsim_files: 从文件读取MATsim网络
        itsumo_files: 从文件读取ITSUMO网络
        heightmap_shapefiles: 从ArcGIS shapefile读取高程图
        heightmap_geotiff: 从GeoTIFF读取高程图
        
        # 输出选项
        write_license: 在每个输出文件中包含许可证信息
        output_prefix: 应用于所有输出文件的前缀
        precision: 定义浮点输出的小数点后位数
        precision_geo: 定义经纬度输出的小数点后位数
        human_readable_time: 以时:分:秒或日:时:分:秒格式写入时间值
        output_file: 生成的网络将被写入该文件
        plain_output_prefix: 写入纯XML节点、边和连接的文件前缀
        plain_output_lanes: 即使未自定义，也写入所有车道及其属性
        junctions_join_output: 将有关连接路口的信息写入文件
        prefix: 定义边和路口名称的前缀
        amitran_output: 生成的网络将以Amitran格式写入文件
        matsim_output: 生成的网络将以MATsim格式写入文件
        opendrive_output: 生成的网络将以OpenDRIVE格式写入文件
        dlr_navteq_output: 生成的网络将写入dlr-navteq文件
        dlr_navteq_version: 要写入的dlr-navteq输出格式版本
        dlr_navteq_precision: 网络坐标将以指定的输出精度写入
        output_street_names: 输出中将包含街道名称(如果可用)
        output_original_names: 将原始名称(如果给定)作为参数写入
        street_sign_output: 将街道标志作为POI写入文件
        ptstop_output: 将公共交通站点写入文件
        ptline_output: 将公共交通线路写入文件
        ptline_clean_up: 清理不被任何线路服务的公交站点
        parking_output: 将停车区域写入文件
        railway_topology_output: 分析铁路网络的拓扑结构
        polygon_output: 写入嵌入在网络输入中且不被polyconvert支持的形状
        opendrive_output_straight_threshold: 当直线段之间的角度变化超过FLOAT度时构建参数化曲线
        opendrive_output_lefthand_left: 在左侧行驶网络中将车道写在左侧(正索引)
        opendrive_output_shape_match_dist: 将加载的形状匹配到FLOAT范围内最近的边缘并导出为道路对象
        """
        
        cmd = ["netconvert"]
        
        # 添加输入选项
        if sumo_net_file:
            cmd.extend(["-s", sumo_net_file])
        if node_files:
            cmd.extend(["-n", node_files])
        if edge_files:
            cmd.extend(["-e", edge_files])
        if connection_files:
            cmd.extend(["-x", connection_files])
        if tllogic_files:
            cmd.extend(["-i", tllogic_files])
        if type_files:
            cmd.extend(["-t", type_files])
        if ptstop_files:
            cmd.extend(["--ptstop-files", ptstop_files])
        if ptline_files:
            cmd.extend(["--ptline-files", ptline_files])
        if polygon_files:
            cmd.extend(["--polygon-files", polygon_files])
        if shapefile_prefix:
            cmd.extend(["--shapefile-prefix", shapefile_prefix])
        if dlr_navteq_prefix:
            cmd.extend(["--dlr-navteq-prefix", dlr_navteq_prefix])
        if osm_files:
            cmd.extend(["--osm-files", osm_files])
        if opendrive_files:
            cmd.extend(["--opendrive-files", opendrive_files])
        if visum_file:
            cmd.extend(["--visum-file", visum_file])
        if vissim_file:
            cmd.extend(["--vissim-file", vissim_file])
        if robocup_dir:
            cmd.extend(["--robocup-dir", robocup_dir])
        if matsim_files:
            cmd.extend(["--matsim-files", matsim_files])
        if itsumo_files:
            cmd.extend(["--itsumo-files", itsumo_files])
        if heightmap_shapefiles:
            cmd.extend(["--heightmap.shapefiles", heightmap_shapefiles])
        if heightmap_geotiff:
            cmd.extend(["--heightmap.geotiff", heightmap_geotiff])
        
        # 添加输出选项
        if write_license:
            cmd.append("--write-license")
        if output_prefix:
            cmd.extend(["--output-prefix", output_prefix])
        if precision is not None:
            cmd.extend(["--precision", str(precision)])
        if precision_geo is not None:
            cmd.extend(["--precision.geo", str(precision_geo)])
        if human_readable_time:
            cmd.append("-H")
        if output_file:
            cmd.extend(["-o", output_file])
        if plain_output_prefix:
            cmd.extend(["-p", plain_output_prefix])
        if plain_output_lanes:
            cmd.append("--plain-output.lanes")
        if junctions_join_output:
            cmd.extend(["--junctions.join-output", junctions_join_output])
        if prefix:
            cmd.extend(["--prefix", prefix])
        if amitran_output:
            cmd.extend(["--amitran-output", amitran_output])
        if matsim_output:
            cmd.extend(["--matsim-output", matsim_output])
        if opendrive_output:
            cmd.extend(["--opendrive-output", opendrive_output])
        if dlr_navteq_output:
            cmd.extend(["--dlr-navteq-output", dlr_navteq_output])
        if dlr_navteq_version:
            cmd.extend(["--dlr-navteq.version", dlr_navteq_version])
        if dlr_navteq_precision is not None:
            cmd.extend(["--dlr-navteq.precision", str(dlr_navteq_precision)])
        if output_street_names:
            cmd.append("--output.street-names")
        if output_original_names:
            cmd.append("--output.original-names")
        if street_sign_output:
            cmd.extend(["--street-sign-output", street_sign_output])
        if ptstop_output:
            cmd.extend(["--ptstop-output", ptstop_output])
        if ptline_output:
            cmd.extend(["--ptline-output", ptline_output])
        if ptline_clean_up:
            cmd.append("--ptline-clean-up")
        if parking_output:
            cmd.extend(["--parking-output", parking_output])
        if railway_topology_output:
            cmd.extend(["--railway.topology.output", railway_topology_output])
        if polygon_output:
            cmd.extend(["--polygon-output", polygon_output])
        if opendrive_output_straight_threshold is not None:
            cmd.extend(["--opendrive-output.straight-threshold", str(opendrive_output_straight_threshold)])
        if opendrive_output_lefthand_left:
            cmd.append("--opendrive-output.lefthand-left")
        if opendrive_output_shape_match_dist is not None:
            cmd.extend(["--opendrive-output.shape-match-dist", str(opendrive_output_shape_match_dist)])
        
        if ctx:
            ctx.info(f"执行命令: {' '.join(cmd)}")
        
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        result = {
            "success": process.returncode == 0,
            "message": "网络转换成功" if process.returncode == 0 else "网络转换失败",
            "stdout": process.stdout,
            "stderr": process.stderr
        }
        
        # 添加输出文件信息
        if output_file and os.path.exists(output_file):
            result["output_file"] = output_file
        if plain_output_prefix:
            nodes_file = f"{plain_output_prefix}.nod.xml"
            edges_file = f"{plain_output_prefix}.edg.xml"
            connections_file = f"{plain_output_prefix}.con.xml"
            types_file = f"{plain_output_prefix}.typ.xml"
            if os.path.exists(nodes_file):
                result["nodes_file"] = nodes_file
            if os.path.exists(edges_file):
                result["edges_file"] = edges_file
            if os.path.exists(connections_file):
                result["connections_file"] = connections_file
            if os.path.exists(types_file):
                result["types_file"] = types_file
        
        return result

# ────────────────────────────────────────────────────────────────────────────────
# TOOL 2: 网络生成器 (netgenerate)
# ────────────────────────────────────────────────────────────────────────────────
@bin_mcp.tool()
async def netgenerate(
        # 网格网络选项
        grid: bool = False,
        grid_number: int = None,
        grid_length: float = None,
        grid_x_number: int = None,
        grid_y_number: int = None,
        grid_x_length: float = None,
        grid_y_length: float = None,
        grid_attach_length: float = None,
        grid_x_attach_length: float = None,
        grid_y_attach_length: float = None,
        
        # 蜘蛛网络选项
        spider: bool = False,
        spider_arm_number: int = None,
        spider_circle_number: int = None,
        spider_space_radius: float = None,
        spider_omit_center: bool = False,
        spider_attach_length: float = None,
        
        # 随机网络选项
        rand: bool = False,
        rand_iterations: int = None,
        rand_max_distance: float = None,
        rand_min_distance: float = None,
        rand_min_angle: float = None,
        rand_num_tries: int = None,
        rand_connectivity: float = None,
        rand_neighbor_dist1: float = None,
        rand_neighbor_dist2: float = None,
        rand_neighbor_dist3: float = None,
        rand_neighbor_dist4: float = None,
        rand_neighbor_dist5: float = None,
        rand_neighbor_dist6: float = None,
        rand_grid: bool = False,
        
        # 输入选项
        type_files: str = None,
        
        # 输出选项
        write_license: bool = False,
        output_prefix: str = None,
        precision: int = None,
        precision_geo: int = None,
        human_readable_time: bool = False,
        alphanumerical_ids: bool = False,
        output_file: str = None,
        plain_output_prefix: str = None,
        plain_output_lanes: bool = False,
        junctions_join_output: str = None,
        prefix: str = None,
        amitran_output: str = None,
        matsim_output: str = None,
        opendrive_output: str = None,
        dlr_navteq_output: str = None,
        dlr_navteq_version: str = None,
        dlr_navteq_precision: int = None,
        output_street_names: bool = False,
        output_original_names: bool = False,
        street_sign_output: str = None,
        opendrive_output_straight_threshold: float = None,
        
        ctx: Context = None
    ) -> Dict[str, Any]:
        """使用netgenerate生成SUMO网络
        
        参数:
        # 网格网络选项
        grid: 强制NETGEN构建网格状网络
        grid_number: 两个方向上的路口数量
        grid_length: 两个方向上的街道长度
        grid_x_number: x方向上的路口数量，覆盖grid_number
        grid_y_number: y方向上的路口数量，覆盖grid_number
        grid_x_length: 水平街道的长度，覆盖grid_length
        grid_y_length: 垂直街道的长度，覆盖grid_length
        grid_attach_length: 边界处附加街道的长度，0表示不附加街道
        grid_x_attach_length: x方向边界处附加街道的长度，0表示不附加街道
        grid_y_attach_length: y方向边界处附加街道的长度，0表示不附加街道
        
        # 蜘蛛网络选项
        spider: 强制NETGEN构建蜘蛛网状网络
        spider_arm_number: 网络中的轴数
        spider_circle_number: 网络中的圆圈数
        spider_space_radius: 圆圈之间的距离
        spider_omit_center: 省略网络的中心节点
        spider_attach_length: 边界处附加街道的长度，0表示不附加街道
        
        # 随机网络选项
        rand: 强制NETGEN构建随机网络
        rand_iterations: 描述将边添加到网络的次数
        rand_max_distance: 每条边的最大距离
        rand_min_distance: 每条边的最小距离
        rand_min_angle: 每对(双向)道路的最小角度，以度为单位
        rand_num_tries: 创建每个节点的尝试次数
        rand_connectivity: 道路在每个节点继续的概率
        rand_neighbor_dist1: 节点恰好有1个邻居的概率
        rand_neighbor_dist2: 节点恰好有2个邻居的概率
        rand_neighbor_dist3: 节点恰好有3个邻居的概率
        rand_neighbor_dist4: 节点恰好有4个邻居的概率
        rand_neighbor_dist5: 节点恰好有5个邻居的概率
        rand_neighbor_dist6: 节点恰好有6个邻居的概率
        rand_grid: 将节点放置在间距为rand_min_distance的规则网格上
        
        # 输入选项
        type_files: 从文件读取边类型定义
        
        # 输出选项
        write_license: 在每个输出文件中包含许可证信息
        output_prefix: 应用于所有输出文件的前缀
        precision: 定义浮点输出的小数点后位数
        precision_geo: 定义经纬度输出的小数点后位数
        human_readable_time: 以时:分:秒或日:时:分:秒格式写入时间值
        alphanumerical_ids: 生成的节点ID使用字母数字代码以便于阅读
        output_file: 生成的网络将被写入该文件
        plain_output_prefix: 写入纯XML节点、边和连接的文件前缀
        plain_output_lanes: 即使未自定义，也写入所有车道及其属性
        junctions_join_output: 将有关连接路口的信息写入文件
        prefix: 定义边和路口名称的前缀
        amitran_output: 生成的网络将以Amitran格式写入文件
        matsim_output: 生成的网络将以MATsim格式写入文件
        opendrive_output: 生成的网络将以OpenDRIVE格式写入文件
        dlr_navteq_output: 生成的网络将写入dlr-navteq文件
        dlr_navteq_version: 要写入的dlr-navteq输出格式版本
        dlr_navteq_precision: 网络坐标将以指定的输出精度写入
        output_street_names: 输出中将包含街道名称(如果可用)
        output_original_names: 将原始名称(如果给定)作为参数写入
        street_sign_output: 将街道标志作为POI写入文件
        opendrive_output_straight_threshold: 当直线段之间的角度变化超过FLOAT度时构建参数化曲线
        """
        
        cmd = ["netgenerate"]
        
        # 添加网格网络选项
        if grid:
            cmd.append("-g")
        if grid_number is not None:
            cmd.extend(["--grid.number", str(grid_number)])
        if grid_length is not None:
            cmd.extend(["--grid.length", str(grid_length)])
        if grid_x_number is not None:
            cmd.extend(["--grid.x-number", str(grid_x_number)])
        if grid_y_number is not None:
            cmd.extend(["--grid.y-number", str(grid_y_number)])
        if grid_x_length is not None:
            cmd.extend(["--grid.x-length", str(grid_x_length)])
        if grid_y_length is not None:
            cmd.extend(["--grid.y-length", str(grid_y_length)])
        if grid_attach_length is not None:
            cmd.extend(["--grid.attach-length", str(grid_attach_length)])
        if grid_x_attach_length is not None:
            cmd.extend(["--grid.x-attach-length", str(grid_x_attach_length)])
        if grid_y_attach_length is not None:
            cmd.extend(["--grid.y-attach-length", str(grid_y_attach_length)])
        
        # 添加蜘蛛网络选项
        if spider:
            cmd.append("-s")
        if spider_arm_number is not None:
            cmd.extend(["--spider.arm-number", str(spider_arm_number)])
        if spider_circle_number is not None:
            cmd.extend(["--spider.circle-number", str(spider_circle_number)])
        if spider_space_radius is not None:
            cmd.extend(["--spider.space-radius", str(spider_space_radius)])
        if spider_omit_center:
            cmd.append("--spider.omit-center")
        if spider_attach_length is not None:
            cmd.extend(["--spider.attach-length", str(spider_attach_length)])
        
        # 添加随机网络选项
        if rand:
            cmd.append("-r")
        if rand_iterations is not None:
            cmd.extend(["--rand.iterations", str(rand_iterations)])
        if rand_max_distance is not None:
            cmd.extend(["--rand.max-distance", str(rand_max_distance)])
        if rand_min_distance is not None:
            cmd.extend(["--rand.min-distance", str(rand_min_distance)])
        if rand_min_angle is not None:
            cmd.extend(["--rand.min-angle", str(rand_min_angle)])
        if rand_num_tries is not None:
            cmd.extend(["--rand.num-tries", str(rand_num_tries)])
        if rand_connectivity is not None:
            cmd.extend(["--rand.connectivity", str(rand_connectivity)])
        if rand_neighbor_dist1 is not None:
            cmd.extend(["--rand.neighbor-dist1", str(rand_neighbor_dist1)])
        if rand_neighbor_dist2 is not None:
            cmd.extend(["--rand.neighbor-dist2", str(rand_neighbor_dist2)])
        if rand_neighbor_dist3 is not None:
            cmd.extend(["--rand.neighbor-dist3", str(rand_neighbor_dist3)])
        if rand_neighbor_dist4 is not None:
            cmd.extend(["--rand.neighbor-dist4", str(rand_neighbor_dist4)])
        if rand_neighbor_dist5 is not None:
            cmd.extend(["--rand.neighbor-dist5", str(rand_neighbor_dist5)])
        if rand_neighbor_dist6 is not None:
            cmd.extend(["--rand.neighbor-dist6", str(rand_neighbor_dist6)])
        if rand_grid:
            cmd.append("--rand.grid")
        
        # 添加输入选项
        if type_files:
            cmd.extend(["-t", type_files])
        
        # 添加输出选项
        if write_license:
            cmd.append("--write-license")
        if output_prefix:
            cmd.extend(["--output-prefix", output_prefix])
        if precision is not None:
            cmd.extend(["--precision", str(precision)])
        if precision_geo is not None:
            cmd.extend(["--precision.geo", str(precision_geo)])
        if human_readable_time:
            cmd.append("-H")
        if alphanumerical_ids:
            cmd.append("--alphanumerical-ids")
        if output_file:
            cmd.extend(["-o", output_file])
        if plain_output_prefix:
            cmd.extend(["-p", plain_output_prefix])
        if plain_output_lanes:
            cmd.append("--plain-output.lanes")
        if junctions_join_output:
            cmd.extend(["--junctions.join-output", junctions_join_output])
        if prefix:
            cmd.extend(["--prefix", prefix])
        if amitran_output:
            cmd.extend(["--amitran-output", amitran_output])
        if matsim_output:
            cmd.extend(["--matsim-output", matsim_output])
        if opendrive_output:
            cmd.extend(["--opendrive-output", opendrive_output])
        if dlr_navteq_output:
            cmd.extend(["--dlr-navteq-output", dlr_navteq_output])
        if dlr_navteq_version:
            cmd.extend(["--dlr-navteq.version", dlr_navteq_version])
        if dlr_navteq_precision is not None:
            cmd.extend(["--dlr-navteq.precision", str(dlr_navteq_precision)])
        if output_street_names:
            cmd.append("--output.street-names")
        if output_original_names:
            cmd.append("--output.original-names")
        if street_sign_output:
            cmd.extend(["--street-sign-output", street_sign_output])
        if opendrive_output_straight_threshold is not None:
            cmd.extend(["--opendrive-output.straight-threshold", str(opendrive_output_straight_threshold)])
        
        cmd.extend(["--tls.guess", "true"])
        cmd.extend(["--tls.guess.threshold", "10"])

        if ctx:
            ctx.info(f"执行命令: {' '.join(cmd)}")
        
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        result = {
            "success": process.returncode == 0,
            "message": "网络生成成功" if process.returncode == 0 else "网络生成失败",
            "stdout": process.stdout,
            "stderr": process.stderr
        }
        
        # 添加输出文件信息
        if output_file and os.path.exists(output_file):
            result["output_file"] = output_file
        if plain_output_prefix:
            nodes_file = f"{plain_output_prefix}.nod.xml"
            edges_file = f"{plain_output_prefix}.edg.xml"
            connections_file = f"{plain_output_prefix}.con.xml"
            types_file = f"{plain_output_prefix}.typ.xml"
            if os.path.exists(nodes_file):
                result["nodes_file"] = nodes_file
            if os.path.exists(edges_file):
                result["edges_file"] = edges_file
            if os.path.exists(connections_file):
                result["connections_file"] = connections_file
            if os.path.exists(types_file):
                result["types_file"] = types_file
        
        return result

# ────────────────────────────────────────────────────────────────────────────────
# TOOL 3: OD矩阵转行程 (od2trips)
# ────────────────────────────────────────────────────────────────────────────────
@bin_mcp.tool()
async def od2trips(
        # 配置选项
        configuration_file: str = None,
        save_configuration: str = None,
        save_configuration_relative: bool = False,
        save_template: str = None,
        save_schema: str = None,
        save_commented: bool = False,
        
        # 输入选项
        taz_files: str = None,
        od_matrix_files: str = None,
        od_amitran_files: str = None,
        tazrelation_files: str = None,
        tazrelation_attribute: str = "count",
        
        # 输出选项
        write_license: bool = False,
        output_prefix: str = None,
        precision: int = None,
        precision_geo: int = None,
        human_readable_time: bool = False,
        output_file: str = None,
        flow_output: str = None,
        flow_output_probability: bool = False,
        pedestrians: bool = False,
        persontrips: bool = False,
        persontrips_modes: List[str] = None,
        ignore_vehicle_type: bool = False,
        junctions: bool = False,
        
        # 时间选项
        begin: str = None,
        end: str = None,
        
        # 处理选项
        scale: float = None,
        spread_uniform: bool = False,
        different_source_sink: bool = False,
        vtype: str = None,
        prefix: str = None,
        timeline: List[str] = None,
        timeline_day_in_hours: bool = False,
        no_step_log: bool = False,
        
        # 默认选项
        departlane: str = None,
        departpos: str = None,
        departspeed: str = None,
        arrivallane: str = None,
        arrivalpos: str = None,
        arrivalspeed: str = None,
        
        # 报告选项
        verbose: bool = False,
        print_options: bool = False,
        xml_validation: str = None,
        no_warnings: bool = False,
        aggregate_warnings: int = None,
        log: str = None,
        message_log: str = None,
        error_log: str = None,
        log_timestamps: bool = False,
        log_processid: bool = False,
        language: str = None,
        ignore_errors: bool = False,
        
        # 随机数选项
        random: bool = False,
        seed: int = None,
        
        ctx: Context = None
    ) -> Dict[str, Any]:
        """使用od2trips将OD矩阵转换为SUMO行程
        
        参数:
        # 配置选项
        configuration_file: 启动时加载指定的配置
        save_configuration: 将当前配置保存到文件
        save_configuration_relative: 保存配置时强制使用相对路径
        save_template: 将配置模板(空)保存到文件
        save_schema: 将配置模式保存到文件
        save_commented: 向保存的模板、配置或模式添加注释
        
        # 输入选项
        taz_files: 从文件加载TAZ(区域;也可以从网络加载)
        od_matrix_files: 从文件加载O/D文件
        od_amitran_files: 从文件加载Amitran格式的O/D矩阵
        tazrelation_files: 从文件加载tazRelation格式的O/D矩阵
        tazrelation_attribute: 定义用于加载计数的数据属性(默认为'count')
        
        # 输出选项
        write_license: 在每个输出文件中包含许可证信息
        output_prefix: 应用于所有输出文件的前缀
        precision: 定义浮点输出的小数点后位数
        precision_geo: 定义经纬度输出的小数点后位数
        human_readable_time: 以时:分:秒或日:时:分:秒格式写入时间值
        output_file: 将行程定义写入文件
        flow_output: 将流量定义写入文件
        flow_output_probability: 写入概率流而不是均匀间隔流
        pedestrians: 写入行人而不是车辆
        persontrips: 写入人员行程而不是车辆
        persontrips_modes: 向personTrips添加modes属性
        ignore_vehicle_type: 不保存车辆类型信息
        junctions: 写入路口之间的行程
        
        # 时间选项
        begin: 定义开始时间;之前的行程将被丢弃
        end: 定义结束时间;之后的行程将被丢弃
        
        # 处理选项
        scale: 按比例缩放加载的流量
        spread_uniform: 在每个时间段内均匀分布行程
        different_source_sink: 始终选择不同的源和目的地边缘
        vtype: 定义要使用的车辆类型的名称
        prefix: 定义车辆名称的前缀
        timeline: 使用timeline作为时间线定义
        timeline_day_in_hours: 使用24小时时间线定义
        no_step_log: 禁用当前时间步的控制台输出
        
        # 默认选项
        departlane: 分配默认的出发车道
        departpos: 分配默认的出发位置
        departspeed: 分配默认的出发速度
        arrivallane: 分配默认的到达车道
        arrivalpos: 分配默认的到达位置
        arrivalspeed: 分配默认的到达速度
        
        # 报告选项
        verbose: 切换到详细输出
        print_options: 在处理前打印选项值
        xml_validation: 设置XML输入的模式验证方案
        no_warnings: 禁用警告输出
        aggregate_warnings: 当发生超过INT次时，聚合相同类型的警告
        log: 将所有消息写入文件(隐含verbose)
        message_log: 将所有非错误消息写入文件(隐含verbose)
        error_log: 将所有警告和错误写入文件
        log_timestamps: 在所有消息前写入时间戳
        log_processid: 在所有消息前写入进程ID
        language: 在消息中使用的语言
        ignore_errors: 在输入损坏时继续
        
        # 随机数选项
        random: 使用当前系统时间初始化随机数生成器
        seed: 使用给定值初始化随机数生成器
        """
        
        cmd = ["od2trips"]
        
        # 添加配置选项
        if configuration_file:
            cmd.extend(["-c", configuration_file])
        if save_configuration:
            cmd.extend(["-C", save_configuration])
        if save_configuration_relative:
            cmd.append("--save-configuration.relative")
        if save_template:
            cmd.extend(["--save-template", save_template])
        if save_schema:
            cmd.extend(["--save-schema", save_schema])
        if save_commented:
            cmd.append("--save-commented")
        
        # 添加输入选项
        if taz_files:
            cmd.extend(["-n", taz_files])
        if od_matrix_files:
            cmd.extend(["-d", od_matrix_files])
        if od_amitran_files:
            cmd.extend(["--od-amitran-files", od_amitran_files])
        if tazrelation_files:
            cmd.extend(["-z", tazrelation_files])
        if tazrelation_attribute and tazrelation_attribute != "count":
            cmd.extend(["--tazrelation-attribute", tazrelation_attribute])
        
        # 添加输出选项
        if write_license:
            cmd.append("--write-license")
        if output_prefix:
            cmd.extend(["--output-prefix", output_prefix])
        if precision is not None:
            cmd.extend(["--precision", str(precision)])
        if precision_geo is not None:
            cmd.extend(["--precision.geo", str(precision_geo)])
        if human_readable_time:
            cmd.append("-H")
        if output_file:
            cmd.extend(["-o", output_file])
        if flow_output:
            cmd.extend(["--flow-output", flow_output])
        if flow_output_probability:
            cmd.append("--flow-output.probability")
        if pedestrians:
            cmd.append("--pedestrians")
        if persontrips:
            cmd.append("--persontrips")
        if persontrips_modes:
            cmd.extend(["--persontrips.modes", ",".join(persontrips_modes)])
        if ignore_vehicle_type:
            cmd.append("--ignore-vehicle-type")
        if junctions:
            cmd.append("--junctions")
        
        # 添加时间选项
        if begin:
            cmd.extend(["-b", begin])
        if end:
            cmd.extend(["-e", end])
        
        # 添加处理选项
        if scale is not None:
            cmd.extend(["-s", str(scale)])
        if spread_uniform:
            cmd.append("--spread.uniform")
        if different_source_sink:
            cmd.append("--different-source-sink")
        if vtype:
            cmd.extend(["--vtype", vtype])
        if prefix:
            cmd.extend(["--prefix", prefix])
        if timeline:
            cmd.extend(["--timeline", ",".join(timeline)])
        if timeline_day_in_hours:
            cmd.append("--timeline.day-in-hours")
        if no_step_log:
            cmd.append("--no-step-log")
        
        # 添加默认选项
        if departlane:
            cmd.extend(["--departlane", departlane])
        if departpos:
            cmd.extend(["--departpos", departpos])
        if departspeed:
            cmd.extend(["--departspeed", departspeed])
        if arrivallane:
            cmd.extend(["--arrivallane", arrivallane])
        if arrivalpos:
            cmd.extend(["--arrivalpos", arrivalpos])
        if arrivalspeed:
            cmd.extend(["--arrivalspeed", arrivalspeed])
        
        # 添加报告选项
        if verbose:
            cmd.append("-v")
        if print_options:
            cmd.append("--print-options")
        if xml_validation:
            cmd.extend(["-X", xml_validation])
        if no_warnings:
            cmd.append("-W")
        if aggregate_warnings is not None:
            cmd.extend(["--aggregate-warnings", str(aggregate_warnings)])
        if log:
            cmd.extend(["-l", log])
        if message_log:
            cmd.extend(["--message-log", message_log])
        if error_log:
            cmd.extend(["--error-log", error_log])
        if log_timestamps:
            cmd.append("--log.timestamps")
        if log_processid:
            cmd.append("--log.processid")
        if language:
            cmd.extend(["--language", language])
        if ignore_errors:
            cmd.append("--ignore-errors")
        
        # 添加随机数选项
        if random:
            cmd.append("--random")
        if seed is not None:
            cmd.extend(["--seed", str(seed)])
        
        if ctx:
            ctx.info(f"执行命令: {' '.join(cmd)}")
        
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        result = {
            "success": process.returncode == 0,
            "message": "OD矩阵转换成功" if process.returncode == 0 else "OD矩阵转换失败",
            "stdout": process.stdout,
            "stderr": process.stderr
        }
        
        # 添加输出文件信息
        if output_file and os.path.exists(output_file):
            result["output_file"] = output_file
        if flow_output and os.path.exists(flow_output):
            result["flow_output"] = flow_output
        
        return result

# ────────────────────────────────────────────────────────────────────────────────
# 二进制工具资源
# ────────────────────────────────────────────────────────────────────────────────
@bin_mcp.resource("data://bin/config")
def get_bin_config() -> Dict[str, Any]:
    """获取二进制工具配置信息"""
    return {
        "version": "1.0.0",
        "name": "SUMO Binary Tools",
        "description": "SUMO核心二进制工具包，提供网络转换、网络生成和OD矩阵处理功能",
        "tools": [
            "netconvert",
            "netgenerate", 
            "od2trips"
        ],
        "core_binaries": [
            "netconvert.exe - 网络格式转换工具",
            "netgenerate.exe - 网络生成工具",
            "od2trips.exe - OD矩阵转行程工具"
        ],
        "supported_formats": [
            "OpenStreetMap (OSM)",
            "OpenDRIVE",
            "SUMO网络格式",
            "Shapefile",
            "Visum",
            "Vissim",
            "MATSim",
            "NavTeq"
        ],
        "capabilities": [
            "多格式网络导入导出",
            "网络拓扑生成",
            "交通需求处理",
            "坐标系转换",
            "网络验证和修复"
        ]
    }

@bin_mcp.resource("data://bin/help")
def get_bin_help() -> Dict[str, str]:
    """获取二进制工具帮助信息"""
    return {
        "netconvert": "SUMO网络转换工具，支持多种格式间的网络数据转换，包括OSM、OpenDRIVE、Shapefile等格式的导入导出",
        "netgenerate": "SUMO网络生成工具，可以生成各种拓扑结构的道路网络，包括网格、随机、蜘蛛网等类型",
        "od2trips": "OD矩阵转行程工具，将起点-终点(Origin-Destination)矩阵转换为具体的车辆行程定义"
    }

@bin_mcp.resource("data://bin/examples")
def get_bin_examples() -> Dict[str, Any]:
    """获取二进制工具使用示例"""
    return {
        "osm_import": {
            "description": "从OpenStreetMap导入网络",
            "tool": "netconvert",
            "parameters": {
                "osm_files": "map.osm",
                "output_file": "network.net.xml",
                "geometry_remove": True,
                "roundabouts_guess": True
            }
        },
        "grid_network": {
            "description": "生成网格状道路网络",
            "tool": "netgenerate",
            "parameters": {
                "grid": True,
                "grid_number": 5,
                "grid_length": 200,
                "output_file": "grid_network.net.xml"
            }
        },
        "od_conversion": {
            "description": "OD矩阵转换为行程",
            "tool": "od2trips",
            "parameters": {
                "od_matrix_files": "od_matrix.xml",
                "output_file": "trips.trips.xml",
                "scale": 1.0,
                "spread": 3600
            }
        },
        "opendrive_import": {
            "description": "从OpenDRIVE导入高精度地图",
            "tool": "netconvert",
            "parameters": {
                "opendrive_files": "highway.xodr",
                "output_file": "highway.net.xml",
                "opendrive_ignore_widths": False
            }
        }
    }

# 如果直接运行此文件，启动二进制工具服务器
if __name__ == "__main__":
    print("启动SUMO二进制工具服务器...")
    bin_mcp.run(transport="sse", host="127.0.0.1", port=8026)
