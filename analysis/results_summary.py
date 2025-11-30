"""
Results Summary: Save comprehensive simulation results to files
"""
import json
import os
from datetime import datetime


def save_results_summary(results, config, speed_multiplier, output_dir='.'):
    """
    Save comprehensive results summary to JSON and text files.
    
    Args:
        results: Simulation results dictionary
        config: Configuration dictionary
        speed_multiplier: Speed multiplier used
        output_dir: Output directory for results
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Prepare summary data
    summary = {
        'simulation_info': {
            'timestamp': datetime.now().isoformat(),
            'speed_multiplier': speed_multiplier,
            'num_cars': config['num_cars'],
            'target_laps': config['simulation']['laps'],
            'simulation_time': results['simulation_time']
        },
        'performance_metrics': {
            'total_collisions': results['total_collisions'],
            'near_misses': results['near_misses'],
            'num_eliminated': results.get('num_eliminated', 0),
            'risk_index': results['total_collisions'] + results['near_misses'] * 0.1
        },
        'lap_times': results['lap_times'],
        'average_speeds': results['average_speeds'],
        'final_laps': results['final_laps'],
        'eliminated_cars': results.get('eliminated_cars', {}),
        'collision_locations': [
            {'x': c['x'], 'y': c['y'], 'lap': c['lap'], 'timestamp': c['timestamp']}
            for c in results['collisions']
        ]
    }
    
    # Calculate aggregate statistics
    all_lap_times = []
    for lap_times in results['lap_times'].values():
        all_lap_times.extend(lap_times)
    
    if all_lap_times:
        summary['aggregate_stats'] = {
            'avg_lap_time': sum(all_lap_times) / len(all_lap_times),
            'min_lap_time': min(all_lap_times),
            'max_lap_time': max(all_lap_times),
            'total_laps_completed': len(all_lap_times)
        }
    else:
        summary['aggregate_stats'] = {
            'avg_lap_time': 0.0,
            'min_lap_time': 0.0,
            'max_lap_time': 0.0,
            'total_laps_completed': 0
        }
    
    avg_speeds = list(results['average_speeds'].values())
    if avg_speeds:
        summary['aggregate_stats']['avg_speed_all_cars'] = sum(avg_speeds) / len(avg_speeds)
        summary['aggregate_stats']['min_speed'] = min(avg_speeds)
        summary['aggregate_stats']['max_speed'] = max(avg_speeds)
    
    # Save JSON
    with open(os.path.join(output_dir, 'results_summary.json'), 'w') as f:
        json.dump(summary, f, indent=2)
    
    # Save human-readable text summary
    with open(os.path.join(output_dir, 'results_summary.txt'), 'w') as f:
        f.write("="*70 + "\n")
        f.write("SIMULATION RESULTS SUMMARY\n")
        f.write("="*70 + "\n\n")
        
        f.write("Simulation Information:\n")
        f.write(f"  Timestamp: {summary['simulation_info']['timestamp']}\n")
        f.write(f"  Speed Multiplier: {speed_multiplier}\n")
        f.write(f"  Number of Cars: {config['num_cars']}\n")
        f.write(f"  Target Laps: {config['simulation']['laps']}\n")
        f.write(f"  Simulation Time: {results['simulation_time']:.2f}s\n\n")
        
        f.write("Performance Metrics:\n")
        f.write(f"  Total Collisions: {results['total_collisions']}\n")
        f.write(f"  Near Misses: {results['near_misses']}\n")
        f.write(f"  Eliminated Cars: {results.get('num_eliminated', 0)}\n")
        f.write(f"  Risk Index: {summary['performance_metrics']['risk_index']:.2f}\n\n")
        
        if summary['aggregate_stats']['total_laps_completed'] > 0:
            f.write("Aggregate Statistics:\n")
            f.write(f"  Average Lap Time: {summary['aggregate_stats']['avg_lap_time']:.2f}s\n")
            f.write(f"  Min Lap Time: {summary['aggregate_stats']['min_lap_time']:.2f}s\n")
            f.write(f"  Max Lap Time: {summary['aggregate_stats']['max_lap_time']:.2f}s\n")
            f.write(f"  Average Speed (All Cars): {summary['aggregate_stats'].get('avg_speed_all_cars', 0):.2f} m/s\n")
            f.write(f"  Total Laps Completed: {summary['aggregate_stats']['total_laps_completed']}\n\n")
        
        f.write("Per-Car Lap Times:\n")
        for car_id, lap_times in results['lap_times'].items():
            if lap_times:
                avg = sum(lap_times) / len(lap_times)
                f.write(f"  Car {car_id:2d}: {lap_times} | Avg: {avg:.2f}s\n")
            else:
                f.write(f"  Car {car_id:2d}: No completed laps\n")
        
        f.write("\nPer-Car Average Speeds:\n")
        for car_id, avg_speed in results['average_speeds'].items():
            f.write(f"  Car {car_id:2d}: {avg_speed:.2f} m/s ({avg_speed*3.6:.2f} km/h)\n")
        
        if results.get('eliminated_cars'):
            f.write("\nEliminated Cars:\n")
            for car_id, elim_info in results['eliminated_cars'].items():
                f.write(f"  Car {car_id:2d}: Eliminated at {elim_info['elimination_time']:.2f}s\n")
                f.write(f"    Reason: {elim_info['elimination_reason']}\n")
                f.write(f"    Collisions: {elim_info['collision_count']}\n")
        
        f.write("\n" + "="*70 + "\n")

