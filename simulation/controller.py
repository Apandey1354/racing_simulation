"""
Controller: IDM (Intelligent Driver Model) + Pure Pursuit Steering
"""
import numpy as np


class IDMController:
    """
    Intelligent Driver Model for longitudinal control (acceleration).
    """
    
    def __init__(self, a_max, b_max, min_gap, reaction_time, desired_speed):
        """
        Initialize IDM controller.
        
        Args:
            a_max: Maximum acceleration (m/s^2)
            b_max: Maximum braking deceleration (m/s^2)
            min_gap: Minimum gap to leading vehicle (m)
            reaction_time: Reaction time (s)
            desired_speed: Desired speed (m/s)
        """
        self.a_max = a_max
        self.b_max = b_max
        self.min_gap = min_gap
        self.reaction_time = reaction_time
        self.desired_speed = desired_speed
        self.delta = 4.0  # Acceleration exponent (typical value)
    
    def compute_acceleration(self, car, leading_car=None, distance=None, relative_velocity=0.0):
        """
        Compute acceleration using IDM.
        
        Args:
            car: Car object
            leading_car: Leading car object (if any)
            distance: Distance to leading car (m)
            relative_velocity: Relative velocity (m/s, positive if leading car is faster)
        
        Returns:
            Acceleration (m/s^2)
        """
        v = car.velocity
        v0 = car.desired_speed * car.speed_multiplier
        
        # Free road acceleration term
        free_term = 1 - (v / v0)**self.delta
        
        # Interaction term (if there's a leading car)
        if leading_car is not None and distance is not None:
            # Desired gap: s_star = s0 + v*T + (v*dv) / (2*sqrt(a_max*b_max))
            s0 = self.min_gap
            T = self.reaction_time
            dv = -relative_velocity  # Negative if approaching
            
            s_star = s0 + v * T + (v * dv) / (2 * np.sqrt(self.a_max * self.b_max))
            
            # Interaction term
            interaction_term = (s_star / max(distance, 0.1))**2
            
            # IDM acceleration
            acceleration = self.a_max * (free_term - interaction_term)
        else:
            # No leading car, just free road acceleration
            acceleration = self.a_max * free_term
        
        # Clamp to physical limits
        acceleration = np.clip(acceleration, -self.b_max, self.a_max)
        
        return acceleration


class PurePursuitController:
    """
    Pure Pursuit steering controller for lateral control.
    """
    
    def __init__(self, lookahead_distance, wheelbase):
        """
        Initialize Pure Pursuit controller.
        
        Args:
            lookahead_distance: Lookahead distance (m)
            wheelbase: Wheelbase length (m)
        """
        self.lookahead_distance = lookahead_distance
        self.wheelbase = wheelbase
    
    def compute_steering_angle(self, car, target_x, target_y):
        """
        Compute steering angle using Pure Pursuit.
        
        Args:
            car: Car object
            target_x, target_y: Target point coordinates
        
        Returns:
            Steering angle delta (radians)
        """
        # Vector from car to target
        dx = target_x - car.x
        dy = target_y - car.y
        
        # Distance to target
        distance = np.sqrt(dx**2 + dy**2)
        
        if distance < 0.1:
            return 0.0
        
        # Angle from car heading to target
        alpha = np.arctan2(dy, dx) - car.yaw
        
        # Normalize alpha to [-pi, pi]
        alpha = np.arctan2(np.sin(alpha), np.cos(alpha))
        
        # Pure Pursuit formula: delta = atan(2 * L * sin(alpha) / lookahead)
        # Use actual distance if it's less than lookahead
        effective_lookahead = min(distance, self.lookahead_distance)
        
        delta = np.arctan2(2 * self.wheelbase * np.sin(alpha), effective_lookahead)
        
        # Clamp steering angle to reasonable limits (±30 degrees)
        max_steering = np.radians(30)
        delta = np.clip(delta, -max_steering, max_steering)
        
        return delta


