"""
Best Path Analysis: Identify optimal racing paths based on performance
"""
import numpy as np
import matplotlib.pyplot as plt
import os
import json


def analyze_best_path(results, track, output_dir='.'):
    """
    Analyze and identify the best racing path based on performance metrics.
    
    Args:
        results: Simulation results dictionary
        track: Track object
        output_dir: Output directory for best path files
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Find best performing car (lowest lap time, fewest collisions)
    best_car_id = None
    best_score = float('inf')
    
    for car_id, lap_times in results['lap_times'].items():
        if lap_times:
            avg_lap_time = np.mean(lap_times)
            # Count collisions for this car
            car_collisions = sum(1 for c in results['collisions'] 
                               if c['car_id1'] == car_id or c['car_id2'] == car_id)
            # Score: lower is better (lap time + collision penalty)
            score = avg_lap_time + car_collisions * 5.0  # 5 second penalty per collision
            
            if score < best_score:
                best_score = score
                best_car_id = car_id
    
    if best_car_id is None:
        print("Warning: No car completed laps, cannot determine best path")
        return
    
    # Get best car's trajectory
    best_trajectory = results['trajectories'][best_car_id]
    
    # Extract path data
    path_x = [p['x'] for p in best_trajectory]
    path_y = [p['y'] for p in best_trajectory]
    path_s = [p['s_position'] for p in best_trajectory]
    path_velocity = [p['velocity'] for p in best_trajectory]
    path_lap = [p['lap'] for p in best_trajectory]
    
    # Save best path data to JSON
    best_path_data = {
        'car_id': best_car_id,
        'avg_lap_time': np.mean(results['lap_times'][best_car_id]),
        'total_laps': results['final_laps'][best_car_id],
        'collisions': sum(1 for c in results['collisions'] 
                         if c['car_id1'] == best_car_id or c['car_id2'] == best_car_id),
        'average_speed': results['average_speeds'][best_car_id],
        'path_points': len(best_trajectory),
        'strategy': 'unknown'  # Would need to track this
    }
    
    with open(os.path.join(output_dir, 'best_path_summary.json'), 'w') as f:
        json.dump(best_path_data, f, indent=2)
    
    # Save best path trajectory to CSV
    import csv
    with open(os.path.join(output_dir, 'best_path_trajectory.csv'), 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['x', 'y', 's_position', 'velocity', 'lap'])
        for i in range(len(path_x)):
            writer.writerow([path_x[i], path_y[i], path_s[i], path_velocity[i], path_lap[i]])
    
    # Create visualization of best path
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    # 1. Best path on track
    ax1 = axes[0, 0]
    # Draw track
    inner_x, inner_y, outer_x, outer_y = track.get_track_boundaries()
    ax1.plot(inner_x, inner_y, 'k-', linewidth=1, alpha=0.3)
    ax1.plot(outer_x, outer_y, 'k-', linewidth=1, alpha=0.3)
    ax1.plot(track.centerline_x, track.centerline_y, 'k--', linewidth=1, alpha=0.2)
    
    # Draw best path with color coding by velocity
    scatter = ax1.scatter(path_x, path_y, c=path_velocity, cmap='viridis', 
                         s=10, alpha=0.6, edgecolors='none')
    ax1.set_xlabel('X Position (m)')
    ax1.set_ylabel('Y Position (m)')
    ax1.set_title(f'Best Path - Car {best_car_id} (Color = Velocity)')
    ax1.set_aspect('equal')
    ax1.grid(True, alpha=0.3)
    plt.colorbar(scatter, ax=ax1, label='Velocity (m/s)')
    
    # 2. Speed profile along path
    ax2 = axes[0, 1]
    ax2.plot(path_s, path_velocity, 'b-', linewidth=2, alpha=0.7)
    ax2.set_xlabel('Arc-Length Position (m)')
    ax2.set_ylabel('Velocity (m/s)')
    ax2.set_title('Speed Profile Along Best Path')
    ax2.grid(True, alpha=0.3)
    
    # 3. Path efficiency (speed vs position)
    ax3 = axes[1, 0]
    # Group by lap
    for lap in range(max(path_lap) + 1):
        lap_indices = [i for i, l in enumerate(path_lap) if l == lap]
        if lap_indices:
            lap_s = [path_s[i] for i in lap_indices]
            lap_v = [path_velocity[i] for i in lap_indices]
            ax3.plot(lap_s, lap_v, label=f'Lap {lap}', linewidth=2, alpha=0.7)
    ax3.set_xlabel('Arc-Length Position (m)')
    ax3.set_ylabel('Velocity (m/s)')
    ax3.set_title('Speed Profile by Lap')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # 4. Optimal zones (where car maintains high speed)
    ax4 = axes[1, 1]
    # Identify high-speed zones (velocity > 80% of max)
    max_velocity = max(path_velocity) if path_velocity else 0
    threshold = max_velocity * 0.8
    high_speed_zones = [(path_s[i], path_velocity[i]) for i in range(len(path_s)) 
                       if path_velocity[i] > threshold]
    
    if high_speed_zones:
        zones_s, zones_v = zip(*high_speed_zones)
        ax4.scatter(zones_s, zones_v, c='green', s=50, alpha=0.6, label='High Speed Zones')
    
    ax4.plot(path_s, path_velocity, 'b-', linewidth=1, alpha=0.3, label='Full Path')
    ax4.axhline(y=threshold, color='r', linestyle='--', label=f'Threshold ({threshold:.1f} m/s)')
    ax4.set_xlabel('Arc-Length Position (m)')
    ax4.set_ylabel('Velocity (m/s)')
    ax4.set_title('Optimal Speed Zones')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'best_path_analysis.png'), dpi=150)
    plt.close()
    
    print(f"Best performing car: Car {best_car_id}")
    print(f"  Average lap time: {best_path_data['avg_lap_time']:.2f}s")
    print(f"  Average speed: {best_path_data['average_speed']:.2f} m/s")
    print(f"  Collisions: {best_path_data['collisions']}")


