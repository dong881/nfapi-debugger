#!/usr/bin/env python3
import re
import json
import sys
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict

def parse_log_file(filepath):
    """解析日誌文件並提取所有條目"""
    entries = []
    pattern = r'\[(\d+\.\d+)\]\s+frame=(\d+)\s+slot=(\d+)\s+(t\d+(?:-\w+)?)'
    
    with open(filepath, 'r') as f:
        for line in f:
            match = re.match(pattern, line.strip())
            if match:
                timestamp, frame, slot, event = match.groups()
                entries.append({
                    'timestamp': float(timestamp),
                    'frame': int(frame),
                    'slot': int(slot),
                    'event': event
                })
    return entries

def organize_by_frame_slot(entries):
    """按照frame和slot組織數據"""
    data = defaultdict(lambda: defaultdict(list))
    
    for entry in entries:
        key = (entry['frame'], entry['slot'])
        data[key][entry['event']].append(entry['timestamp'])
    
    return data

def calculate_time_differences(data):
    """計算時間差異"""
    results = {
        'ultti': defaultdict(list),
        'uldci': defaultdict(list),
        'dltti': defaultdict(list),
        'txdata': defaultdict(list)
    }
    
    for (frame, slot), events in data.items():
        # 獲取時間戳
        t1 = events.get('t1', [None])[0]
        t2 = events.get('t2', [None])[0]
        t3 = events.get('t3', [None])[0]
        t5 = events.get('t5', [None])[0]
        
        t4_ultti = events.get('t4-ultti', [None])[0]
        t4_uldci = events.get('t4-uldci', [None])[0]
        t4_dltti = events.get('t4-dltti', [None])[0]
        t4_txdata = events.get('t4-txdata', [None])[0]
        
        # 計算ultti的時間差
        if t4_ultti:
            if t1 and t2:
                results['ultti']['t1-t2'].append({'frame': frame, 'slot': slot, 'duration_us': (t2 - t1) * 1e6})
            if t2 and t3:
                results['ultti']['t2-t3'].append({'frame': frame, 'slot': slot, 'duration_us': (t3 - t2) * 1e6})
            if t3 and t4_ultti:
                results['ultti']['t3-t4'].append({'frame': frame, 'slot': slot, 'duration_us': (t4_ultti - t3) * 1e6})
            if t4_ultti and t5:
                results['ultti']['t4-t5'].append({'frame': frame, 'slot': slot, 'duration_us': (t5 - t4_ultti) * 1e6})
            if t1 and t5:
                results['ultti']['t1-t5'].append({'frame': frame, 'slot': slot, 'duration_us': (t5 - t1) * 1e6})
        
        # 計算uldci的時間差
        if t4_uldci:
            if t1 and t2:
                results['uldci']['t1-t2'].append({'frame': frame, 'slot': slot, 'duration_us': (t2 - t1) * 1e6})
            if t2 and t3:
                results['uldci']['t2-t3'].append({'frame': frame, 'slot': slot, 'duration_us': (t3 - t2) * 1e6})
            if t3 and t4_uldci:
                results['uldci']['t3-t4'].append({'frame': frame, 'slot': slot, 'duration_us': (t4_uldci - t3) * 1e6})
            if t4_uldci and t5:
                results['uldci']['t4-t5'].append({'frame': frame, 'slot': slot, 'duration_us': (t5 - t4_uldci) * 1e6})
            if t1 and t5:
                results['uldci']['t1-t5'].append({'frame': frame, 'slot': slot, 'duration_us': (t5 - t1) * 1e6})
        
        # 計算dltti的時間差
        if t4_dltti:
            if t1 and t2:
                results['dltti']['t1-t2'].append({'frame': frame, 'slot': slot, 'duration_us': (t2 - t1) * 1e6})
            if t2 and t3:
                results['dltti']['t2-t3'].append({'frame': frame, 'slot': slot, 'duration_us': (t3 - t2) * 1e6})
            if t3 and t4_dltti:
                results['dltti']['t3-t4'].append({'frame': frame, 'slot': slot, 'duration_us': (t4_dltti - t3) * 1e6})
            if t4_dltti and t5:
                results['dltti']['t4-t5'].append({'frame': frame, 'slot': slot, 'duration_us': (t5 - t4_dltti) * 1e6})
            if t1 and t5:
                results['dltti']['t1-t5'].append({'frame': frame, 'slot': slot, 'duration_us': (t5 - t1) * 1e6})
        
        # 計算txdata的時間差
        if t4_txdata:
            if t1 and t2:
                results['txdata']['t1-t2'].append({'frame': frame, 'slot': slot, 'duration_us': (t2 - t1) * 1e6})
            if t2 and t3:
                results['txdata']['t2-t3'].append({'frame': frame, 'slot': slot, 'duration_us': (t3 - t2) * 1e6})
            if t3 and t4_txdata:
                results['txdata']['t3-t4'].append({'frame': frame, 'slot': slot, 'duration_us': (t4_txdata - t3) * 1e6})
            if t4_txdata and t5:
                results['txdata']['t4-t5'].append({'frame': frame, 'slot': slot, 'duration_us': (t5 - t4_txdata) * 1e6})
            if t1 and t5:
                results['txdata']['t1-t5'].append({'frame': frame, 'slot': slot, 'duration_us': (t5 - t1) * 1e6})
    
    return results

