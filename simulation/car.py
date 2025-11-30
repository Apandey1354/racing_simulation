"""
Car Model: State, Parameters, and Sensing
"""
import numpy as np


class Car:
    """
    Represents a single autonomous racing car with state and parameters.
    """
    
    def __init__(self, car_id, x, y, yaw, strategy_type, config):
        """
        Initialize a car.
        
        Args:
            car_id: Unique identifier
            x, y: Initial position
            yaw: Initial heading angle (radians)
            strategy_type: "aggressive", "balanced", or "cautious"
            config: Configuration dictionary from YAML
        """
        self.car_id = car_id
        self.strategy_type = strategy_type
        
        # State variables
        self.x = x
        self.y = y
        self.yaw = yaw
        self.velocity = 0.0
        self.acceleration = 0.0
        self.lane = np.random.randint(0, 5)  # Random initial lane (0-4)
        self.target_lane = self.lane  # Target lane for lane changing
        self.lap_count = 0
        self.s_position = 0.0  # Arc-length position on track
        self.lane_change_timer = 0.0  # Timer to prevent rapid lane changes
        
        # Strategy-based parameters
        self.desired_speed = config['controller']['desired_speed'][strategy_type]
        self.max_accel = config['controller']['a_max']
        self.max_brake = config['controller']['b_max']
        self.reaction_time = config['controller']['reaction_time']
        self.min_gap = config['controller']['min_gap']
        
        # Additional parameters
        self.wheelbase = config['controller']['wheelbase']
        self.lookahead_distance = config['controller']['lookahead_distance']
        
        # Strategy multipliers
        if strategy_type == "aggressive":
            self.speed_multiplier = 1.2
            self.min_gap *= 0.8  # Closer following
        elif strategy_type == "balanced":
            self.speed_multiplier = 1.0
        else:  # cautious
            self.speed_multiplier = 0.9
            self.min_gap *= 1.2  # Larger gap
        
        # Telemetry history
        self.trajectory = []
        self.collision_flag = False
        
        # Collision tracking for elimination
        self.collision_count = 0
        self.total_collision_severity = 0.0  # Cumulative collision severity
        self.eliminated = False
        self.elimination_time = None
        self.elimination_reason = None
        
        # Performance metrics
        self.lap_times = []
        self.last_lap_start_s = 0.0
        self.last_lap_start_time = 0.0
    
    def update_state(self, dt, track):
        """
        Update car state based on physics and track projection.
        
        Args:
            dt: Time step
            track: Track object for position projection
        """
        # Project position onto track to get arc-length
        old_s = self.s_position
        self.s_position = track.project_car_position(self.x, self.y)
        
        # Check for lap completion
        if old_s > track.total_length * 0.9 and self.s_position < track.total_length * 0.1:
            self.lap_count += 1
            if self.last_lap_start_time > 0:
                lap_time = self.last_lap_start_time
                self.lap_times.append(lap_time)
            self.last_lap_start_s = self.s_position
            self.last_lap_start_time = 0.0  # Reset for new lap
        
        # Update lap timer
        self.last_lap_start_time += dt
        
        # Store trajectory point
        self.trajectory.append({
            'x': self.x,
            'y': self.y,
            'yaw': self.yaw,
            'velocity': self.velocity,
            'acceleration': self.acceleration,
            's_position': self.s_position,
            'lap': self.lap_count
        })
    
    def sense_neighbors(self, all_cars, radius):
        """
        Sense neighboring cars within radius.
        
        Args:
            all_cars: List of all Car objects
            radius: Sensing radius (meters)
        
        Returns:
            List of (car, distance, relative_velocity) tuples
        """
        neighbors = []
        
        for other_car in all_cars:
            if other_car.car_id == self.car_id:
                continue
            
            # Compute distance
            dx = other_car.x - self.x
            dy = other_car.y - self.y
            distance = np.sqrt(dx**2 + dy**2)
            
            if distance <= radius:
                # Compute relative velocity (projected along line of sight)
                rel_vx = other_car.velocity * np.cos(other_car.yaw) - self.velocity * np.cos(self.yaw)
                rel_vy = other_car.velocity * np.sin(other_car.yaw) - self.velocity * np.sin(self.yaw)
                
                # Project onto line of sight
                if distance > 0:
                    cos_theta = dx / distance
                    sin_theta = dy / distance
                    relative_velocity = rel_vx * cos_theta + rel_vy * sin_theta
                else:
                    relative_velocity = 0.0
                
                neighbors.append((other_car, distance, relative_velocity))
        
        # Sort by distance (closest first)
        neighbors.sort(key=lambda x: x[1])
        
        return neighbors
    
    def get_max_speed(self):
        """Get maximum allowed speed for this car."""
        return self.desired_speed * self.speed_multiplier
    
    def reset_collision_flag(self):
        """Reset collision flag after logging."""
        self.collision_flag = False

