#!/usr/bin/env python3
import re
import json
import sys
import matplotlib.pyplot as plt
from collections import defaultdict

def parse_log_file(filepath):
    """解析日誌文件並提取所有條目"""
    entries = []
    pattern = r'\[(\d+\.\d+)\]\s+frame=(\d+)\s+slot=(\d+)\s+(start|stop-\w+)'
    
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

def create_pairs(entries):
    """創建start和stop的配對"""
    pairs = defaultdict(list)
    start_map = {}  # key: (frame, slot), value: timestamp
    
    for entry in entries:
        key = (entry['frame'], entry['slot'])
        
        if entry['event'] == 'start':
            start_map[key] = entry['timestamp']
        elif entry['event'].startswith('stop-'):
            suffix = entry['event'].replace('stop-', '')
            if key in start_map:
                pair = {
                    'frame': entry['frame'],
                    'slot': entry['slot'],
                    'start_timestamp': start_map[key],
                    'stop_timestamp': entry['timestamp'],
                    'duration_us': (entry['timestamp'] - start_map[key]) * 1e6,
                    'suffix': suffix
                }
                pairs[suffix].append(pair)
    
    return pairs

def save_json(pairs, output_file):
    """保存配對結果為JSON"""
    with open(output_file, 'w') as f:
        json.dump(pairs, f, indent=2)

def plot_pairs(pairs, title_prefix, output_prefix):
    """為每個後綴繪製獨立圖表"""
    for suffix, pair_list in pairs.items():
        if not pair_list:
            continue
        
        # 準備數據
        slots = [f"{p['frame']}/{p['slot']}" for p in pair_list]
        durations = [p['duration_us'] for p in pair_list]
        
        # 創建圖表
        plt.figure(figsize=(12, 6))
        plt.plot(range(len(durations)), durations, marker='o', linestyle='-', linewidth=1, markersize=3)
        
        plt.title(f'{title_prefix} - {suffix}')
        plt.xlabel('Frame/Slot Index')
        plt.ylabel('Duration (μs)')
        plt.grid(True, alpha=0.3)
        
        # 添加統計信息
        avg_duration = sum(durations) / len(durations)
        max_duration = max(durations)
        min_duration = min(durations)
        
        stats_text = f'Avg: {avg_duration:.2f}μs | Min: {min_duration:.2f}μs | Max: {max_duration:.2f}μs | Count: {len(durations)}'
        plt.text(0.5, 0.95, stats_text, transform=plt.gca().transAxes, 
                ha='center', va='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.tight_layout()
        
        # 保存圖表
        output_file = f'{output_prefix}-{suffix}.png'
        plt.savefig(output_file, dpi=150)
        plt.close()
        
        print(f'已生成圖表: {output_file}')

def main():
    if len(sys.argv) != 2:
        print(f'使用方法: {sys.argv[0]} <log_file_path>')
        print(f'範例: {sys.argv[0]} ./measure-monolithic.txt')
        sys.exit(1)
    
    log_file = sys.argv[1]
    
    # 從檔名提取measure-後綴
    import os
    basename = os.path.basename(log_file)
    if basename.startswith('measure-') and basename.endswith('.txt'):
        suffix = basename.replace('measure-', '').replace('.txt', '')
    else:
        suffix = basename.replace('.txt', '')
    
    print(f'解析日誌文件: {log_file}')
    
    # 解析日誌
    entries = parse_log_file(log_file)
    print(f'解析到 {len(entries)} 條日誌')
    
    # 創建配對
    pairs = create_pairs(entries)
    
    # 輸出統計
    total_pairs = sum(len(p) for p in pairs.values())
    print(f'\n配對統計:')
    print(f'總配對數: {total_pairs}')
    for event_suffix, pair_list in pairs.items():
        print(f'  {event_suffix}: {len(pair_list)} 對')
    
    # 保存JSON
    json_file = f'pairs-{suffix}.json'
    save_json(pairs, json_file)
    print(f'\n已保存JSON: {json_file}')
    
    # 繪製圖表
    print(f'\n開始繪製圖表...')
    plot_pairs(pairs, f'measure-{suffix}', f'plot-{suffix}')
    
    print(f'\n完成!')

if __name__ == '__main__':
    main()

