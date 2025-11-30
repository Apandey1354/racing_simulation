"""
Phase 2 Script: Entry Point for Multi-Car Racing Simulation
"""
import argparse
import yaml
import os
import sys

from simulation.simulation import RacingSimulation
from simulation.simulation_types import SimulationType
from simulation.discrete_event import DiscreteEventSimulation
from simulation.monte_carlo import MonteCarloSimulation
from simulation.markov_chain import MarkovChainSimulation
from analysis.plot_results import plot_results
from analysis.heatmap import plot_collision_heatmap
from analysis.best_path import analyze_best_path
from analysis.results_summary import save_results_summary


def get_project_root():
    """Get the project root directory (where this script is located)."""
    return os.path.dirname(os.path.abspath(__file__))


def load_config(config_path='config/parameters.yaml'):
    """Load configuration from YAML file."""
    # If path is relative, make it relative to project root
    if not os.path.isabs(config_path):
        project_root = get_project_root()
        config_path = os.path.join(project_root, config_path)
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}\n"
            f"Make sure you're running from the racing_simulation directory or provide an absolute path."
        )
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config


def print_summary(results):
    """Print simulation summary metrics."""
    print("\n" + "="*60)
    print("SIMULATION SUMMARY")
    print("="*60)
    
    print(f"\nTotal Collisions: {results['total_collisions']}")
    print(f"Near Misses: {results['near_misses']}")
    print(f"Eliminated Cars: {results.get('num_eliminated', 0)}")
    print(f"Simulation Time: {results['simulation_time']:.2f}s")
    
    # Show elimination details
    if results.get('eliminated_cars'):
        print("\n" + "-"*60)
        print("ELIMINATED CARS")
        print("-"*60)
        for car_id, elim_info in results['eliminated_cars'].items():
            print(f"Car {car_id:2d}: Eliminated at {elim_info['elimination_time']:.2f}s")
            print(f"         Reason: {elim_info['elimination_reason']}")
            print(f"         Collisions: {elim_info['collision_count']}, "
                  f"Total Severity: {elim_info['total_severity']:.1f}")
    
    print("\n" + "-"*60)
    print("LAP TIMES (seconds)")
    print("-"*60)
    for car_id, lap_times in results['lap_times'].items():
        if lap_times:
            avg_lap = sum(lap_times) / len(lap_times)
            print(f"Car {car_id:2d}: {lap_times} | Avg: {avg_lap:.2f}s")
        else:
            print(f"Car {car_id:2d}: No completed laps")
    
    print("\n" + "-"*60)
    print("AVERAGE SPEEDS (m/s)")
    print("-"*60)
    for car_id, avg_speed in results['average_speeds'].items():
        print(f"Car {car_id:2d}: {avg_speed:.2f} m/s ({avg_speed*3.6:.2f} km/h)")
    
    print("\n" + "-"*60)
    print("FINAL LAP COUNTS")
    print("-"*60)
    for car_id, lap_count in results['final_laps'].items():
        print(f"Car {car_id:2d}: {lap_count} laps")
    
    print("\n" + "="*60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Multi-Car Racing Dynamics Simulation')
    parser.add_argument('--config', type=str, default='config/parameters.yaml',
                       help='Path to configuration YAML file (relative to racing_simulation directory)')
    parser.add_argument('--speed-multiplier', type=float, default=1.0,
                       help='Global speed multiplier (default: 1.0)')
    parser.add_argument('--no-plots', action='store_true',
                       help='Skip generating plots')
    parser.add_argument('--no-visualize', action='store_true',
                       help='Disable pygame real-time visualization (visualization is enabled by default)')
    parser.add_argument('--simulation-type', type=str, 
                       choices=['agent_based', 'discrete_event', 'monte_carlo', 'markov_chain'],
                       default='agent_based',
                       help='Simulation modeling approach (default: agent_based)')
    parser.add_argument('--monte-carlo-runs', type=int, default=10,
                       help='Number of runs for Monte Carlo simulation (default: 10)')
    
    args = parser.parse_args()
    
    # Visualization is enabled by default unless --no-visualize is specified
    visualize = not args.no_visualize
    
    # Load configuration
    try:
        config = load_config(args.config)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    # Get absolute config path for display
    if not os.path.isabs(args.config):
        project_root = get_project_root()
        config_display_path = os.path.join(project_root, args.config)
    else:
        config_display_path = args.config
    
    print("Multi-Car Racing Dynamics Simulation")
    print("="*60)
    print(f"Configuration: {config_display_path}")
    print(f"Speed Multiplier: {args.speed_multiplier}")
    print(f"Number of Cars: {config['num_cars']}")
    print(f"Target Laps: {config['simulation']['laps']}")
    print(f"Simulation Type: {args.simulation_type.upper().replace('_', ' ')}")
    if visualize:
        print("Visualization: ENABLED (pygame) - Close window or press ESC to quit")
        # Check if pygame is available
        try:
            import pygame
            print("Pygame is installed and ready.")
        except ImportError:
            print("\n" + "!"*60)
            print("ERROR: Pygame is not installed!")
            print("Install it with: pip install pygame")
            print("Or run without visualization: python Phase2.py --no-visualize")
            print("!"*60 + "\n")
    else:
        print("Visualization: DISABLED")
    
    # Create and run simulation based on type
    if args.simulation_type == 'agent_based':
        simulation = RacingSimulation(config, speed_multiplier=args.speed_multiplier, 
                                     visualize=visualize)
        results = simulation.run()
    elif args.simulation_type == 'discrete_event':
        print("\nUsing Discrete Event Simulation (event-driven approach)")
        simulation = DiscreteEventSimulation(config, speed_multiplier=args.speed_multiplier,
                                           visualize=visualize)
        results = simulation.run()
    elif args.simulation_type == 'monte_carlo':
        print(f"\nUsing Monte Carlo Simulation ({args.monte_carlo_runs} runs)")
        simulation = MonteCarloSimulation(config, base_speed_multiplier=args.speed_multiplier,
                                       num_runs=args.monte_carlo_runs, visualize=visualize)
        results = simulation.run()
        # For Monte Carlo, results structure is different
        if 'last_run' in results:
            # Use last run for visualization/analysis
            last_run_results = results['last_run']
            # Create a dummy simulation object for track access
            simulation = RacingSimulation(config, speed_multiplier=args.speed_multiplier, 
                                         visualize=False)
            simulation.track = RacingSimulation(config, speed_multiplier=args.speed_multiplier).track
    elif args.simulation_type == 'markov_chain':
        print("\nUsing Markov Chain Simulation (probabilistic state transitions)")
        simulation = MarkovChainSimulation(config, speed_multiplier=args.speed_multiplier,
                                         visualize=visualize)
        results = simulation.run()
    
    # Handle Monte Carlo results differently
    if args.simulation_type == 'monte_carlo':
        # Print Monte Carlo statistics
        print("\n" + "="*70)
        print("MONTE CARLO STATISTICS")
        print("="*70)
        stats = results['statistics']
        print(f"\nCollisions:")
        print(f"  Mean: {stats['collisions']['mean']:.2f} ± {stats['collisions']['std']:.2f}")
        print(f"  Range: [{stats['collisions']['min']}, {stats['collisions']['max']}]")
        if 'ci_95' in stats['collisions']:
            print(f"  95% CI: [{stats['collisions']['ci_95'][0]:.2f}, {stats['collisions']['ci_95'][1]:.2f}]")
        
        print(f"\nEliminated Cars:")
        print(f"  Mean: {stats['eliminated']['mean']:.2f} ± {stats['eliminated']['std']:.2f}")
        print(f"  Range: [{stats['eliminated']['min']}, {stats['eliminated']['max']}]")
        
        print(f"\nSimulation Time:")
        print(f"  Mean: {stats['simulation_time']['mean']:.2f}s ± {stats['simulation_time']['std']:.2f}s")
        
        if 'avg_lap_time' in stats:
            print(f"\nAverage Lap Time:")
            print(f"  Mean: {stats['avg_lap_time']['mean']:.2f}s ± {stats['avg_lap_time']['std']:.2f}s")
        
        # Use last run for detailed analysis
        results = last_run_results
        print("\n" + "="*70)
        print("DETAILED RESULTS (Last Run)")
        print("="*70)
    
    # Print summary
    print_summary(results)
    
    # Generate plots and analysis
    if not args.no_plots and args.simulation_type != 'monte_carlo':
        print("\nGenerating visualizations and analysis...")
        try:
            # Save plots to visualizations directory
            plot_results(results, config, output_dir=results['visualizations_dir'])
            plot_collision_heatmap(results, simulation.track, 
                                 output_dir=results['visualizations_dir'])
            print(f"Visualizations saved to {results['visualizations_dir']}")
            
            # Generate best path analysis
            analyze_best_path(results, simulation.track, 
                            output_dir=results['best_path_dir'])
            print(f"Best path analysis saved to {results['best_path_dir']}")
            
            # Save summary results
            save_results_summary(results, config, args.speed_multiplier,
                               output_dir=results['results_dir'])
            print(f"Results summary saved to {results['results_dir']}")
            
        except Exception as e:
            print(f"Warning: Error generating outputs: {e}")
            import traceback
            traceback.print_exc()
    elif args.simulation_type == 'monte_carlo':
        # Save Monte Carlo statistics
        import json
        stats_output_dir = os.path.join("output", "monte_carlo_results")
        os.makedirs(stats_output_dir, exist_ok=True)
        
        with open(os.path.join(stats_output_dir, "monte_carlo_statistics.json"), 'w') as f:
            json.dump(results['statistics'], f, indent=2)
        
        print(f"\nMonte Carlo statistics saved to: {stats_output_dir}")
        
        # Also generate plots for last run
        if 'last_run' in results and results['last_run']:
            try:
                last_run = results['last_run']
                if 'visualizations_dir' in last_run:
                    plot_results(last_run, config, output_dir=last_run['visualizations_dir'])
                    plot_collision_heatmap(last_run, simulation.track,
                                         output_dir=last_run['visualizations_dir'])
            except Exception as e:
                print(f"Warning: Could not generate plots for last run: {e}")
    
    # Safety vs Speed analysis
    if results['total_collisions'] > 0 or results['near_misses'] > 0:
        avg_speed_all = sum(results['average_speeds'].values()) / len(results['average_speeds'])
        print(f"\nSafety vs Speed Tradeoff:")
        print(f"  Average Speed: {avg_speed_all:.2f} m/s")
        print(f"  Total Accidents: {results['total_collisions']}")
        print(f"  Near Misses: {results['near_misses']}")
        print(f"  Risk Index: {results['total_collisions'] + results['near_misses']*0.1:.2f}")
    
    print(f"\nAll outputs saved to: {results['output_dir']}")
    print(f"  - Telemetry: {results['telemetry_dir']}")
    print(f"  - Visualizations: {results['visualizations_dir']}")
    print(f"  - Results: {results['results_dir']}")
    print(f"  - Best Path: {results['best_path_dir']}")
    print("\nSimulation complete!")


if __name__ == '__main__':
    main()

