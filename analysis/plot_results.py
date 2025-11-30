"""
Analysis: Plot Results (Lap Times, Speed Traces, Collisions)
"""
import numpy as np
import matplotlib.pyplot as plt
import os


def plot_results(results, config, output_dir='.'):
    """
    Generate various result plots.
    
    Args:
        results: Simulation results dictionary
        config: Configuration dictionary
        output_dir: Output directory for plots
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Lap Times Plot
    fig, ax = plt.subplots(figsize=(12, 6))
    car_ids = []
    lap_times_list = []
    
    for car_id, lap_times in results['lap_times'].items():
        if lap_times:
            car_ids.append(car_id)
            lap_times_list.append(lap_times)
    
    if lap_times_list:
        ax.boxplot(lap_times_list, labels=[f'Car {cid}' for cid in car_ids])
        ax.set_xlabel('Car ID')
        ax.set_ylabel('Lap Time (seconds)')
        ax.set_title('Lap Time Distribution by Car')
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'lap_times.png'), dpi=150)
        plt.close()
    
    # 2. Speed Traces
    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    
    # Plot individual speed traces
    ax1 = axes[0]
    for car_id, trajectory in results['trajectories'].items():
        if trajectory:
            times = np.arange(len(trajectory)) * config['simulation']['dt']
            speeds = [p['velocity'] for p in trajectory]
            ax1.plot(times, speeds, label=f'Car {car_id}', alpha=0.7, linewidth=1.5)
    
    ax1.set_xlabel('Time (seconds)')
    ax1.set_ylabel('Velocity (m/s)')
    ax1.set_title('Speed Traces for All Cars')
    ax1.legend(ncol=3, fontsize=8)
    ax1.grid(True, alpha=0.3)
    
    # Plot average speed over time
    ax2 = axes[1]
    if results['trajectories']:
        max_len = max(len(traj) for traj in results['trajectories'].values())
        times = np.arange(max_len) * config['simulation']['dt']
        
        # Compute average speed at each time step
        avg_speeds = []
        for t_idx in range(max_len):
            speeds_at_t = []
            for trajectory in results['trajectories'].values():
                if t_idx < len(trajectory):
                    speeds_at_t.append(trajectory[t_idx]['velocity'])
            if speeds_at_t:
                avg_speeds.append(np.mean(speeds_at_t))
            else:
                avg_speeds.append(0)
        
        ax2.plot(times[:len(avg_speeds)], avg_speeds, 'k-', linewidth=2, label='Average Speed')
        ax2.set_xlabel('Time (seconds)')
        ax2.set_ylabel('Average Velocity (m/s)')
        ax2.set_title('Average Speed Over Time')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'speed_traces.png'), dpi=150)
    plt.close()
    
    # 3. Collisions per Run
    if results['collisions']:
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Count collisions per car
        collision_counts = {}
        for collision in results['collisions']:
            car_id1 = collision['car_id1']
            car_id2 = collision['car_id2']
            collision_counts[car_id1] = collision_counts.get(car_id1, 0) + 1
            collision_counts[car_id2] = collision_counts.get(car_id2, 0) + 1
        
        car_ids = sorted(collision_counts.keys())
        counts = [collision_counts[cid] for cid in car_ids]
        
        ax.bar([f'Car {cid}' for cid in car_ids], counts, color='red', alpha=0.7)
        ax.set_xlabel('Car ID')
        ax.set_ylabel('Number of Collisions')
        ax.set_title('Collisions per Car')
        ax.grid(True, alpha=0.3, axis='y')
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'collisions_per_car.png'), dpi=150)
        plt.close()
    
    # 4. Safety vs Speed Scatter Plot
    fig, ax = plt.subplots(figsize=(10, 6))
    
    car_ids = list(results['average_speeds'].keys())
    avg_speeds = [results['average_speeds'][cid] for cid in car_ids]
    
    # Count collisions per car
    collision_counts = {cid: 0 for cid in car_ids}
    for collision in results['collisions']:
        collision_counts[collision['car_id1']] += 1
        collision_counts[collision['car_id2']] += 1
    
    collision_nums = [collision_counts[cid] for cid in car_ids]
    
    scatter = ax.scatter(avg_speeds, collision_nums, s=100, alpha=0.6, c=car_ids, cmap='viridis')
    ax.set_xlabel('Average Speed (m/s)')
    ax.set_ylabel('Number of Collisions')
    ax.set_title('Safety vs Speed Tradeoff')
    ax.grid(True, alpha=0.3)
    
    # Add colorbar
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('Car ID')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'safety_vs_speed.png'), dpi=150)
    plt.close()
    
    print("Generated plots: lap_times.png, speed_traces.png, collisions_per_car.png, safety_vs_speed.png")

