#!/usr/bin/env python3
"""
計算和繪製不同 SLOT 間的時間間隔分析工具
"""

import sys
import re
import argparse
from collections import defaultdict
import numpy as np
import matplotlib.pyplot as plt

def parse_log_file(log_path):
    """
    解析 log 文件，提取 timestamp、frame、slot 和 event type
    """
    entries = []
    try:
        with open(log_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                # 解析格式: [timestamp] frame=X slot=Y tZ
                match = re.match(r'\[(\d+\.\d+)\]\s+frame=(\d+)\s+slot=(\d+)\s+(t\d+)', line)
                if match:
                    timestamp = float(match.group(1))
                    frame = int(match.group(2))
                    slot = int(match.group(3))
                    event_type = match.group(4)
                    
                    entries.append({
                        'timestamp': timestamp,
                        'frame': frame,
                        'slot': slot,
                        'event': event_type
                    })
    except FileNotFoundError:
        print(f"錯誤: 找不到文件 {log_path}")
        sys.exit(1)
    
    return entries

def extract_t1_slots(entries):
    """
    提取每個 slot 的 T1 timestamp（固定參考 T1）
    """
    t1_slots = {}
    
    for entry in entries:
        if entry['event'] == 't1':
            slot_id = (entry['frame'], entry['slot'])
            t1_slots[slot_id] = entry['timestamp']
    
    return t1_slots

def calculate_intervals(t1_slots):
    """
    計算相鄰 slot 間的時間間隔
    返回 slot 編號和對應的時間間隔（毫秒）
    """
    if len(t1_slots) < 2:
        print("警告: 沒有足夠的 T1 數據來計算間隔")
        return [], []
    
    # 按時間順序排序
    sorted_slots = sorted(t1_slots.items(), key=lambda x: x[1])
    
    slot_labels = []
    intervals_ms = []
    
    for i in range(1, len(sorted_slots)):
        prev_slot, prev_time = sorted_slots[i-1]
        curr_slot, curr_time = sorted_slots[i]
        
        interval = (curr_time - prev_time) * 1000  # 轉換為毫秒
        intervals_ms.append(interval)
        
        # 創建槽位標籤
        label = f"F{curr_slot[0]}_S{curr_slot[1]}"
        slot_labels.append(label)
    
    return slot_labels, intervals_ms

def plot_intervals(slot_labels, intervals_ms, output_path=None):
    """
    繪製時間間隔圖表
    """
    fig, ax = plt.subplots(figsize=(14, 6))
    
    # 繪製柱狀圖
    x_pos = np.arange(len(slot_labels))
    ax.bar(x_pos, intervals_ms, color='steelblue', alpha=0.8, edgecolor='black')
    
    # 添加平均線
    avg_interval = np.mean(intervals_ms)
    ax.axhline(y=avg_interval, color='red', linestyle='--', linewidth=2, 
               label=f'平均值: {avg_interval:.4f} ms')
    
    # 設置 x 軸標籤（每 5 個顯示一個以避免重疊）
    tick_positions = np.arange(0, len(slot_labels), max(1, len(slot_labels)//15))
    ax.set_xticks(tick_positions)
    ax.set_xticklabels([slot_labels[i] for i in tick_positions], rotation=45, ha='right')
    
    ax.set_xlabel('Slot 編號 (Frame_Slot)', fontsize=12, fontweight='bold')
    ax.set_ylabel('時間間隔 (毫秒)', fontsize=12, fontweight='bold')
    ax.set_title('相鄰 Slot 間的時間間隔分析', fontsize=14, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"✓ 圖表已保存: {output_path}")
    
    plt.show()

def print_statistics(intervals_ms):
    """
    打印統計信息
    """
    if not intervals_ms:
        print("沒有數據可顯示統計")
        return
    
    print("\n" + "="*50)
    print("時間間隔統計信息")
    print("="*50)
    print(f"總計測量次數: {len(intervals_ms)}")
    print(f"最小間隔: {np.min(intervals_ms):.6f} ms")
    print(f"最大間隔: {np.max(intervals_ms):.6f} ms")
    print(f"平均間隔: {np.mean(intervals_ms):.6f} ms")
    print(f"標準差:   {np.std(intervals_ms):.6f} ms")
    print(f"中位數:   {np.median(intervals_ms):.6f} ms")
    print("="*50 + "\n")

def main():
    parser = argparse.ArgumentParser(
        description='計算和分析不同 SLOT 間的時間間隔',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
使用範例:
  python slot_interval_analyzer.py log.txt
  python slot_interval_analyzer.py log.txt -o output.png
  python slot_interval_analyzer.py --help
        '''
    )
    
    parser.add_argument('log_file', help='輸入的 log 文件路徑')
    parser.add_argument('-o', '--output', default=None,
                       help='輸出圖表的保存路徑（默認: 不保存）')
    
    args = parser.parse_args()
    
    print(f"📖 正在解析 log 文件: {args.log_file}")
    entries = parse_log_file(args.log_file)
    print(f"✓ 解析成功，共找到 {len(entries)} 條記錄")
    
    print("🔍 提取 T1 事件...")
    t1_slots = extract_t1_slots(entries)
    print(f"✓ 找到 {len(t1_slots)} 個 T1 event")
    
    print("📊 計算時間間隔...")
    slot_labels, intervals_ms = calculate_intervals(t1_slots)
    
    # 打印統計信息
    print_statistics(intervals_ms)
    
    # 繪製圖表
    print("🎨 正在繪製圖表...")
    plot_intervals(slot_labels, intervals_ms, output_path=args.output)
    
    print("✅ 分析完成！")

if __name__ == '__main__':
    main()
