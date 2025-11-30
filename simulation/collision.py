"""
Collision Detection: Circle-based Collision Detection
"""
import numpy as np


class CollisionDetector:
    """
    Detects collisions between cars using circle-based collision detection.
    """
    
    def __init__(self, collision_radius):
        """
        Initialize collision detector.
        
        Args:
            collision_radius: Collision detection radius (m)
        """
        self.collision_radius = collision_radius
        self.collisions = []  # List of collision events
    
    def check_collisions(self, cars, timestamp):
        """
        Check for collisions between all pairs of cars and calculate severity.
        
        Args:
            cars: List of Car objects
            timestamp: Current simulation time
        
        Returns:
            List of collision events with severity information
        """
        new_collisions = []
        collision_pairs = set()  # Track pairs to avoid duplicates
        
        for i, car1 in enumerate(cars):
            # Skip eliminated cars
            if car1.eliminated:
                continue
                
            for car2 in cars[i+1:]:
                # Skip eliminated cars
                if car2.eliminated:
                    continue
                
                # Check if already detected this collision
                pair = tuple(sorted([car1.car_id, car2.car_id]))
                if pair in collision_pairs:
                    continue
                
                # Compute distance
                dx = car1.x - car2.x
                dy = car1.y - car2.y
                distance = np.sqrt(dx**2 + dy**2)
                
                if distance < self.collision_radius:
                    # Collision detected
                    collision_pairs.add(pair)
                    
                    # Calculate collision severity based on relative velocity
                    # Severity = magnitude of relative velocity at impact
                    v1x = car1.velocity * np.cos(car1.yaw)
                    v1y = car1.velocity * np.sin(car1.yaw)
                    v2x = car2.velocity * np.cos(car2.yaw)
                    v2y = car2.velocity * np.sin(car2.yaw)
                    
                    rel_vx = v2x - v1x
                    rel_vy = v2y - v1y
                    relative_speed = np.sqrt(rel_vx**2 + rel_vy**2)
                    
                    # Collision severity (higher = worse)
                    severity = relative_speed
                    
                    # Record collision
                    collision_event = {
                        'timestamp': timestamp,
                        'car_id1': car1.car_id,
                        'car_id2': car2.car_id,
                        'x': (car1.x + car2.x) / 2,
                        'y': (car1.y + car2.y) / 2,
                        'lap': min(car1.lap_count, car2.lap_count),
                        'severity': severity
                    }
                    
                    new_collisions.append(collision_event)
                    self.collisions.append(collision_event)
                    
                    # Update car collision statistics
                    car1.collision_count += 1
                    car1.total_collision_severity += severity
                    car2.collision_count += 1
                    car2.total_collision_severity += severity
                    
                    # Mark cars as collided
                    car1.collision_flag = True
                    car2.collision_flag = True
        
        return new_collisions
    
    def get_all_collisions(self):
        """Get all recorded collisions."""
        return self.collisions
    
    def get_collision_count(self):
        """Get total number of collisions."""
        return len(self.collisions)
    
    def compute_near_misses(self, cars, timestamp, ttc_threshold=2.0):
        """
        Compute near-miss events (Time To Collision < threshold).
        
        Args:
            cars: List of Car objects
            timestamp: Current simulation time
            ttc_threshold: TTC threshold (s)
        
        Returns:
            Number of near-misses
        """
        near_misses = 0
        
        for i, car1 in enumerate(cars):
            for car2 in cars[i+1:]:
                # Compute distance
                dx = car2.x - car1.x
                dy = car2.y - car1.y
                distance = np.sqrt(dx**2 + dy**2)
                
                if distance < 10.0:  # Only check nearby cars
                    # Compute relative velocity
                    v1x = car1.velocity * np.cos(car1.yaw)
                    v1y = car1.velocity * np.sin(car1.yaw)
                    v2x = car2.velocity * np.cos(car2.yaw)
                    v2y = car2.velocity * np.sin(car2.yaw)
                    
                    rel_vx = v2x - v1x
                    rel_vy = v2y - v1y
                    
                    # Project relative velocity onto line of sight
                    if distance > 0.1:
                        rel_v = (dx * rel_vx + dy * rel_vy) / distance
                        
                        # Time to collision
                        if rel_v < 0:  # Approaching
                            ttc = distance / abs(rel_v)
                            if 0 < ttc < ttc_threshold:
                                near_misses += 1
        
        return near_misses

