"""
Markov Chain Modeling: Probabilistic state transition modeling for car strategies
"""
import numpy as np
from typing import Dict, List
from .simulation import RacingSimulation


class MarkovChainSimulation:
    """
    Markov Chain Simulation for probabilistic strategy transitions.
    
    Cars transition between states (aggressive, balanced, cautious, eliminated)
    based on transition probabilities that depend on performance metrics.
    """
    
    def __init__(self, config, speed_multiplier=1.0, visualize=False):
        """
        Initialize Markov Chain simulation.
        
        Args:
            config: Configuration dictionary
            speed_multiplier: Global speed multiplier
            visualize: Whether to show visualization
        """
        self.config = config
        self.speed_multiplier = speed_multiplier
        self.visualize = visualize
        
        # Define state space
        self.states = ['aggressive', 'balanced', 'cautious', 'eliminated']
        
        # Transition probability matrix (state -> state)
        # Probabilities depend on performance
        self.base_transition_matrix = {
            'aggressive': {'aggressive': 0.7, 'balanced': 0.2, 'cautious': 0.05, 'eliminated': 0.05},
            'balanced': {'aggressive': 0.1, 'balanced': 0.8, 'cautious': 0.08, 'eliminated': 0.02},
            'cautious': {'aggressive': 0.05, 'balanced': 0.15, 'cautious': 0.75, 'eliminated': 0.05},
            'eliminated': {'aggressive': 0.0, 'balanced': 0.0, 'cautious': 0.0, 'eliminated': 1.0}
        }
    
    def _update_transition_probabilities(self, car, all_cars):
        """
        Update transition probabilities based on car's performance.
        
        Args:
            car: Car object
            all_cars: List of all cars
        """
        # Adjust probabilities based on performance
        # If car has many collisions, increase elimination probability
        # If car is performing well, maintain current strategy
        
        current_state = car.strategy_type
        
        if current_state == 'eliminated':
            return  # No transitions from eliminated state
        
        # Calculate performance metrics
        collision_rate = car.collision_count / max(car.lap_count, 1)
        avg_speed = np.mean([p['velocity'] for p in car.trajectory]) if car.trajectory else 0
        
        # Adjust transition probabilities
        transition_probs = self.base_transition_matrix[current_state].copy()
        
        # High collision rate -> more likely to be eliminated or become cautious
        if collision_rate > 0.5:
            transition_probs['eliminated'] = min(0.3, transition_probs['eliminated'] * 2)
            transition_probs['cautious'] = min(0.4, transition_probs['cautious'] * 2)
            transition_probs['aggressive'] = max(0.0, transition_probs['aggressive'] * 0.5)
        
        # Low collision rate and high speed -> might become more aggressive
        elif collision_rate < 0.1 and avg_speed > car.desired_speed * 0.9:
            transition_probs['aggressive'] = min(0.3, transition_probs['aggressive'] * 1.5)
            transition_probs['eliminated'] = max(0.0, transition_probs['eliminated'] * 0.5)
        
        # Normalize probabilities
        total = sum(transition_probs.values())
        if total > 0:
            transition_probs = {k: v / total for k, v in transition_probs.items()}
        
        return transition_probs
    
    def _transition_state(self, car, all_cars):
        """
        Perform Markov Chain state transition for a car.
        
        Args:
            car: Car object
            all_cars: List of all cars
        """
        if car.eliminated:
            car.strategy_type = 'eliminated'
            return
        
        # Get transition probabilities
        transition_probs = self._update_transition_probabilities(car, all_cars)
        
        # Sample next state
        states = list(transition_probs.keys())
        probs = [transition_probs[s] for s in states]
        next_state = np.random.choice(states, p=probs)
        
        # If state changed, update car strategy
        if next_state != car.strategy_type and next_state != 'eliminated':
            old_strategy = car.strategy_type
            car.strategy_type = next_state
            
            # Update car parameters based on new strategy
            if next_state == 'aggressive':
                car.speed_multiplier = 1.2
                car.min_gap *= 0.8
            elif next_state == 'balanced':
                car.speed_multiplier = 1.0
            elif next_state == 'cautious':
                car.speed_multiplier = 0.9
                car.min_gap *= 1.2
            
            # Recreate controller with new strategy
            from .controller import CombinedController
            car.controller = CombinedController(self.config, next_state)
            
            print(f"Car {car.car_id}: {old_strategy} -> {next_state}")
        
        elif next_state == 'eliminated':
            car.eliminated = True
            car.elimination_time = None  # Will be set by collision handler
            car.elimination_reason = "Markov Chain state transition"
    
    def run(self):
        """
        Run Markov Chain simulation.
        
        Returns:
            Dictionary with simulation results
        """
        # Use base simulation but add Markov Chain transitions
        simulation = RacingSimulation(
            self.config,
            speed_multiplier=self.speed_multiplier,
            visualize=self.visualize
        )
        
        # Override the simulation loop to add Markov transitions
        original_run = simulation.run
        
        def run_with_markov():
            """Run simulation with Markov Chain state transitions."""
            import os
            import csv
            from datetime import datetime
            from tqdm import tqdm
            
            # Setup telemetry (reuse simulation's setup)
            simulation._setup_telemetry()
            
            max_steps = int(simulation.time_limit / simulation.dt)
            all_collisions = []
            
            print(f"Starting Markov Chain simulation with {len(simulation.cars)} cars...")
            print(f"Target: {simulation.target_laps} laps")
            print(f"Time limit: {simulation.time_limit}s")
            
            pbar = None
            if not simulation.visualize:
                pbar = tqdm(total=max_steps, desc="Simulating")
            
            try:
                for step in range(max_steps):
                    simulation.timestamp = step * simulation.dt
                    
                    # Handle pygame events
                    if simulation.visualize and simulation.visualizer:
                        if not simulation.visualizer.handle_events():
                            print("\nSimulation stopped by user.")
                            break
                    
                    # Check if all cars finished
                    active_cars = [c for c in simulation.cars if not c.eliminated]
                    if len(active_cars) == 0:
                        break
                    if all(c.lap_count >= simulation.target_laps for c in active_cars):
                        break
                    
                    # Update cars
                    for car in simulation.cars:
                        if car.eliminated:
                            continue
                        
                        if car.lane_change_timer > 0:
                            car.lane_change_timer -= simulation.dt
                        
                        # Markov Chain state transition (periodically)
                        if step % 20 == 0:  # Every 1 second (20 * 0.05)
                            self._transition_state(car, simulation.cars)
                        
                        if car.eliminated:
                            continue
                        
                        active_cars = [c for c in simulation.cars if not c.eliminated]
                        acceleration, steering_angle = car.controller.compute_control(
                            car, simulation.track, active_cars
                        )
                        
                        from .physics import update_car_dynamics
                        update_car_dynamics(car, acceleration, steering_angle, simulation.dt)
                        car.update_state(simulation.dt, simulation.track)
                    
                    # Check collisions
                    new_collisions = simulation.collision_detector.check_collisions(
                        simulation.cars, simulation.timestamp
                    )
                    all_collisions.extend(new_collisions)
                    
                    if simulation.elimination_enabled:
                        simulation._check_eliminations(new_collisions)
                    
                    # Check near-misses
                    active_cars = [car for car in simulation.cars if not car.eliminated]
                    simulation.near_misses += simulation.collision_detector.compute_near_misses(
                        active_cars, simulation.timestamp, simulation.ttc_threshold
                    )
                    
                    # Update visualization
                    if simulation.visualize and simulation.visualizer:
                        simulation.visualizer.update(
                            simulation.timestamp, new_collisions, simulation.near_misses, simulation.dt
                        )
                        simulation.visualizer.render(len(all_collisions), simulation.near_misses)
                        simulation.visualizer.tick(fps=60)
                    
                    # Log telemetry
                    simulation._log_telemetry()
                    
                    if pbar:
                        pbar.update(1)
            finally:
                if pbar:
                    pbar.close()
                if simulation.visualize and simulation.visualizer:
                    simulation.visualizer.quit()
            
            # Collect results
            import numpy as np
            results = {
                'total_collisions': len(all_collisions),
                'collisions': all_collisions,
                'near_misses': simulation.near_misses,
                'lap_times': {car.car_id: car.lap_times for car in simulation.cars},
                'average_speeds': {car.car_id: np.mean([p['velocity'] for p in car.trajectory]) if car.trajectory else 0.0
                                  for car in simulation.cars},
                'final_laps': {car.car_id: car.lap_count for car in simulation.cars},
                'simulation_time': simulation.timestamp,
                'output_dir': simulation.output_dir,
                'telemetry_dir': simulation.telemetry_dir,
                'visualizations_dir': simulation.visualizations_dir,
                'results_dir': simulation.results_dir,
                'best_path_dir': simulation.best_path_dir,
                'trajectories': {car.car_id: car.trajectory for car in simulation.cars},
                'eliminated_cars': {
                    car.car_id: {
                        'elimination_time': car.elimination_time,
                        'elimination_reason': car.elimination_reason,
                        'collision_count': car.collision_count,
                        'total_severity': car.total_collision_severity
                    }
                    for car in simulation.eliminated_cars
                },
                'num_eliminated': len(simulation.eliminated_cars),
                'markov_transitions': self._get_transition_history()
            }
            
            return results
        
        return run_with_markov()
    
    def _get_transition_history(self):
        """Get history of Markov Chain transitions."""
        # This would track state transitions over time
        # For now, return empty (could be enhanced)
        return {}

