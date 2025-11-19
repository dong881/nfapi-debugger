#!/usr/bin/env python3
import sys

def merge_and_sort_files(file1, file2, output_file):
    lines = []
    timestamp_pattern = r'\[(\d+\.\d+)\]'
    import re

    # 收集所有行和其timestamp
    for filename in [file1, file2]:
        with open(filename, 'r') as f:
            for line in f:
                match = re.search(timestamp_pattern, line)
                if match:
                    ts = float(match.group(1))
                    lines.append((ts, line.rstrip('\n')))
    
    # 按timestamp排序
    lines.sort(key=lambda x: x[0])
    
    # 寫入新檔案
    with open(output_file, 'w') as f:
        for ts, line in lines:
            f.write(f"{line}\n")
    
    print(f"已合併並排序到: {output_file}")

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print(f"使用方法: {sys.argv[0]} ./measure.txt ./measure-VNF.txt ./measure-nfapi.txt")
        sys.exit(1)
    file1 = sys.argv[1]
    file2 = sys.argv[2]
    output_file = sys.argv[3]
    merge_and_sort_files(file1, file2, output_file)
