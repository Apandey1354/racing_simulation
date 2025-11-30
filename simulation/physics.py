"""
Physics: Kinematic Bicycle Model for Car Dynamics
"""
import numpy as np


def update_car_dynamics(car, acceleration, steering_angle, dt):
    """
    Update car state using kinematic bicycle model.
    
    Args:
        car: Car object
        acceleration: Longitudinal acceleration (m/s^2)
        steering_angle: Steering angle delta (radians)
        dt: Time step (s)
    """
    # Update velocity
    car.velocity += acceleration * dt
    
    # Clamp velocity to [0, max_speed]
    max_speed = car.get_max_speed()
    car.velocity = np.clip(car.velocity, 0.0, max_speed)
    
    # Update position using kinematic bicycle model
    # x += v * cos(yaw) * dt
    # y += v * sin(yaw) * dt
    # yaw += (v / L) * tan(delta) * dt
    
    car.x += car.velocity * np.cos(car.yaw) * dt
    car.y += car.velocity * np.sin(car.yaw) * dt
    
    # Update heading
    if car.velocity > 0.01:  # Avoid division by zero
        car.yaw += (car.velocity / car.wheelbase) * np.tan(steering_angle) * dt
        # Normalize yaw to [0, 2*pi)
        car.yaw = car.yaw % (2 * np.pi)
    
    # Store acceleration
    car.acceleration = acceleration