def plot_time_differences(all_results, file_labels):
    """繪製時間差異比較圖"""
    categories = ['ultti', 'uldci', 'dltti', 'txdata']
    time_intervals = ['t1-t2', 't2-t3', 't3-t4', 't4-t5', 't1-t5']
    colors = ['red', 'blue']
    
    for category in categories:
        for interval in time_intervals:
            plt.figure(figsize=(14, 6))
            
            for idx, (file_key, file_label) in enumerate(file_labels):
                data_list = all_results[file_key][category][interval]
                if not data_list:
                    continue
                
                # 過濾超過100us的數據
                filtered_data = [d for d in data_list if d['duration_us'] <= 100]
                
                if not filtered_data:
                    continue
                
                indices = list(range(len(filtered_data)))
                durations = [d['duration_us'] for d in filtered_data]
                
                color = colors[idx % len(colors)]
                plt.scatter(indices, durations, color=color, s=20, alpha=0.6, label=file_label)
            
            plt.title(f'Comparison - {category} - {interval}')
            plt.xlabel('Measurement Index')
            plt.ylabel('Duration (μs)')
            plt.grid(True, alpha=0.3)
            plt.ylim(0, 110)
            plt.legend(loc='upper right')
            plt.tight_layout()
            
            output_file = f'comparison-{category}-{interval}.png'
            plt.savefig(output_file, dpi=150)
            plt.close()
            
            print(f'已生成比較圖表: {output_file}')

