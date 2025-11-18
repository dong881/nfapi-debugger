#!/usr/bin/env python3
"""
VNF+PNF Log Comparative Analyzer v2
- 支援負延遲值（TOO EARLY/TOO LATE）
- 支援 VNF Delays 的正負值
- 支援 PNF 的 TOO EARLY/TOO LATE 格式
- 自動過濾 ANSI 色碼
"""
import re
import pandas as pd
import matplotlib.pyplot as plt
import sys
from pathlib import Path

def strip_ansi(line):
    """去除 ANSI 色碼控制字元"""
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    return ansi_escape.sub('', line)

class VNFPNFLogParser:
    def __init__(self, log_file):
        self.log_file = log_file
        self.data = []

    def parse(self):
        """解析整個日誌檔案"""
        with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                d = self.parse_line(line)
                if d:
                    self.data.append(d)
        df = pd.DataFrame(self.data)
        return df

    def parse_line(self, line):
        """解析單行日誌"""
        line = strip_ansi(line)
        
        # 提取時間戳
        timestamp_match = re.match(r'^([\d.]+)', line)
        timestamp = float(timestamp_match.group(1)) if timestamp_match else None
        if not timestamp:
            return None

        result = {'timestamp': timestamp}

        # ========== VNF Jitter/Delay (支援正負值) ==========
        jitter_pattern = r'Jitter\(DL=(-?\d+)\s+UL=(-?\d+)\s+ULDCI=(-?\d+)\s+TxData=(-?\d+)\s*µ?s?\)'
        delay_pattern  = r'Delays\(DL=(-?\d+)\s+UL=(-?\d+)\s+ULDCI=(-?\d+)\s+TxData=(-?\d+)\s*µ?s?\)'
        jitter_match = re.search(jitter_pattern, line)
        delay_match  = re.search(delay_pattern, line)
        
        if jitter_match and delay_match:
            vals = [int(jitter_match.group(i)) for i in range(1,5)] \
                + [int(delay_match.group(i)) for i in range(1,5)]
            result.update({
                'type': 'vnf-jitterdelay',
                'dl_jitter': int(jitter_match.group(1)),
                'ul_jitter': int(jitter_match.group(2)),
                'uldci_jitter': int(jitter_match.group(3)),
                'txdata_jitter': int(jitter_match.group(4)),
                'dl_delay': int(delay_match.group(1)),
                'ul_delay': int(delay_match.group(2)),
                'uldci_delay': int(delay_match.group(3)),
                'txdata_delay': int(delay_match.group(4)),
                'abnormal': max([abs(v) for v in vals]) >= 2147483647
            })
            return result

        # ========== VNF 高延遲警告 (舊格式保留) ==========
        tti_warn = re.search(r'High DL_TTI delay=(\d+)µs', line)
        if tti_warn:
            result.update({
                'type': 'vnf-dltti',
                'dl_delay': int(tti_warn.group(1)),
                'abnormal': int(tti_warn.group(1)) >= 2147483647
            })
            return result
        
        txdata_warn = re.search(r'High TxData delay=(\d+)µs', line)
        if txdata_warn:
            result.update({
                'type': 'vnf-txdata',
                'txdata_delay': int(txdata_warn.group(1)),
                'abnormal': int(txdata_warn.group(1)) >= 2147483647
            })
            return result

        # ========== VNF 時槽同步調整 ==========
        sync = re.search(r'adjustment: (-?\d+) \(from ([\d.]+)\)', line)
        if sync:
            result.update({
                'type': 'vnf-sync',
                'sync_adjustment': int(sync.group(1)),
                'vnf_slotnum': float(sync.group(2)),
            })
            return result

        # ========== PNF DL_TTI (支援 TOO LATE 和 TOO EARLY) ==========
        # [PNF-TIMING] 格式
        pnf_dltti_timing = re.search(
            r'Message DL_TTI for ([\d.]+) arrived (TOO LATE|TOO EARLY) \(delta: (-?\d+) µs\)', line)
        if pnf_dltti_timing:
            result.update({
                'type': 'pnf-dltti',
                'slotnum': float(pnf_dltti_timing.group(1)),
                'timing_status': pnf_dltti_timing.group(2),
                'delta_us': int(pnf_dltti_timing.group(3))
            })
            return result
        
        # [PNF-DELAY] 格式（PHY 層）
        pnf_dltti_phy = re.search(
            r'DL_TTI for ([\d.]+) arrived (TOO LATE|TOO EARLY) \(delta=(-?\d+) µs\)', line)
        if pnf_dltti_phy:
            result.update({
                'type': 'pnf-dltti',
                'slotnum': float(pnf_dltti_phy.group(1)),
                'timing_status': pnf_dltti_phy.group(2),
                'delta_us': int(pnf_dltti_phy.group(3))
            })
            return result

        # ========== PNF TX_DATA (支援 TOO LATE 和 TOO EARLY) ==========
        pnf_txdata_timing = re.search(
            r'Message TX_DATA for ([\d.]+) arrived (TOO LATE|TOO EARLY) \(delta: (-?\d+) µs\)', line)
        if pnf_txdata_timing:
            result.update({
                'type': 'pnf-txdata',
                'slotnum': float(pnf_txdata_timing.group(1)),
                'timing_status': pnf_txdata_timing.group(2),
                'delta_us': int(pnf_txdata_timing.group(3))
            })
            return result
        
        pnf_txdata_phy = re.search(
            r'TX_Data for ([\d.]+) arrived (TOO LATE|TOO EARLY) \(delta=(-?\d+) µs\)', line)
        if pnf_txdata_phy:
            result.update({
                'type': 'pnf-txdata',
                'slotnum': float(pnf_txdata_phy.group(1)),
                'timing_status': pnf_txdata_phy.group(2),
                'delta_us': int(pnf_txdata_phy.group(3))
            })
            return result

        # ========== PNF UL_TTI ==========
        pnf_ultti = re.search(
            r'Message UL_TTI for ([\d.]+) arrived (TOO LATE|TOO EARLY) \(delta: (-?\d+) µs\)', line)
        if pnf_ultti:
            result.update({
                'type': 'pnf-ultti',
                'slotnum': float(pnf_ultti.group(1)),
                'timing_status': pnf_ultti.group(2),
                'delta_us': int(pnf_ultti.group(3))
            })
            return result

        return None

