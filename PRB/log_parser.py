#!/usr/bin/env python3
"""
Log Parser for UE Size Analysis (Advanced v2)
- Auto-extract throughput from filename
- English only text to avoid font issues
- Moving average + original data overlay for noisy data
- Hide UE ID from filename and chart title
"""

import sys
import re
import argparse
from collections import defaultdict
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

def parse_log_file(filepath):
    """
    Parse log file and extract timestamp, UE ID, and Size
    
    Returns:
        dict: {ue_id: [(timestamp, frame, slot, size), ...]}
    """
    ue_data = defaultdict(list)
    
    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                # Regex pattern: [timestamp] frame=X slot=Y UE xxxx: Size Z
                match = re.match(
                    r'\[(\d+\.\d+)\]\s+frame=(\d+)\s+slot=(\d+)\s+UE\s+([a-fA-F0-9]+):\s+Size\s+(\d+)',
                    line
                )
                
                if match:
                    timestamp = float(match.group(1))
                    frame = int(match.group(2))
                    slot = int(match.group(3))
                    ue_id = match.group(4)
                    size = int(match.group(5))
                    
                    ue_data[ue_id].append({
                        'timestamp': timestamp,
                        'frame': frame,
                        'slot': slot,
                        'size': size
                    })
    
    except FileNotFoundError:
        print(f"ERROR: File not found {filepath}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Problem reading file: {e}")
        sys.exit(1)
    
    if not ue_data:
        print("ERROR: No matching log format found")
        sys.exit(1)
    
    return ue_data

def extract_throughput_from_filename(log_file):
    """
    Extract throughput from filename pattern like 'measure-PRB-500M.txt'
    
    Returns:
        float or None: throughput value in Mbps
    """
    filename = Path(log_file).stem
    
    # Try to match patterns like: 500M, 1000M, 125.5M, etc.
    match = re.search(r'-(\d+(?:\.\d+)?)(M|Mbps)?(?:\.txt)?$', filename)
    if match:
        return float(match.group(1))
    
    return None

def get_ues_to_plot(ue_data, top_only=True, all_ues=False):
    """
    Determine which UEs to plot based on parameters
    
    Args:
        ue_data: All UE data
        top_only: Only output UE with most data (default)
        all_ues: Output all UEs (overrides top_only)
    
    Returns:
        list: List of UE IDs to plot
    """
    if all_ues:
        ues_to_plot = sorted(ue_data.keys())
        print(f"MODE: Output all UEs ({len(ues_to_plot)})")
    elif top_only:
        # Find UE with most records
        top_ue = max(ue_data.items(), key=lambda x: len(x[1]))[0]
        ues_to_plot = [top_ue]
        max_count = len(ue_data[top_ue])
        print(f"MODE: Output UE with most data")
        print(f"Selected: UE {top_ue} (Records: {max_count})")
    else:
        ues_to_plot = sorted(ue_data.keys())
        print(f"MODE: Output all UEs ({len(ues_to_plot)})")
    
    return ues_to_plot

def generate_output_filename(log_file, throughput_override=None, output_prefix=None):
    """
    Generate output filename with auto-extracted or provided throughput
    
    Args:
        log_file: Path to log file
        throughput_override: Explicitly provided throughput (overrides auto-extract)
        output_prefix: Custom prefix
    
    Returns:
        str: Filename prefix (without extension)
    """
    if output_prefix:
        return output_prefix
    
    base_name = Path(log_file).stem
    
    # Auto-extract throughput from filename if not overridden
    throughput = throughput_override if throughput_override is not None else extract_throughput_from_filename(log_file)
    
    if throughput is not None:
        # Format throughput nicely
        if throughput == int(throughput):
            tp_str = f"{int(throughput)}"
        else:
            tp_str = f"{throughput:.1f}".rstrip('0').rstrip('.')
        
        return f"{base_name}_tp{tp_str}"
    else:
        return base_name

def calculate_moving_average(data, window=5):
    """
    Calculate moving average for smoothing noisy data
    
    Args:
        data: List of values
        window: Window size for moving average
    
    Returns:
        np.array: Smoothed data
    """
    if len(data) < window:
        return np.array(data)
    
    return np.convolve(data, np.ones(window)/window, mode='valid')

