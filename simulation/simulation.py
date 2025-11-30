"""
Simulation Engine: Main Simulation Loop
"""
import numpy as np
import os
import csv
from datetime import datetime
from tqdm import tqdm

from .car import Car
from .track import Track
from .controller import CombinedController
from .physics import update_car_dynamics
from .collision import CollisionDetector


class RacingSimulation:
    """
    Main simulation engine for multi-car racing.
    """
    
    def __init__(self, config, speed_multiplier=1.0, visualize=False):
        """
        Initialize simulation.
        
        Args:
            config: Configuration dictionary from YAML
            speed_multiplier: Global speed multiplier
            visualize: Whether to show pygame visualization
        """
        self.config = config
        self.speed_multiplier = speed_multiplier
        self.visualize = visualize
        
        # Initialize track
        track_config = config['track']
        num_lanes = track_config.get('num_lanes', 5)
        self.track = Track(
            radius_x=track_config['radius_x'],
            radius_y=track_config['radius_y'],
            width=track_config['width'],
            num_lanes=num_lanes
        )
        
        # Initialize cars
        self.cars = []
        self._initialize_cars()
        
        # Initialize collision detector
        self.collision_detector = CollisionDetector(
            collision_radius=config['simulation']['collision_radius']
        )
        
        # Simulation parameters
        self.dt = config['simulation']['dt']
        self.target_laps = config['simulation']['laps']
        self.time_limit = config['simulation']['time_limit']
        self.ttc_threshold = config['simulation']['near_miss_ttc_threshold']
        
        # Telemetry
        self.telemetry_dir = None
        self.telemetry_files = {}
        self.timestamp = 0.0
        
        # Metrics
        self.near_misses = 0
        self.eliminated_cars = []  # Track eliminated cars
        
        # Elimination parameters
        sim_config = config['simulation']
        elim_config = sim_config.get('elimination', {})
        self.elimination_enabled = elim_config.get('enabled', True)
        self.elimination_chance = elim_config.get('elimination_chance', 6)  # Threshold: if roll < 6, eliminate
        
        # Visualization
        self.visualizer = None
        if self.visualize:
            try:
                from .visualization import PygameVisualization
                print("Initializing pygame visualization...")
                self.visualizer = PygameVisualization(self.track, self.cars)
                print("Pygame visualization initialized successfully!")
            except ImportError as e:
                print(f"Warning: pygame not available. Visualization disabled.")
                print(f"Error: {e}")
                print("Install pygame with: pip install pygame")
                self.visualize = False
            except Exception as e:
                print(f"Warning: Failed to initialize visualization: {e}")
                print("Visualization disabled. Continuing without visualization.")
                self.visualize = False
                import traceback
                traceback.print_exc()
    
    def _initialize_cars(self):
        """Initialize cars with random starting positions."""
        num_cars = self.config['num_cars']
        strategy_dist = self.config['strategy_distribution']
        
        # Create strategy list
        strategies = []
        for strategy, count in strategy_dist.items():
            strategies.extend([strategy] * count)
        
        # Shuffle strategies
        np.random.shuffle(strategies)
        
        # Initialize cars with random starting positions along track
        for i in range(num_cars):
            # Random starting arc-length
            start_s = np.random.uniform(0, self.track.total_length)
            
            # Get position on centerline
            x = self.track.x_interp(start_s)
            y = self.track.y_interp(start_s)
            
            # Random starting yaw (tangent to track)
            # Approximate by using nearby points
            idx = np.argmin(np.abs(self.track.arc_lengths - start_s))
            if idx < len(self.track.centerline_x) - 1:
                dx = self.track.centerline_x[idx + 1] - self.track.centerline_x[idx]
                dy = self.track.centerline_y[idx + 1] - self.track.centerline_y[idx]
                yaw = np.arctan2(dy, dx)
            else:
                yaw = 0.0
            
            # Add small random offset
            yaw += np.random.uniform(-0.1, 0.1)
            
            # Create car
            car = Car(i, x, y, yaw, strategies[i], self.config)
            
            # Apply speed multiplier
            car.desired_speed *= self.speed_multiplier
            
            # Create controller
            car.controller = CombinedController(self.config, strategies[i])
            
            self.cars.append(car)
    
    def _setup_telemetry(self):
        """Setup telemetry logging directory and files."""
        # Create output directory structure with timestamp
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_name = f"run_{timestamp_str}"
        
        # Main output directory
        self.output_dir = os.path.join("output", run_name)
        self.telemetry_dir = os.path.join(self.output_dir, "telemetry")
        self.visualizations_dir = os.path.join(self.output_dir, "visualizations")
        self.results_dir = os.path.join(self.output_dir, "results")
        self.best_path_dir = os.path.join(self.output_dir, "best_path")
        
        # Create all directories
        os.makedirs(self.telemetry_dir, exist_ok=True)
        os.makedirs(self.visualizations_dir, exist_ok=True)
        os.makedirs(self.results_dir, exist_ok=True)
        os.makedirs(self.best_path_dir, exist_ok=True)
        
        # Create CSV files for each car
        for car in self.cars:
            filename = os.path.join(self.telemetry_dir, f"car_{car.car_id}.csv")
            self.telemetry_files[car.car_id] = filename
            
            # Write header
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'car_id', 'x', 'y', 'yaw', 'velocity', 
                    'acceleration', 'lap', 's_position', 'collision_flag'
                ])
    
    def _log_telemetry(self):
        """Log telemetry for all cars."""
        for car in self.cars:
            filename = self.telemetry_files[car.car_id]
            with open(filename, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    self.timestamp,
                    car.car_id,
                    car.x,
                    car.y,
                    car.yaw,
                    car.velocity,
                    car.acceleration,
                    car.lap_count,
                    car.s_position,
                    1 if car.collision_flag else 0
                ])
            car.reset_collision_flag()
    
    def _check_eliminations(self, new_collisions):
        """
        Check if cars should be eliminated based on random chance after collision.
        Rolls 1-10, if result < elimination_chance, car is eliminated.
        
        Args:
            new_collisions: List of new collision events
        """
        for collision in new_collisions:
            car1_id = collision['car_id1']
            car2_id = collision['car_id2']
            
            # Find cars
            car1 = next((c for c in self.cars if c.car_id == car1_id), None)
            car2 = next((c for c in self.cars if c.car_id == car2_id), None)
            
            # Check car1 for elimination
            if car1 and not car1.eliminated:
                # Roll random number 1-10
                roll = np.random.randint(1, 11)
                
                # If roll is less than elimination_chance (default 6), eliminate
                if roll < self.elimination_chance:
                    car1.eliminated = True
                    car1.elimination_time = self.timestamp
                    car1.elimination_reason = f"Eliminated after collision (rolled {roll}, threshold: {self.elimination_chance})"
                    car1.velocity = 0.0  # Stop the car
                    self.eliminated_cars.append(car1)
                    print(f"Car {car1.car_id} eliminated: Rolled {roll} (threshold: <{self.elimination_chance})")
            
            # Check car2 for elimination
            if car2 and not car2.eliminated:
                # Roll random number 1-10
                roll = np.random.randint(1, 11)
                
                # If roll is less than elimination_chance (default 6), eliminate
                if roll < self.elimination_chance:
                    car2.eliminated = True
                    car2.elimination_time = self.timestamp
                    car2.elimination_reason = f"Eliminated after collision (rolled {roll}, threshold: {self.elimination_chance})"
                    car2.velocity = 0.0  # Stop the car
                    self.eliminated_cars.append(car2)
                    print(f"Car {car2.car_id} eliminated: Rolled {roll} (threshold: <{self.elimination_chance})")
    
    def run(self):
        """
        Run the simulation.
        
        Returns:
            Dictionary with simulation results and metrics
        """
        # Setup telemetry
        self._setup_telemetry()
        
        # Simulation loop
        max_steps = int(self.time_limit / self.dt)
        all_collisions = []
        
        print(f"Starting simulation with {len(self.cars)} cars...")
        print(f"Target: {self.target_laps} laps")
        print(f"Time limit: {self.time_limit}s")
        if self.visualize and self.visualizer:
            print("Pygame visualization enabled. Close window or press ESC to quit.")
            # Render initial frame to show window immediately
            try:
                self.visualizer.render(0, 0)
            except Exception as e:
                print(f"Warning: Could not render initial frame: {e}")
        elif self.visualize and not self.visualizer:
            print("WARNING: Visualization requested but pygame is not installed!")
            print("Install pygame with: pip install pygame")
        
        # Progress bar (only if not visualizing)
        pbar = None
        if not self.visualize:
            pbar = tqdm(total=max_steps, desc="Simulating")
        
        try:
            for step in range(max_steps):
                self.timestamp = step * self.dt
                
                # Handle pygame events
                if self.visualize and self.visualizer:
                    if not self.visualizer.handle_events():
                        print("\nSimulation stopped by user.")
                        break
                
                # Check if all active cars completed target laps
                active_cars = [car for car in self.cars if not car.eliminated]
                if len(active_cars) == 0:
                    print(f"\nAll cars eliminated at t={self.timestamp:.2f}s")
                    break
                
                all_finished = all(car.lap_count >= self.target_laps for car in active_cars)
                if all_finished:
                    print(f"\nAll active cars completed {self.target_laps} laps at t={self.timestamp:.2f}s")
                    break
                
                # Update each car (only active, non-eliminated cars)
                for car in self.cars:
                    if car.eliminated:
                        # Eliminated cars stop moving but remain visible
                        continue
                    
                    # Update lane change timer
                    if car.lane_change_timer > 0:
                        car.lane_change_timer -= self.dt
                    
                    # Compute control (only consider active cars)
                    active_cars = [c for c in self.cars if not c.eliminated]
                    acceleration, steering_angle = car.controller.compute_control(
                        car, self.track, active_cars
                    )
                    
                    # Update physics
                    update_car_dynamics(car, acceleration, steering_angle, self.dt)
                    
                    # Update state (track projection, lap counting)
                    car.update_state(self.dt, self.track)
                
                # Check collisions
                new_collisions = self.collision_detector.check_collisions(self.cars, self.timestamp)
                all_collisions.extend(new_collisions)
                
                # Check for eliminations based on collision severity
                if self.elimination_enabled:
                    self._check_eliminations(new_collisions)
                
                # Check near-misses (only for active cars)
                active_cars = [car for car in self.cars if not car.eliminated]
                self.near_misses += self.collision_detector.compute_near_misses(
                    active_cars, self.timestamp, self.ttc_threshold
                )
                
                # Update visualization
                if self.visualize and self.visualizer:
                    self.visualizer.update(self.timestamp, new_collisions, self.near_misses, self.dt)
                    self.visualizer.render(len(all_collisions), self.near_misses)
                    self.visualizer.tick(fps=60)
                
                # Log telemetry
                self._log_telemetry()
                
                if pbar:
                    pbar.update(1)
        finally:
            if pbar:
                pbar.close()
            if self.visualize and self.visualizer:
                self.visualizer.quit()
        
        # Collect results
        results = {
            'total_collisions': len(all_collisions),
            'collisions': all_collisions,
            'near_misses': self.near_misses,
            'lap_times': {car.car_id: car.lap_times for car in self.cars},
            'average_speeds': {car.car_id: np.mean([p['velocity'] for p in car.trajectory]) if car.trajectory else 0.0
                              for car in self.cars},
            'final_laps': {car.car_id: car.lap_count for car in self.cars},
            'simulation_time': self.timestamp,
            'output_dir': self.output_dir,
            'telemetry_dir': self.telemetry_dir,
            'visualizations_dir': self.visualizations_dir,
            'results_dir': self.results_dir,
            'best_path_dir': self.best_path_dir,
            'trajectories': {car.car_id: car.trajectory for car in self.cars},
            'eliminated_cars': {
                car.car_id: {
                    'elimination_time': car.elimination_time,
                    'elimination_reason': car.elimination_reason,
                    'collision_count': car.collision_count,
                    'total_severity': car.total_collision_severity
                }
                for car in self.eliminated_cars
            },
            'num_eliminated': len(self.eliminated_cars)
        }
        
        return results

