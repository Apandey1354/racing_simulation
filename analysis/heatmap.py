"""
Analysis: Collision Heatmap Visualization
"""
import numpy as np
import matplotlib.pyplot as plt
import os


def plot_collision_heatmap(results, track, output_dir='.', resolution=100):
    """
    Create 2D collision heatmap on track.
    
    Args:
        results: Simulation results dictionary
        track: Track object
        output_dir: Output directory for plots
        resolution: Grid resolution for heatmap
    """
    os.makedirs(output_dir, exist_ok=True)
    
    if not results['collisions']:
        print("No collisions to plot in heatmap")
        return
    
    # Create figure with track overlay
    fig, ax = plt.subplots(figsize=(14, 10))
    
    # Plot track boundaries
    inner_x, inner_y, outer_x, outer_y = track.get_track_boundaries()
    ax.plot(inner_x, inner_y, 'k-', linewidth=2, label='Track Boundary')
    ax.plot(outer_x, outer_y, 'k-', linewidth=2)
    ax.plot(track.centerline_x, track.centerline_y, 'k--', linewidth=1, alpha=0.5, label='Centerline')
    
    # Extract collision positions
    collision_x = [c['x'] for c in results['collisions']]
    collision_y = [c['y'] for c in results['collisions']]
    
    # Create 2D histogram
    x_min, x_max = min(track.centerline_x) - track.width, max(track.centerline_x) + track.width
    y_min, y_max = min(track.centerline_y) - track.width, max(track.centerline_y) + track.width
    
    x_bins = np.linspace(x_min, x_max, resolution)
    y_bins = np.linspace(y_min, y_max, resolution)
    
    H, x_edges, y_edges = np.histogram2d(collision_x, collision_y, bins=[x_bins, y_bins])
    
    # Plot heatmap
    X, Y = np.meshgrid(x_edges[:-1], y_edges[:-1])
    im = ax.pcolormesh(X, Y, H.T, cmap='hot', alpha=0.7, shading='auto')
    
    # Add colorbar
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('Collision Density', rotation=270, labelpad=20)
    
    # Plot individual collision points
    ax.scatter(collision_x, collision_y, c='red', s=30, alpha=0.6, 
              edgecolors='black', linewidths=0.5, label='Collision Events', zorder=5)
    
    # Plot car trajectories (optional, can be slow)
    # for car_id, trajectory in list(results['trajectories'].items())[:3]:  # First 3 cars only
    #     traj_x = [p['x'] for p in trajectory]
    #     traj_y = [p['y'] for p in trajectory]
    #     ax.plot(traj_x, traj_y, alpha=0.1, linewidth=0.5)
    
    ax.set_xlabel('X Position (m)')
    ax.set_ylabel('Y Position (m)')
    ax.set_title('Collision Heatmap on Track')
    ax.set_aspect('equal')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'collision_heatmap.png'), dpi=150)
    plt.close()
    
    print("Generated collision heatmap: collision_heatmap.png")