class CombinedController:
    """
    Combined IDM + Pure Pursuit controller.
    """
    
    def __init__(self, config, strategy_type):
        """Initialize combined controller."""
        controller_config = config['controller']
        
        self.idm = IDMController(
            a_max=controller_config['a_max'],
            b_max=controller_config['b_max'],
            min_gap=controller_config['min_gap'],
            reaction_time=controller_config['reaction_time'],
            desired_speed=controller_config['desired_speed'][strategy_type]
        )
        
        self.pure_pursuit = PurePursuitController(
            lookahead_distance=controller_config['lookahead_distance'],
            wheelbase=controller_config['wheelbase']
        )
    
    def _check_lane_clear(self, car, target_lane, all_cars, lookahead_distance=20.0):
        """
        Check if a lane is clear for lane change.
        
        Args:
            car: Car object
            target_lane: Lane to check (0-4)
            all_cars: List of all cars
            lookahead_distance: Distance to check ahead
        
        Returns:
            True if lane is clear, False otherwise
        """
        if target_lane < 0 or target_lane >= 5:
            return False
        
        # Check for cars in target lane
        for other_car in all_cars:
            if other_car.car_id == car.car_id:
                continue
            
            # Only check cars in target lane
            if abs(other_car.lane - target_lane) > 0.5:  # Not in target lane
                continue
            
            # Check if car is nearby (ahead or behind)
            dx = other_car.x - car.x
            dy = other_car.y - car.y
            distance = np.sqrt(dx**2 + dy**2)
            
            # Project onto car's forward direction
            forward_x = np.cos(car.yaw)
            forward_y = np.sin(car.yaw)
            projection = dx * forward_x + dy * forward_y
            
            # Check if car is in the danger zone (ahead or close behind)
            if abs(projection) < lookahead_distance:
                return False
        
        return True
    
    def _decide_lane_change(self, car, track, all_cars):
        """
        Decide if car should change lanes for overtaking.
        
        Returns:
            Target lane number, or None if no change needed
        """
        # Don't change lanes too frequently
        if car.lane_change_timer > 0:
            return None
        
        # Find leading car in current lane
        leading_car = None
        leading_distance = None
        leading_speed = None
        
        for other_car in all_cars:
            if other_car.car_id == car.car_id:
                continue
            
            # Check if car is in same lane (with tolerance)
            if abs(other_car.lane - car.lane) > 0.5:
                continue
            
            # Check if car is ahead
            dx = other_car.x - car.x
            dy = other_car.y - car.y
            
            forward_x = np.cos(car.yaw)
            forward_y = np.sin(car.yaw)
            projection = dx * forward_x + dy * forward_y
            
            if projection > 0 and projection < 30.0:  # Car is ahead and close
                distance = np.sqrt(dx**2 + dy**2)
                if leading_car is None or distance < leading_distance:
                    leading_car = other_car
                    leading_distance = distance
                    leading_speed = other_car.velocity
        
        # If there's a slower car ahead, try to change lanes
        if leading_car is not None and leading_speed < car.velocity * 0.9:
            # Prefer changing to faster lanes (outer lanes for overtaking)
            # Try lanes in order: current+1, current+2, current-1, current-2
            candidates = []
            if car.lane < 4:
                candidates.append(car.lane + 1)
            if car.lane < 3:
                candidates.append(car.lane + 2)
            if car.lane > 0:
                candidates.append(car.lane - 1)
            if car.lane > 1:
                candidates.append(car.lane - 2)
            
            # Check each candidate lane
            for candidate_lane in candidates:
                if self._check_lane_clear(car, candidate_lane, all_cars):
                    return candidate_lane
        
        return None
    
    def compute_control(self, car, track, all_cars, sensing_radius=50.0):
        """
        Compute acceleration and steering angle.
        
        Args:
            car: Car object
            track: Track object
            all_cars: List of all cars
            sensing_radius: Sensing radius for neighbors
        
        Returns:
            (acceleration, steering_angle)
        """
        # Update lane change timer (will be decremented in simulation loop)
        # This is just a check here
        
        # Decide on lane change
        target_lane = self._decide_lane_change(car, track, all_cars)
        if target_lane is not None:
            car.target_lane = target_lane
            car.lane_change_timer = 2.0  # Prevent rapid lane changes (2 seconds)
        
        # Smoothly transition to target lane
        lane_diff = car.target_lane - car.lane
        if abs(lane_diff) > 0.1:
            # Gradually change lane
            lane_change_rate = 0.1  # Lane change speed
            if lane_diff > 0:
                car.lane = min(car.lane + lane_change_rate, car.target_lane)
            else:
                car.lane = max(car.lane - lane_change_rate, car.target_lane)
        else:
            car.lane = car.target_lane
        
        # Clamp lane to valid range
        car.lane = np.clip(car.lane, 0, 4)
        car.target_lane = np.clip(car.target_lane, 0, 4)
        
        # Sense neighbors
        neighbors = car.sense_neighbors(all_cars, sensing_radius)
        
        # Find leading car (closest car ahead in same lane)
        leading_car = None
        leading_distance = None
        leading_relative_velocity = None
        
        for neighbor_car, distance, rel_vel in neighbors:
            # Check if car is in same lane
            if abs(neighbor_car.lane - car.lane) > 0.5:
                continue
            
            # Check if car is ahead
            dx = neighbor_car.x - car.x
            dy = neighbor_car.y - car.y
            
            # Project onto car's forward direction
            forward_x = np.cos(car.yaw)
            forward_y = np.sin(car.yaw)
            projection = dx * forward_x + dy * forward_y
            
            if projection > 0:  # Car is ahead
                leading_car = neighbor_car
                leading_distance = distance
                leading_relative_velocity = rel_vel
                break
        
        # Compute IDM acceleration
        acceleration = self.idm.compute_acceleration(
            car, leading_car, leading_distance, leading_relative_velocity
        )
        
        # Get target point on current lane
        target_lane_int = int(np.round(car.lane))
        target_x, target_y = track.get_target_point(car.s_position, car.lookahead_distance, 
                                                   lane=target_lane_int)
        
        # Compute Pure Pursuit steering
        steering_angle = self.pure_pursuit.compute_steering_angle(car, target_x, target_y)
        
        return acceleration, steering_angle