def plot_compare_vnf_pnf(vnf_df, pnf_df, prefix='vnf_pnf'):
    """比較 VNF 和 PNF 延遲"""
    
    # ========== 圖1: TxData 延遲對比 ==========
    vnf_txdata = vnf_df[vnf_df['type'] == 'vnf-jitterdelay'][['timestamp', 'txdata_delay']].copy()
    pnf_txdata = pnf_df[pnf_df['type'] == 'pnf-txdata'][['timestamp', 'delta_us']].copy()
    
    plt.figure(figsize=(16, 6))
    if not vnf_txdata.empty:
        plt.plot(vnf_txdata['timestamp'], vnf_txdata['txdata_delay'], 'b-o', 
                label='VNF TxData Delay (µs)', linewidth=2, markersize=4, alpha=0.7)
    if not pnf_txdata.empty:
        plt.plot(pnf_txdata['timestamp'], pnf_txdata['delta_us'], 'r--s', 
                label='PNF TxData Delay (µs)', linewidth=2, markersize=4, alpha=0.7)
    
    plt.xlabel('Timestamp (s)', fontsize=12)
    plt.ylabel('Delay (µs)', fontsize=12)
    plt.title('TxData Delay Comparison: VNF vs PNF', fontsize=14, fontweight='bold')
    plt.axhline(y=0, color='k', linestyle='--', alpha=0.3)
    plt.legend(fontsize=11, loc='best')
    plt.grid(True, alpha=0.5)
    plt.tight_layout()
    plt.savefig(f'{prefix}_txdata_compare.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f'✓ 已繪製 TxData 比對圖: {prefix}_txdata_compare.png')

    # ========== 圖2: DL_TTI 延遲對比 ==========
    vnf_dltti = vnf_df[vnf_df['type'] == 'vnf-jitterdelay'][['timestamp', 'dl_delay']].copy()
    pnf_dltti = pnf_df[pnf_df['type'] == 'pnf-dltti'][['timestamp', 'delta_us']].copy()
    
    plt.figure(figsize=(16, 6))
    if not vnf_dltti.empty:
        plt.plot(vnf_dltti['timestamp'], vnf_dltti['dl_delay'], 'g-o', 
                label='VNF DL Delay (µs)', linewidth=2, markersize=4, alpha=0.7)
    if not pnf_dltti.empty:
        plt.plot(pnf_dltti['timestamp'], pnf_dltti['delta_us'], 'orange', marker='^', 
                linestyle='--', label='PNF DL_TTI Delay (µs)', linewidth=2, markersize=4, alpha=0.7)
    
    plt.xlabel('Timestamp (s)', fontsize=12)
    plt.ylabel('Delay (µs)', fontsize=12)
    plt.title('DL Delay Comparison: VNF vs PNF', fontsize=14, fontweight='bold')
    plt.axhline(y=0, color='k', linestyle='--', alpha=0.3)
    plt.legend(fontsize=11, loc='best')
    plt.grid(True, alpha=0.5)
    plt.tight_layout()
    plt.savefig(f'{prefix}_dltti_compare.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f'✓ 已繪製 DL_TTI 比對圖: {prefix}_dltti_compare.png')

    # ========== 圖3: VNF 延遲分布 ==========
    vnf_all = vnf_df[vnf_df['type'] == 'vnf-jitterdelay'].copy()
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle('VNF Delay Distribution (All)', fontsize=14, fontweight='bold')
    
    if not vnf_all.empty:
        axes[0, 0].plot(vnf_all['timestamp'], vnf_all['dl_delay'], 'b-', alpha=0.7)
        axes[0, 0].set_title('DL Delay')
        axes[0, 0].set_ylabel('Delay (µs)')
        axes[0, 0].grid(True, alpha=0.3)
        axes[0, 0].axhline(y=0, color='r', linestyle='--', alpha=0.3)
        
        axes[0, 1].plot(vnf_all['timestamp'], vnf_all['ul_delay'], 'g-', alpha=0.7)
        axes[0, 1].set_title('UL Delay')
        axes[0, 1].set_ylabel('Delay (µs)')
        axes[0, 1].grid(True, alpha=0.3)
        axes[0, 1].axhline(y=0, color='r', linestyle='--', alpha=0.3)
        
        axes[1, 0].plot(vnf_all['timestamp'], vnf_all['txdata_delay'], 'm-', alpha=0.7)
        axes[1, 0].set_title('TxData Delay')
        axes[1, 0].set_xlabel('Timestamp (s)')
        axes[1, 0].set_ylabel('Delay (µs)')
        axes[1, 0].grid(True, alpha=0.3)
        axes[1, 0].axhline(y=0, color='r', linestyle='--', alpha=0.3)
        
        axes[1, 1].plot(vnf_all['timestamp'], vnf_all['txdata_jitter'], 'c-', alpha=0.7)
        axes[1, 1].set_title('TxData Jitter')
        axes[1, 1].set_xlabel('Timestamp (s)')
        axes[1, 1].set_ylabel('Jitter (µs)')
        axes[1, 1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f'{prefix}_vnf_delays.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f'✓ 已繪製 VNF 延遲圖: {prefix}_vnf_delays.png')

    # ========== 圖4: PNF 延遲統計 ==========
    pnf_all_dltti = pnf_df[pnf_df['type'] == 'pnf-dltti'].copy()
    pnf_all_txdata = pnf_df[pnf_df['type'] == 'pnf-txdata'].copy()
    
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    fig.suptitle('PNF Timing Status (TOO LATE vs TOO EARLY)', fontsize=14, fontweight='bold')
    
    if not pnf_all_dltti.empty:
        dltti_late = pnf_all_dltti[pnf_all_dltti['timing_status'] == 'TOO LATE']
        dltti_early = pnf_all_dltti[pnf_all_dltti['timing_status'] == 'TOO EARLY']
        
        axes[0].hist([dltti_late['delta_us'].values, dltti_early['delta_us'].values], 
                     label=['TOO LATE', 'TOO EARLY'], bins=20, alpha=0.7)
        axes[0].set_title('DL_TTI Delta Distribution')
        axes[0].set_xlabel('Delta (µs)')
        axes[0].set_ylabel('Count')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
    
    if not pnf_all_txdata.empty:
        txdata_late = pnf_all_txdata[pnf_all_txdata['timing_status'] == 'TOO LATE']
        txdata_early = pnf_all_txdata[pnf_all_txdata['timing_status'] == 'TOO EARLY']
        
        axes[1].hist([txdata_late['delta_us'].values, txdata_early['delta_us'].values], 
                     label=['TOO LATE', 'TOO EARLY'], bins=20, alpha=0.7)
        axes[1].set_title('TX_Data Delta Distribution')
        axes[1].set_xlabel('Delta (µs)')
        axes[1].set_ylabel('Count')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f'{prefix}_pnf_timing_stats.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f'✓ 已繪製 PNF 時序統計圖: {prefix}_pnf_timing_stats.png')

def print_summary(vnf_df, pnf_df):
    """列印統計摘要"""
    print('\n' + '='*60)
    print('VNF LOG 統計摘要'.center(60))
    print('='*60)
    
    vnf_jitterdelay = vnf_df[vnf_df['type'] == 'vnf-jitterdelay']
    print(f'\n[VNF-JITTERDELAY] 記錄數: {len(vnf_jitterdelay)}')
    
    if not vnf_jitterdelay.empty:
        print(f'  - TxData Delay: 平均={vnf_jitterdelay["txdata_delay"].mean():.2f} µs, '
              f'最大={vnf_jitterdelay["txdata_delay"].max()} µs, '
              f'最小={vnf_jitterdelay["txdata_delay"].min()} µs')
        print(f'  - DL Delay:    平均={vnf_jitterdelay["dl_delay"].mean():.2f} µs, '
              f'最大={vnf_jitterdelay["dl_delay"].max()} µs, '
              f'最小={vnf_jitterdelay["dl_delay"].min()} µs')
        print(f'  - UL Delay:    平均={vnf_jitterdelay["ul_delay"].mean():.2f} µs, '
              f'最大={vnf_jitterdelay["ul_delay"].max()} µs, '
              f'最小={vnf_jitterdelay["ul_delay"].min()} µs')
    
    vnf_sync = vnf_df[vnf_df['type'] == 'vnf-sync']
    print(f'\n[VNF-SYNC] 同步調整記錄數: {len(vnf_sync)}')
    if not vnf_sync.empty:
        print(f'  - 調整值: 平均={vnf_sync["sync_adjustment"].mean():.2f} slots, '
              f'最大={vnf_sync["sync_adjustment"].max()} slots, '
              f'最小={vnf_sync["sync_adjustment"].min()} slots')

    print('\n' + '='*60)
    print('PNF LOG 統計摘要'.center(60))
    print('='*60)
    
    pnf_dltti = pnf_df[pnf_df['type'] == 'pnf-dltti']
    pnf_txdata = pnf_df[pnf_df['type'] == 'pnf-txdata']
    
    if not pnf_dltti.empty:
        dltti_late = pnf_dltti[pnf_dltti['timing_status'] == 'TOO LATE']
        dltti_early = pnf_dltti[pnf_dltti['timing_status'] == 'TOO EARLY']
        print(f'\n[PNF-DL_TTI] 記錄數: {len(pnf_dltti)}')
        print(f'  - TOO LATE 數: {len(dltti_late)}, '
              f'平均延遲={dltti_late["delta_us"].mean():.2f} µs' if not dltti_late.empty else '')
        print(f'  - TOO EARLY 數: {len(dltti_early)}, '
              f'平均提前={dltti_early["delta_us"].mean():.2f} µs' if not dltti_early.empty else '')
    
    if not pnf_txdata.empty:
        txdata_late = pnf_txdata[pnf_txdata['timing_status'] == 'TOO LATE']
        txdata_early = pnf_txdata[pnf_txdata['timing_status'] == 'TOO EARLY']
        print(f'\n[PNF-TX_DATA] 記錄數: {len(pnf_txdata)}')
        print(f'  - TOO LATE 數: {len(txdata_late)}, '
              f'平均延遲={txdata_late["delta_us"].mean():.2f} µs' if not txdata_late.empty else '')
        print(f'  - TOO EARLY 數: {len(txdata_early)}, '
              f'平均提前={txdata_early["delta_us"].mean():.2f} µs' if not txdata_early.empty else '')
    
    print('\n' + '='*60 + '\n')

def main():
    if len(sys.argv) < 3:
        print("用法: python vnf_pnf_parser_v2.py <vnf_log> <pnf_log> [output_prefix]")
        sys.exit(1)
    
    vnf_log = sys.argv[1]
    pnf_log = sys.argv[2]
    prefix = sys.argv[3] if len(sys.argv) > 3 else 'vnf_pnf'

    if not Path(vnf_log).exists() or not Path(pnf_log).exists():
        print(f"❌ 找不到指定日誌檔案")
        sys.exit(1)

    print(f"📖 正在解析 VNF LOG: {vnf_log}")
    vnf = VNFPNFLogParser(vnf_log).parse()
    
    print(f"📖 正在解析 PNF LOG: {pnf_log}")
    pnf = VNFPNFLogParser(pnf_log).parse()

    # 儲存 CSV
    vnf.to_csv(f'{prefix}_vnf.csv', index=False)
    pnf.to_csv(f'{prefix}_pnf.csv', index=False)
    print(f'✓ 已儲存解析結果: {prefix}_vnf.csv, {prefix}_pnf.csv')

    # 列印統計摘要
    print_summary(vnf, pnf)

    # 繪製圖表
    plot_compare_vnf_pnf(vnf, pnf, prefix)
    
    print(f'\n✅ 分析完成！結果已儲存至 {prefix}_*.png 和 {prefix}_*.csv')

if __name__ == '__main__':
    main()

