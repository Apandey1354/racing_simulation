"""
Monte Carlo Simulation: Statistical simulation with multiple runs
"""
import numpy as np
from typing import List, Dict, Any
from .simulation import RacingSimulation


class MonteCarloSimulation:
    """
    Monte Carlo Simulation runner for statistical analysis.
    
    Runs multiple simulation runs with random parameter variations
    and collects statistical results (mean, std, confidence intervals).
    """
    
    def __init__(self, config, base_speed_multiplier=1.0, num_runs=10, visualize=False):
        """
        Initialize Monte Carlo simulation.
        
        Args:
            config: Configuration dictionary
            base_speed_multiplier: Base speed multiplier
            num_runs: Number of Monte Carlo runs
            visualize: Whether to show visualization (only for first run)
        """
        self.config = config
        self.base_speed_multiplier = base_speed_multiplier
        self.num_runs = num_runs
        self.visualize = visualize
        self.results = []
    
    def run(self):
        """
        Run Monte Carlo simulation (multiple runs with variations).
        
        Returns:
            Dictionary with statistical results
        """
        print("="*70)
        print("MONTE CARLO SIMULATION")
        print("="*70)
        print(f"Number of runs: {self.num_runs}")
        print(f"Base speed multiplier: {self.base_speed_multiplier}")
        print("="*70)
        
        # Run multiple simulations with random variations
        for run_num in range(self.num_runs):
            print(f"\nRun {run_num + 1}/{self.num_runs}")
            print("-"*70)
            
            # Add random variation to speed multiplier (±10%)
            speed_variation = np.random.uniform(-0.1, 0.1)
            speed_multiplier = self.base_speed_multiplier * (1 + speed_variation)
            
            # Add random variation to initial positions
            # (This is handled in simulation initialization)
            
            # Run single simulation (only visualize first run)
            visualize_this_run = self.visualize and (run_num == 0)
            simulation = RacingSimulation(
                self.config,
                speed_multiplier=speed_multiplier,
                visualize=visualize_this_run
            )
            
            result = simulation.run()
            result['run_number'] = run_num + 1
            result['speed_multiplier'] = speed_multiplier
            self.results.append(result)
            
            print(f"Run {run_num + 1} complete:")
            print(f"  Collisions: {result['total_collisions']}")
            print(f"  Eliminated: {result.get('num_eliminated', 0)}")
            print(f"  Simulation time: {result['simulation_time']:.2f}s")
        
        # Calculate statistics
        return self._calculate_statistics()
    
    def _calculate_statistics(self):
        """Calculate statistical metrics across all runs."""
        if not self.results:
            return {}
        
        # Extract metrics
        collisions = [r['total_collisions'] for r in self.results]
        eliminated = [r.get('num_eliminated', 0) for r in self.results]
        sim_times = [r['simulation_time'] for r in self.results]
        near_misses = [r['near_misses'] for r in self.results]
        
        # Calculate average lap times
        all_avg_lap_times = []
        for result in self.results:
            for car_id, lap_times in result['lap_times'].items():
                if lap_times:
                    all_avg_lap_times.extend([np.mean(lap_times)])
        
        # Calculate statistics
        stats = {
            'num_runs': self.num_runs,
            'collisions': {
                'mean': np.mean(collisions),
                'std': np.std(collisions),
                'min': np.min(collisions),
                'max': np.max(collisions),
                'values': collisions
            },
            'eliminated': {
                'mean': np.mean(eliminated),
                'std': np.std(eliminated),
                'min': np.min(eliminated),
                'max': np.max(eliminated),
                'values': eliminated
            },
            'simulation_time': {
                'mean': np.mean(sim_times),
                'std': np.std(sim_times),
                'min': np.min(sim_times),
                'max': np.max(sim_times),
                'values': sim_times
            },
            'near_misses': {
                'mean': np.mean(near_misses),
                'std': np.std(near_misses),
                'min': np.min(near_misses),
                'max': np.max(near_misses),
                'values': near_misses
            }
        }
        
        if all_avg_lap_times:
            stats['avg_lap_time'] = {
                'mean': np.mean(all_avg_lap_times),
                'std': np.std(all_avg_lap_times),
                'min': np.min(all_avg_lap_times),
                'max': np.max(all_avg_lap_times)
            }
        
        # Calculate 95% confidence intervals
        from scipy import stats as scipy_stats
        if len(collisions) > 1:
            stats['collisions']['ci_95'] = scipy_stats.t.interval(
                0.95, len(collisions)-1,
                loc=np.mean(collisions),
                scale=scipy_stats.sem(collisions)
            )
        
        # Combine with last run's detailed results
        combined_results = {
            'statistics': stats,
            'individual_runs': self.results,
            'last_run': self.results[-1] if self.results else {}
        }
        
        return combined_results

