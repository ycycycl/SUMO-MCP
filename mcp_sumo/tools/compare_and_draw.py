# '''
# Compare metrics of different control methods and draw radar charts, example usage:
# python adaptive_control\utils\compare_and_draw.py --results "results\adaptive_opt\IDQN-tr3-rongdong_2_phase-0-drq_norm-wait_norm\tripinfo_100.xml" --results "results\adaptive_opt\IPPO-tr3-rongdong_2_phase-0-drq_norm-wait_norm\tripinfo_100.xml" --results "results\adaptive_opt\MAXPRESSURE-tr3-rongdong_2_phase-0-mplight-wait\tripinfo_100.xml" --results "results\adaptive_opt\MAXWAVE-tr3-rongdong_2_phase-0-wave-wait\tripinfo_100.xml" --results "results\adaptive_opt\FIXED-tr3-rongdong_2_phase-0-mplight-wait\tripinfo_100.xml" --type network
# '''
import os
import re
import csv
import sys
import time
import copy
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
sys.path.append("./utils/")
from get_score import queue_network

ap = argparse.ArgumentParser()
ap.add_argument("--results", type=str, default=None, action='append', help='''XML file path, can have multiple, path enclosed in double quotes, each path must be preceded by --results''')
ap.add_argument("--labels", type=str, default=None, action='append', help='''Legend label list, can have multiple, each label must be preceded by --labels''')
ap.add_argument("--output_dir", type=str, default=".", help='''Output directory for saving csv and png files''')
args = ap.parse_args()

path_lists = [r"results\adaptive_opt\IDQN-tr3-rongdong_2_phase-0-drq_norm-wait_norm\tripinfo_100.xml", r"results\adaptive_opt\IPPO-tr3-rongdong_2_phase-0-drq_norm-wait_norm\tripinfo_100.xml",\
                r"results\adaptive_opt\MAXPRESSURE-tr3-rongdong_2_phase-0-mplight-wait\tripinfo_100.xml", r"results\adaptive_opt\MAXWAVE-tr3-rongdong_2_phase-0-wave-wait\tripinfo_100.xml"]

if args.results is not None:
    path_lists = args.results

def get_performce_score(path):
    if not os.path.exists(path):
        return

    # Load XML file
    tree = ET.parse(path)
    root = tree.getroot()

    # Initialize metrics
    ret = {}
    ret['avg_duration'] = 0.0
    ret['avg_waitingTime'] = 0.0
    ret['total_waitingCount'] = 0
    ret['avg_queue'] = 0
    ret['avg_timeLoss'] = 0.0

    # Read queue length from metrics.csv
    epoch = re.search(r'tripinfo_(\d+).xml', str(path))
    if epoch:
        epoch = epoch.group(1)
        ret['avg_queue'] = queue_network(os.path.join(os.path.dirname(path), "metrics_"+epoch+".csv"))

    # Traverse tripinfo nodes, read information
    for tripinfo in root.findall('tripinfo'):
        # Get id attribute and add to list
        ret['avg_duration'] += float(tripinfo.get('duration'))
        ret['avg_waitingTime'] += float(tripinfo.get('waitingTime'))
        ret['total_waitingCount'] += int(tripinfo.get('waitingCount'))
        ret['avg_timeLoss'] += float(tripinfo.get('timeLoss'))

    # Calculate averages
    car_count = len(root.findall('tripinfo'))
    ret['avg_duration'] /= float(car_count)
    ret['avg_waitingTime'] /= float(car_count)
    ret['avg_timeLoss'] /= float(car_count)

    return ret