def plot_single_ue(ue_id, data, throughput=None, filename_prefix=None, separate=False):
    """
    Plot chart for single UE with moving average overlay
    
    Returns:
        str: Saved filename
    """
    # Suppress matplotlib font warnings
    import warnings
    warnings.filterwarnings('ignore', category=UserWarning)
    
    fig, ax = plt.subplots(figsize=(14, 7))
    
    # Prepare data
    timestamps = [d['timestamp'] for d in data]
    sizes = [d['size'] for d in data]
    
    # Normalize timestamps (start from 0)
    min_timestamp = min(timestamps)
    relative_times = np.array([t - min_timestamp for t in timestamps])
    sizes = np.array(sizes)
    
    # Calculate moving average for smoothing (window = 5)
    window_size = 10
    if len(sizes) >= window_size:
        smoothed_sizes = calculate_moving_average(sizes, window=window_size)
        smoothed_times = relative_times[window_size-1:]
    else:
        smoothed_sizes = sizes
        smoothed_times = relative_times
    
    # Plot original data (light, transparent)
    ax.scatter(relative_times, sizes, alpha=0.3, s=20, color='#90CAF9', label='Raw Data', zorder=1)
    
    # Plot moving average trend line
    ax.plot(smoothed_times, smoothed_sizes, linewidth=2.5, color='#1976D2', label='Moving Average (5-point)', zorder=2)
    
    # Set labels (English only)
    ax.set_xlabel('Time (seconds)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Size (bytes)', fontsize=12, fontweight='bold')
    
    # Set title (English only, no UE ID)
    if throughput is not None:
        title = f'Size Analysis - Throughput: {throughput} Mbps'
    else:
        title = 'Size Analysis'
    
    ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
    ax.grid(True, alpha=0.3, linestyle='--', zorder=0)
    ax.legend(loc='upper right', fontsize=10)
    
    # Add statistics box (English only)
    mean_size = np.mean(sizes)
    max_size = np.max(sizes)
    min_size = np.min(sizes)
    count = len(sizes)
    duration = max(timestamps) - min(timestamps)
    std_size = np.std(sizes)
    
    stats_text = (f'Statistics\n'
                  f'─────────────\n'
                  f'Samples: {count}\n'
                  f'Mean: {mean_size:.2f} B\n'
                  f'Std Dev: {std_size:.2f} B\n'
                  f'Max: {max_size} B\n'
                  f'Min: {min_size} B\n'
                  f'Duration: {duration:.3f} s')
    
    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
            fontsize=9, verticalalignment='top', horizontalalignment='left',
            bbox=dict(boxstyle='round', facecolor='#FFFDE7', alpha=0.85, pad=0.8),
            family='monospace')
    
    plt.tight_layout()
    
    # Generate filename (no UE ID in filename)
    if filename_prefix:
        output_file = f"{filename_prefix}.png"
    else:
        output_file = 'size_analysis.png'
    
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    return output_file

def plot_all_ues_combined(ue_data, ues_to_plot, throughput=None, filename_prefix=None):
    """
    Plot multiple UEs in subplots with moving average overlay
    """
    # Suppress warnings
    import warnings
    warnings.filterwarnings('ignore', category=UserWarning)
    
    num_ues = len(ues_to_plot)
    
    cols = 3
    rows = (num_ues + cols - 1) // cols
    
    fig, axes = plt.subplots(rows, cols, figsize=(16, 5*rows))
    
    # Ensure axes is 2D array
    if num_ues == 1:
        axes = np.array([[axes]])
    elif rows == 1:
        axes = axes.reshape(1, -1)
    elif cols == 1:
        axes = axes.reshape(-1, 1)
    
    # Set main title (English only)
    if throughput is not None:
        fig.suptitle(f'Size Analysis - Throughput: {throughput} Mbps', 
                    fontsize=16, fontweight='bold')
    else:
        fig.suptitle('Size Analysis', fontsize=16, fontweight='bold')
    
    for idx, ue_id in enumerate(ues_to_plot):
        data = ue_data[ue_id]
        row = idx // cols
        col = idx % cols
        ax = axes[row, col]
        
        # Prepare data
        timestamps = [d['timestamp'] for d in data]
        sizes = np.array([d['size'] for d in data])
        
        # Normalize timestamps
        min_timestamp = min(timestamps)
        relative_times = np.array([t - min_timestamp for t in timestamps])
        
        # Calculate moving average
        window_size = 5
        if len(sizes) >= window_size:
            smoothed_sizes = calculate_moving_average(sizes, window=window_size)
            smoothed_times = relative_times[window_size-1:]
        else:
            smoothed_sizes = sizes
            smoothed_times = relative_times
        
        # Plot
        ax.scatter(relative_times, sizes, alpha=0.3, s=15, color='#90CAF9', zorder=1)
        ax.plot(smoothed_times, smoothed_sizes, linewidth=2, color='#1976D2', zorder=2)
        
        # Labels (English only)
        ax.set_xlabel('Time (s)', fontsize=9)
        ax.set_ylabel('Size (B)', fontsize=9)
        ax.set_title(f'UE {ue_id}', fontsize=11, fontweight='bold')
        ax.grid(True, alpha=0.3, linestyle='--', zorder=0)
        
        # Small stats (English only)
        mean_size = np.mean(sizes)
        max_size = np.max(sizes)
        min_size = np.min(sizes)
        count = len(sizes)
        
        stats_text = f'N: {count}\nMean: {mean_size:.1f}\nMax: {max_size}\nMin: {min_size}'
        ax.text(0.98, 0.97, stats_text, transform=ax.transAxes, 
                fontsize=8, verticalalignment='top', horizontalalignment='right',
                bbox=dict(boxstyle='round', facecolor='#FFFDE7', alpha=0.85, pad=0.5),
                family='monospace')
    
    # Hide extra subplots
    for idx in range(num_ues, rows * cols):
        row = idx // cols
        col = idx % cols
        axes[row, col].set_visible(False)
    
    plt.tight_layout()
    
    # Save
    if filename_prefix:
        output_file = f"{filename_prefix}.png"
    else:
        output_file = 'size_analysis.png'
    
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    return output_file

