"""
Discrete Event Simulation: Event-driven simulation engine
"""
import numpy as np
import heapq
from typing import List, Dict, Any, Callable
from .car import Car
from .track import Track
from .controller import CombinedController
from .physics import update_car_dynamics
from .collision import CollisionDetector


class Event:
    """
    Represents a discrete event in the simulation.
    
    Events are prioritized by time and processed in chronological order.
    """
    
    def __init__(self, time: float, event_type: str, handler: Callable, data: Dict = None):
        """
        Initialize an event.
        
        Args:
            time: Event time (simulation time)
            event_type: Type of event (e.g., 'collision', 'lane_change', 'lap_complete')
            handler: Function to handle the event
            data: Additional data for the event
        """
        self.time = time
        self.event_type = event_type
        self.handler = handler
        self.data = data or {}
    
    def __lt__(self, other):
        """Comparison for priority queue (earlier events first)."""
        return self.time < other.time
    
    def __eq__(self, other):
        """Equality comparison."""
        return self.time == other.time and self.event_type == other.event_type


class DiscreteEventSimulation:
    """
    Discrete Event Simulation engine for racing simulation.
    
    Uses an event queue to process events in chronological order rather than
    time-stepped updates. Events include collisions, lane changes, eliminations, etc.
    """
    
    def __init__(self, config, speed_multiplier=1.0, visualize=False):
        """
        Initialize discrete event simulation.
        
        Args:
            config: Configuration dictionary
            speed_multiplier: Global speed multiplier
            visualize: Whether to show visualization
        """
        self.config = config
        self.speed_multiplier = speed_multiplier
        self.visualize = visualize
        
        # Event queue (priority queue)
        self.event_queue = []
        self.current_time = 0.0
        
        # Initialize track
        track_config = config['track']
        num_lanes = track_config.get('num_lanes', 5)
        from .track import Track
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
        self.target_laps = config['simulation']['laps']
        self.time_limit = config['simulation']['time_limit']
        self.dt = config['simulation']['dt']  # Used for continuous updates between events
        
        # Statistics
        self.collisions = []
        self.near_misses = 0
        self.eliminated_cars = []
        
        # Visualization
        self.visualizer = None
        if self.visualize:
            try:
                from .visualization import PygameVisualization
                self.visualizer = PygameVisualization(self.track, self.cars)
            except ImportError:
                self.visualize = False
    
    def _initialize_cars(self):
        """Initialize cars with random starting positions."""
        from .car import Car
        from .controller import CombinedController
        
        num_cars = self.config['num_cars']
        strategy_dist = self.config['strategy_distribution']
        
        strategies = []
        for strategy, count in strategy_dist.items():
            strategies.extend([strategy] * count)
        np.random.shuffle(strategies)
        
        for i in range(num_cars):
            start_s = np.random.uniform(0, self.track.total_length)
            x = self.track.x_interp(start_s)
            y = self.track.y_interp(start_s)
            
            idx = np.argmin(np.abs(self.track.arc_lengths - start_s))
            if idx < len(self.track.centerline_x) - 1:
                dx = self.track.centerline_x[idx + 1] - self.track.centerline_x[idx]
                dy = self.track.centerline_y[idx + 1] - self.track.centerline_y[idx]
                yaw = np.arctan2(dy, dx)
            else:
                yaw = 0.0
            
            yaw += np.random.uniform(-0.1, 0.1)
            
            car = Car(i, x, y, yaw, strategies[i], self.config)
            car.desired_speed *= self.speed_multiplier
            car.controller = CombinedController(self.config, strategies[i])
            self.cars.append(car)
    
    def schedule_event(self, time: float, event_type: str, handler: Callable, data: Dict = None):
        """Schedule an event to occur at a specific time."""
        event = Event(time, event_type, handler, data)
        heapq.heappush(self.event_queue, event)
    
    def _check_collision_event(self, car1: Car, car2: Car):
        """Check if two cars will collide and schedule collision event."""
        # Predict collision time based on current trajectories
        dx = car2.x - car1.x
        dy = car2.y - car1.y
        distance = np.sqrt(dx**2 + dy**2)
        
        if distance < self.collision_detector.collision_radius:
            # Collision happening now
            self._handle_collision(car1, car2)
        else:
            # Predict future collision
            v1x = car1.velocity * np.cos(car1.yaw)
            v1y = car1.velocity * np.sin(car1.yaw)
            v2x = car2.velocity * np.cos(car2.yaw)
            v2y = car2.velocity * np.sin(car2.yaw)
            
            rel_vx = v2x - v1x
            rel_vy = v2y - v1y
            rel_v = np.sqrt(rel_vx**2 + rel_vy**2)
            
            if rel_v > 0.1:  # Approaching
                collision_time = distance / rel_v
                if collision_time < 5.0:  # Only schedule near-future collisions
                    self.schedule_event(
                        self.current_time + collision_time,
                        'collision',
                        lambda: self._handle_collision(car1, car2),
                        {'car1_id': car1.car_id, 'car2_id': car2.car_id}
                    )
    
    def _handle_collision(self, car1: Car, car2: Car):
        """Handle collision event."""
        # Calculate collision severity
        v1x = car1.velocity * np.cos(car1.yaw)
        v1y = car1.velocity * np.sin(car1.yaw)
        v2x = car2.velocity * np.cos(car2.yaw)
        v2y = car2.velocity * np.sin(car2.yaw)
        
        rel_vx = v2x - v1x
        rel_vy = v2y - v1y
        relative_speed = np.sqrt(rel_vx**2 + rel_vy**2)
        
        collision_event = {
            'timestamp': self.current_time,
            'car_id1': car1.car_id,
            'car_id2': car2.car_id,
            'x': (car1.x + car2.x) / 2,
            'y': (car1.y + car2.y) / 2,
            'lap': min(car1.lap_count, car2.lap_count),
            'severity': relative_speed
        }
        
        self.collisions.append(collision_event)
        car1.collision_flag = True
        car2.collision_flag = True
        
        car1.collision_count += 1
        car1.total_collision_severity += relative_speed
        car2.collision_count += 1
        car2.total_collision_severity += relative_speed
        
        # Check eliminations
        self._check_elimination(car1)
        self._check_elimination(car2)
    
    def _check_elimination(self, car: Car):
        """Check if car should be eliminated."""
        if car.eliminated:
            return
        
        elim_config = self.config['simulation'].get('elimination', {})
        if not elim_config.get('enabled', True):
            return
        
        elimination_chance = elim_config.get('elimination_chance', 6)
        roll = np.random.randint(1, 11)
        
        if roll < elimination_chance:
            car.eliminated = True
            car.elimination_time = self.current_time
            car.elimination_reason = f"Eliminated after collision (rolled {roll})"
            car.velocity = 0.0
            self.eliminated_cars.append(car)
            print(f"Car {car.car_id} eliminated: Rolled {roll} (threshold: <{elimination_chance})")
    
    def run(self):
        """Run discrete event simulation."""
        import os
        import csv
        from datetime import datetime
        
        # Setup output directories
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_name = f"run_{timestamp_str}"
        self.output_dir = os.path.join("output", run_name)
        self.telemetry_dir = os.path.join(self.output_dir, "telemetry")
        self.visualizations_dir = os.path.join(self.output_dir, "visualizations")
        self.results_dir = os.path.join(self.output_dir, "results")
        self.best_path_dir = os.path.join(self.output_dir, "best_path")
        
        os.makedirs(self.telemetry_dir, exist_ok=True)
        os.makedirs(self.visualizations_dir, exist_ok=True)
        os.makedirs(self.results_dir, exist_ok=True)
        os.makedirs(self.best_path_dir, exist_ok=True)
        
        # Setup telemetry files
        self.telemetry_files = {}
        for car in self.cars:
            filename = os.path.join(self.telemetry_dir, f"car_{car.car_id}.csv")
            self.telemetry_files[car.car_id] = filename
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'car_id', 'x', 'y', 'yaw', 'velocity',
                    'acceleration', 'lap', 's_position', 'collision_flag'
                ])
        
        # Schedule initial update events
        update_interval = self.dt
        for i in range(int(self.time_limit / update_interval)):
            self.schedule_event(
                i * update_interval,
                'update',
                self._update_all_cars
            )
        
        # Schedule periodic collision checks
        check_interval = 0.1  # Check every 0.1 seconds
        for i in range(int(self.time_limit / check_interval)):
            self.schedule_event(
                i * check_interval,
                'collision_check',
                self._check_all_collisions
            )
        
        print(f"Starting discrete event simulation with {len(self.cars)} cars...")
        print(f"Target: {self.target_laps} laps")
        print(f"Time limit: {self.time_limit}s")
        
        # Process events
        last_log_time = 0.0
        log_interval = 0.5  # Log every 0.5 seconds
        
        while self.event_queue and self.current_time < self.time_limit:
            # Get next event
            event = heapq.heappop(self.event_queue)
            self.current_time = event.time
            
            # Handle pygame events
            if self.visualize and self.visualizer:
                if not self.visualizer.handle_events():
                    print("\nSimulation stopped by user.")
                    break
            
            # Check if all cars finished
            active_cars = [c for c in self.cars if not c.eliminated]
            if len(active_cars) == 0:
                break
            if all(c.lap_count >= self.target_laps for c in active_cars):
                break
            
            # Execute event handler
            event.handler()
            
            # Log telemetry periodically
            if self.current_time - last_log_time >= log_interval:
                self._log_telemetry()
                last_log_time = self.current_time
            
            # Update visualization
            if self.visualize and self.visualizer:
                self.visualizer.update(self.current_time, [], self.near_misses, self.dt)
                self.visualizer.render(len(self.collisions), self.near_misses)
                self.visualizer.tick(fps=60)
        
        if self.visualize and self.visualizer:
            self.visualizer.quit()
        
        # Collect results
        return self._collect_results()
    
    def _update_all_cars(self):
        """Update all cars (called as event handler)."""
        active_cars = [c for c in self.cars if not c.eliminated]
        
        for car in self.cars:
            if car.eliminated:
                continue
            
            if car.lane_change_timer > 0:
                car.lane_change_timer -= self.dt
            
            acceleration, steering_angle = car.controller.compute_control(
                car, self.track, active_cars
            )
            
            update_car_dynamics(car, acceleration, steering_angle, self.dt)
            car.update_state(self.dt, self.track)
    
    def _check_all_collisions(self):
        """Check for collisions between all cars (called as event handler)."""
        new_collisions = self.collision_detector.check_collisions(self.cars, self.current_time)
        self.collisions.extend(new_collisions)
    
    def _log_telemetry(self):
        """Log telemetry for all cars."""
        import csv
        for car in self.cars:
            filename = self.telemetry_files[car.car_id]
            with open(filename, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    self.current_time,
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
    
    def _collect_results(self):
        """Collect simulation results."""
        import numpy as np
        
        return {
            'total_collisions': len(self.collisions),
            'collisions': self.collisions,
            'near_misses': self.near_misses,
            'lap_times': {car.car_id: car.lap_times for car in self.cars},
            'average_speeds': {car.car_id: np.mean([p['velocity'] for p in car.trajectory]) if car.trajectory else 0.0
                              for car in self.cars},
            'final_laps': {car.car_id: car.lap_count for car in self.cars},
            'simulation_time': self.current_time,
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