def draw_network(result_lists, legends, output_dir="."):
    ori_result = copy.deepcopy(result_lists)
    # Display Chinese labels normally
    mpl.rcParams['font.sans-serif'] = ['SimHei']
    # Auto-adjust layout
    mpl.rcParams.update({'figure.autolayout': True})
    # Display minus sign normally
    mpl.rcParams['axes.unicode_minus'] = False
    # Disable scientific notation
    pd.set_option('display.float_format', lambda x: '%.2f' % x) 

    data_length = len(result_lists[0])
    angles = np.linspace(0, 2*np.pi, data_length, endpoint=False)
    labels = ['Avg Trip Time', 'Avg Waiting\nTime', 'Total Wait Count', 'Avg Queue Length', '  Avg Delay']
    angles = np.concatenate((angles, [angles[0]]))
    labels = np.concatenate((labels, [labels[0]]))
    for i in range(len(result_lists)):
        result_lists[i] = list(result_lists[i].values())
        result_lists[i] = np.concatenate((result_lists[i], [result_lists[i][0]]))
    fig = plt.figure(figsize=(10, 6), dpi=100)
    fig.suptitle("Comparison of Control Methods at Network Level")

    ax = plt.subplot(111, polar=True) 

    # Modify the outermost grid line to be thick solid, inner grid lines to be thin solid
    for j in np.arange(20, 100+20, 20):
        ax.plot(angles, (len(result_lists[0]))*[j/100.0], '-', lw=0.5, color='black')  # Thin solid line
    ax.plot(angles, (len(result_lists[0]))*[1], '-', lw=1.5, color='black')  # Thick solid line

    # Draw radar chart axes
    for j in range(data_length):
        ax.plot([angles[j], angles[j]], [0, 100], '-', lw=0.5, color='black')

    # Hide the outermost circle
    ax.spines['polar'].set_visible(False)
    # Hide circular grid lines
    ax.grid(False)

    colors = ['r', 'y', 'c', 'b', 'g']
    # Normalize data
    for j in range(len(result_lists[0])):
        max_val = -np.inf
        min_val = np.inf
        for i in range(len(result_lists)):
            # The jth metric of the ith data group
            if result_lists[i][j] > max_val:
                max_val = result_lists[i][j]
            if result_lists[i][j] < min_val:
                min_val = result_lists[i][j]
        if max_val != min_val:
            max_val *= 1.1
            min_val *= 0.9
        for i in range(len(result_lists)):
            if max_val == min_val:
                result_lists[i][j] = 0
            else:
                result_lists[i][j] = float(result_lists[i][j] - min_val) / float(max_val - min_val)
        for i in range(len(result_lists)):
            # Flip it, larger values should indicate worse performance
            result_lists[i][j] = 1 - result_lists[i][j]

    
    # First write original data to csv
    csv_labels = ['Avg Trip Time(s)', 'Avg Waiting Time(s/veh)', 'Total Wait Count', 'Avg Queue Length(veh)', 'Avg Delay(s/veh)']
    # CSV filename
    csv_filename = os.path.join(output_dir, 'comparison_metrics.csv')
    os.makedirs(output_dir, exist_ok=True)

    # Write to CSV file
    with open(csv_filename, mode='w', newline='', encoding='utf-8-sig') as file:
        writer = csv.writer(file)
        # Write header, first column empty
        writer.writerow([""] + csv_labels)
        # Write data
        for i in range(len(ori_result)):
            row = [legends[i]] + list(ori_result[i].values())  # Combine legend and data into one row
            writer.writerow(row)

    print(f'Data written to {csv_filename}')

    # Draw each data group
    for i in range(len(result_lists)):
        ax.plot(angles, result_lists[i], color=colors[i], label=legends[i])
        ax.fill(angles, result_lists[i], color=colors[i], alpha=0.25)

    ax.set_thetagrids(angles*180/np.pi, labels)
    ax.set_theta_zero_location('N')
    ax.set_rlim(0, 1)
    ax.set_rlabel_position(0)
    ax.legend(loc="upper right", bbox_to_anchor=(1.2, 1.0))  # Add legend
    ax.set_yticklabels([])
    plt.savefig(os.path.join(output_dir, 'comparison_radar.png'))


time_start=time.time()
# Parse each address in path_lists and put the parsing results into score_lists
score_lists = []
default_labels = ['DQN', 'PPO', 'Max Pressure', 'Actuated Control', 'Fixed Time']
labels = args.labels if args.labels is not None else default_labels[:len(path_lists)]
for i in range(len(path_lists)):
    tmp = get_performce_score(Path(path_lists[i]))
    if tmp is not None:   
        score_lists.append(tmp)
        print(labels[i])
        print(tmp)
draw_network(score_lists, labels, args.output_dir)
time_end=time.time()