def print_summary(ue_data, ues_to_plot):
    """
    Print UE data summary
    """
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    for ue_id in ues_to_plot:
        data = ue_data[ue_id]
        sizes = [d['size'] for d in data]
        timestamps = [d['timestamp'] for d in data]
        
        print(f"\nUE {ue_id}:")
        print(f"   Samples: {len(data)}")
        print(f"   Mean Size: {np.mean(sizes):.2f} bytes")
        print(f"   Max Size: {np.max(sizes)} bytes")
        print(f"   Min Size: {np.min(sizes)} bytes")
        print(f"   Std Dev: {np.std(sizes):.2f} bytes")
        print(f"   Duration: {max(timestamps) - min(timestamps):.6f} sec")

def main():
    """
    Main program
    """
    parser = argparse.ArgumentParser(
        description='Log Parser for UE Size Analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Usage Examples:
  python3 log_parser.py ./measure-PRB-500M.txt
  python3 log_parser.py ./measure-PRB-500M.txt --all-ues
  python3 log_parser.py ./measure-PRB.txt -t 125.5
  python3 log_parser.py ./measure-PRB.txt --separate
  python3 log_parser.py ./measure-PRB.txt -o custom_name

Automatic throughput extraction:
  measure-PRB-500M.txt  -> 500 Mbps
  test-1000M.txt        -> 1000 Mbps
  exp-125.5M.txt        -> 125.5 Mbps

Options:
  --top-only      Output only UE with most data (default)
  --all-ues       Output all UEs
  -t, --throughput  Override auto-detected throughput (Mbps)
  --separate      Output separate PNG for each UE
  -o, --output    Custom output filename (without extension)
        '''
    )
    
    parser.add_argument('log_file', help='Path to log file')
    parser.add_argument('--top-only', action='store_true', default=True,
                       help='Output only UE with most data (default)')
    parser.add_argument('--all-ues', action='store_true',
                       help='Output all UEs')
    parser.add_argument('-t', '--throughput', type=float, default=None,
                       help='Override throughput value (Mbps)')
    parser.add_argument('--separate', action='store_true',
                       help='Output separate PNG for each UE')
    parser.add_argument('-o', '--output', type=str, default=None,
                       help='Custom output filename prefix')
    
    args = parser.parse_args()
    
    print(f"\n{'='*70}")
    print("Log Parser for UE Size Analysis v2")
    print(f"{'='*70}")
    print(f"Log file: {args.log_file}")
    
    # Parse log file
    print(f"\nParsing log file...")
    ue_data = parse_log_file(args.log_file)
    print(f"Found {len(ue_data)} UE(s)")
    
    # Determine which UEs to plot
    if args.all_ues:
        args.top_only = False
    
    ues_to_plot = get_ues_to_plot(ue_data, top_only=args.top_only, all_ues=args.all_ues)
    
    # Auto-extract throughput if not provided
    throughput = args.throughput if args.throughput is not None else extract_throughput_from_filename(args.log_file)
    
    if throughput is not None:
        print(f"Throughput: {throughput} Mbps (from {'command' if args.throughput else 'filename'})")
    
    # Print summary
    print_summary(ue_data, ues_to_plot)
    
    # Generate output filename
    filename_prefix = generate_output_filename(args.log_file, args.throughput, args.output)
    
    # Plot
    print(f"\nGenerating chart...")
    
    if args.separate or len(ues_to_plot) == 1:
        # Single UE or separate mode
        output_files = []
        for ue_id in ues_to_plot:
            output_file = plot_single_ue(
                ue_id, 
                ue_data[ue_id],
                throughput=throughput,
                filename_prefix=filename_prefix,
                separate=True
            )
            output_files.append(output_file)
        
        print(f"\nChart saved:")
        for f in output_files:
            print(f"   {f}")
    else:
        # Multiple UEs combined
        output_file = plot_all_ues_combined(
            ue_data,
            ues_to_plot,
            throughput=throughput,
            filename_prefix=filename_prefix
        )
        print(f"\nChart saved: {output_file}")
    
    print(f"\n{'='*70}\n")

if __name__ == '__main__':
    main()