def plot_scheduling_heatmap(data, file_label):
    """繪製排程熱圖 - Y軸20個slot, X軸Frame"""
    # 收集所有frame和slot的t4事件
    scheduling_data = defaultdict(lambda: defaultdict(lambda: {'ultti': False, 'uldci': False, 'dltti': False, 'txdata': False}))
    
    frames = set()
    for (frame, slot), events in data.items():
        frames.add(frame)
        if 't4-ultti' in events:
            scheduling_data[frame][slot]['ultti'] = True
        if 't4-uldci' in events:
            scheduling_data[frame][slot]['uldci'] = True
        if 't4-dltti' in events:
            scheduling_data[frame][slot]['dltti'] = True
        if 't4-txdata' in events:
            scheduling_data[frame][slot]['txdata'] = True
    
    if not frames:
        print(f'警告: {file_label} 沒有找到任何t4事件')
        return
    
    frames = sorted(frames)
    slots = list(range(20))
    
    # 創建圖表
    fig, ax = plt.subplots(figsize=(max(16, len(frames) * 0.3), 10))
    
    # 繪製每個slot和frame的狀態
    for frame_idx, frame in enumerate(frames):
        for slot in slots:
            has_ul = scheduling_data[frame][slot]['ultti'] or scheduling_data[frame][slot]['uldci']
            has_dl = scheduling_data[frame][slot]['dltti'] or scheduling_data[frame][slot]['txdata']
            
            if has_ul and has_dl:
                # 上半部紅色，下半部藍色
                ax.add_patch(plt.Rectangle((frame_idx, slot), 1, 0.5, facecolor='red', edgecolor='gray', linewidth=0.5))
                ax.add_patch(plt.Rectangle((frame_idx, slot + 0.5), 1, 0.5, facecolor='blue', edgecolor='gray', linewidth=0.5))
            elif has_ul:
                ax.add_patch(plt.Rectangle((frame_idx, slot), 1, 1, facecolor='red', edgecolor='gray', linewidth=0.5))
            elif has_dl:
                ax.add_patch(plt.Rectangle((frame_idx, slot), 1, 1, facecolor='blue', edgecolor='gray', linewidth=0.5))
            else:
                ax.add_patch(plt.Rectangle((frame_idx, slot), 1, 1, facecolor='white', edgecolor='gray', linewidth=0.5))
    
    # 設置座標軸
    ax.set_xlim(0, len(frames))
    ax.set_ylim(0, 20)
    ax.set_xlabel('Frame')
    ax.set_ylabel('Slot')
    ax.set_title(f'Scheduling Heatmap - {file_label} (Red: UL, Blue: DL)')
    
    # 設置刻度
    ax.set_xticks(np.arange(len(frames)) + 0.5)
    ax.set_xticklabels(frames, rotation=90, fontsize=8)
    ax.set_yticks(np.arange(20) + 0.5)
    ax.set_yticklabels(range(20))
    
    # 添加圖例
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='red', edgecolor='gray', label='UL (ultti/uldci)'),
        Patch(facecolor='blue', edgecolor='gray', label='DL (dltti/txdata)'),
        Patch(facecolor='white', edgecolor='gray', label='No t4')
    ]
    ax.legend(handles=legend_elements, loc='upper right')
    
    plt.tight_layout()
    
    output_file = f'heatmap-{file_label}.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f'已生成排程熱圖: {output_file}')

def main():
    if len(sys.argv) != 3:
        print(f'使用方法: {sys.argv[0]} <log_file1> <log_file2>')
        print(f'範例: {sys.argv[0]} ./measure-nfapi.txt ./measure-monolithic.txt')
        sys.exit(1)
    
    log_files = sys.argv[1:3]
    all_results = {}
    all_data = {}
    file_labels = []
    
    # 解析所有日誌檔案
    for log_file in log_files:
        print(f'\n解析日誌文件: {log_file}')
        
        entries = parse_log_file(log_file)
        print(f'解析到 {len(entries)} 條日誌')
        
        data = organize_by_frame_slot(entries)
        results = calculate_time_differences(data)
        
        # 提取檔名標籤
        import os
        basename = os.path.basename(log_file)
        if basename.startswith('measure-') and basename.endswith('.txt'):
            suffix = basename.replace('measure-', '').replace('.txt', '')
        else:
            suffix = basename.replace('.txt', '')
        
        all_results[suffix] = results
        all_data[suffix] = data
        file_labels.append((suffix, suffix))
        
        # 保存JSON
        json_file = f'timing-{suffix}.json'
        with open(json_file, 'w') as f:
            json.dump({cat: {interval: data_list for interval, data_list in intervals.items()} 
                      for cat, intervals in results.items()}, f, indent=2)
        print(f'已保存JSON: {json_file}')
        
        # 輸出統計
        print(f'統計資訊:')
        for category in ['ultti', 'uldci', 'dltti', 'txdata']:
            total = sum(len(v) for v in results[category].values())
            if total > 0:
                print(f'  {category}: {total} 個測量點')
    
    # 繪製時間差異比較圖
    print(f'\n開始繪製時間差異比較圖...')
    plot_time_differences(all_results, file_labels)
    
    # 繪製排程熱圖
    print(f'\n開始繪製排程熱圖...')
    for file_key, file_label in file_labels:
        plot_scheduling_heatmap(all_data[file_key], file_label)
    
    print(f'\n完成!')

if __name__ == '__main__':
    main()
