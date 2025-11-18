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
                duration_us = (entry['timestamp'] - start_map[key]) * 1e6
                # 過濾掉超過100us的數據
                if duration_us <= 100:
                    pair = {
                        'frame': entry['frame'],
                        'slot': entry['slot'],
                        'start_timestamp': start_map[key],
                        'stop_timestamp': entry['timestamp'],
                        'duration_us': duration_us,
                        'suffix': suffix
                    }
                    pairs[suffix].append(pair)
    
    return pairs

def save_json(pairs, output_file):
    """保存配對結果為JSON"""
    with open(output_file, 'w') as f:
        json.dump(pairs, f, indent=2)

def get_max_y_value(all_pairs_dict):
    """取得所有數據中的最大Y軸值"""
    max_val = 0
    for suffix_data in all_pairs_dict.values():
        for pair_list in suffix_data.values():
            if pair_list:
                max_val = max(max_val, max(p['duration_us'] for p in pair_list))
    return max_val * 1.1  # 增加10%的空間

def plot_individual_pairs(pairs, title_prefix, output_prefix):
    """為每個檔案的後綴繪製獨立圖表 (紅點散佈圖)"""
    for suffix, pair_list in pairs.items():
        if not pair_list:
            continue
        
        # 準備數據
        indices = list(range(len(pair_list)))
        durations = [p['duration_us'] for p in pair_list]
        
        # 創建圖表
        plt.figure(figsize=(12, 6))
        plt.scatter(indices, durations, color='red', s=20, alpha=0.6)
        
        plt.title(f'{title_prefix} - {suffix}')
        plt.xlabel('Measurement Index')
        plt.ylabel('Duration (μs)')
        plt.grid(True, alpha=0.3)
        plt.ylim(0, 110)
        
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
        
        print(f'已生成獨立圖表: {output_file}')

def plot_comparison(all_pairs_dict, file_labels, max_y):
    """繪製比較圖表 - 相同後綴放在一起，不同顏色表示不同檔案"""
    # 收集所有後綴
    all_suffixes = set()
    for suffix_data in all_pairs_dict.values():
        all_suffixes.update(suffix_data.keys())
    
    all_suffixes = sorted(all_suffixes)
    
    colors = ['red', 'blue', 'green', 'orange', 'purple', 'brown', 'pink']
    
    for suffix in all_suffixes:
        plt.figure(figsize=(14, 6))
        
        for idx, (file_key, file_label) in enumerate(file_labels):
            pair_list = all_pairs_dict[file_key].get(suffix, [])
            if not pair_list:
                continue
            
            indices = list(range(len(pair_list)))
            durations = [p['duration_us'] for p in pair_list]
            
            color = colors[idx % len(colors)]
            plt.scatter(indices, durations, color=color, s=20, alpha=0.6, label=file_label)
        
        plt.title(f'Comparison - {suffix}')
        plt.xlabel('Measurement Index')
        plt.ylabel('Duration (μs)')
        plt.grid(True, alpha=0.3)
        plt.ylim(0, max_y)
        plt.legend(loc='upper right')
        
        plt.tight_layout()
        
        # 保存比較圖表
        output_file = f'comparison-{suffix}.png'
        plt.savefig(output_file, dpi=150)
        plt.close()
        
        print(f'已生成比較圖表: {output_file}')

def main():
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print(f'使用方法: {sys.argv[0]} <log_file1> [log_file2]')
        print(f'範例: {sys.argv[0]} ./measure-nfapi.txt ./measure-monolithic.txt')
        print(f'或: {sys.argv[0]} ./measure-monolithic.txt')
        sys.exit(1)
    
    log_files = sys.argv[1:]
    all_pairs_dict = {}
    file_labels = []
    
    # 解析所有日誌檔案
    for log_file in log_files:
        print(f'\n解析日誌文件: {log_file}')
        
        entries = parse_log_file(log_file)
        print(f'解析到 {len(entries)} 條日誌')
        
        pairs = create_pairs(entries)
        
        # 輸出統計
        total_pairs = sum(len(p) for p in pairs.values())
        print(f'有效配對統計 (≤100μs):')
        print(f'  總配對數: {total_pairs}')
        for event_suffix, pair_list in pairs.items():
            print(f'  {event_suffix}: {len(pair_list)} 對')
        
        # 提取檔名標籤
        import os
        basename = os.path.basename(log_file)
        if basename.startswith('measure-') and basename.endswith('.txt'):
            suffix = basename.replace('measure-', '').replace('.txt', '')
        else:
            suffix = basename.replace('.txt', '')
        
        all_pairs_dict[suffix] = pairs
        file_labels.append((suffix, f'measure-{suffix}'))
        
        # 保存JSON
        json_file = f'pairs-{suffix}.json'
        save_json(pairs, json_file)
        print(f'已保存JSON: {json_file}')
    
    # 計算最大Y軸值 (統一所有圖表)
    max_y = get_max_y_value(all_pairs_dict)
    print(f'\n統一Y軸最大值: {max_y:.2f}μs')
    
    # 繪製獨立圖表
    print(f'\n開始繪製獨立圖表...')
    for file_key, file_label in file_labels:
        pairs = all_pairs_dict[file_key]
        plot_individual_pairs(pairs, file_label, f'plot-{file_key}')
    
    # 如果有多個檔案，繪製比較圖表
    if len(log_files) > 1:
        print(f'\n開始繪製比較圖表...')
        plot_comparison(all_pairs_dict, file_labels, max_y)
    
    print(f'\n完成!')

if __name__ == '__main__':
    main()
