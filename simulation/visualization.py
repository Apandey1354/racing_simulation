"""
Pygame Visualization: Real-time Racing Simulation Display
"""
import pygame
import numpy as np
import sys


class PygameVisualization:
    """
    Real-time pygame visualization for the racing simulation.
    """
    
    def __init__(self, track, cars, width=1200, height=800, scale=5.0):
        """
        Initialize pygame visualization.
        
        Args:
            track: Track object
            cars: List of Car objects
            width: Window width (pixels)
            height: Window height (pixels)
            scale: Pixels per meter
        """
        self.track = track
        self.cars = cars
        self.scale = scale
        self.width = width
        self.height = height
        
        # Initialize pygame
        try:
            pygame.init()
            # Set environment variable to prevent pygame from trying to use audio
            import os
            os.environ['SDL_AUDIODRIVER'] = 'dummy'
            
            self.screen = pygame.display.set_mode((width, height))
            pygame.display.set_caption("Multi-Car Racing Simulation")
            self.clock = pygame.time.Clock()
            self.font = pygame.font.Font(None, 24)
            self.small_font = pygame.font.Font(None, 18)
            print(f"Pygame window created: {width}x{height}")
            
            # Force initial display update
            pygame.display.flip()
        except Exception as e:
            print(f"Error initializing pygame: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        # Colors
        self.colors = {
            'track_outer': (50, 50, 50),
            'track_inner': (100, 100, 100),
            'track_centerline': (150, 150, 150),
            'track_surface': (40, 40, 40),
            'aggressive': (255, 50, 50),    # Red
            'balanced': (50, 150, 255),     # Blue
            'cautious': (50, 255, 50),      # Green
            'collision': (255, 255, 0),    # Yellow
            'background': (20, 20, 20),
            'text': (255, 255, 255),
            'text_bg': (0, 0, 0, 128)
        }
        
        # Compute track bounds and center for view
        self._compute_view_transform()
        
        # Collision indicators (fade out over time)
        self.collision_indicators = []
        
        # Running stats
        self.total_collisions = 0
        self.timestamp = 0.0
    
    def _compute_view_transform(self):
        """Compute transformation to center and scale track in view."""
        # Get track bounds
        track_x = self.track.centerline_x
        track_y = self.track.centerline_y
        
        min_x, max_x = np.min(track_x), np.max(track_x)
        min_y, max_y = np.min(track_y), np.max(track_y)
        
        # Add padding
        padding = 20
        track_width = max_x - min_x + 2 * padding
        track_height = max_y - min_y + 2 * padding
        
        # Compute scale to fit
        scale_x = self.width / track_width
        scale_y = self.height / track_height
        self.view_scale = min(scale_x, scale_y) * 0.9  # 90% to add margin
        
        # Center point
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        
        # Transform: world to screen
        self.offset_x = self.width / 2 - center_x * self.view_scale
        self.offset_y = self.height / 2 - center_y * self.view_scale
    
    def world_to_screen(self, x, y):
        """Convert world coordinates to screen coordinates."""
        screen_x = x * self.view_scale + self.offset_x
        screen_y = y * self.view_scale + self.offset_y
        return int(screen_x), int(screen_y)
    
    def draw_track(self):
        """Draw the track (boundaries, lanes, and centerline)."""
        # Get track boundaries
        inner_x, inner_y, outer_x, outer_y = self.track.get_track_boundaries()
        
        # Draw track surface (filled polygon)
        points_outer = [self.world_to_screen(x, y) for x, y in zip(outer_x, outer_y)]
        points_inner = [self.world_to_screen(x, y) for x, y in zip(inner_x, inner_y)]
        
        # Draw outer boundary
        if len(points_outer) > 2:
            pygame.draw.polygon(self.screen, self.colors['track_surface'], points_outer)
            pygame.draw.lines(self.screen, self.colors['track_outer'], True, points_outer, 2)
        
        # Draw inner boundary
        if len(points_inner) > 2:
            pygame.draw.lines(self.screen, self.colors['track_inner'], True, points_inner, 2)
        
        # Draw lane markings (dashed lines between lanes)
        if hasattr(self.track, 'lanes') and len(self.track.lanes) > 0:
            for lane_id in range(len(self.track.lanes) - 1):
                lane = self.track.lanes[lane_id]
                lane_points = [self.world_to_screen(x, y) 
                              for x, y in zip(lane['x'], lane['y'])]
                # Draw dashed line (every 10th point)
                if len(lane_points) > 10:
                    for i in range(0, len(lane_points) - 1, 10):
                        if i + 1 < len(lane_points):
                            pygame.draw.line(self.screen, (100, 100, 100), 
                                           lane_points[i], lane_points[i+1], 1)
        
        # Draw centerline (lane 2, middle lane)
        if hasattr(self.track, 'lanes') and len(self.track.lanes) >= 3:
            center_lane = self.track.lanes[2]  # Middle lane
            centerline_points = [self.world_to_screen(x, y) 
                                for x, y in zip(center_lane['x'], center_lane['y'])]
            if len(centerline_points) > 1:
                pygame.draw.lines(self.screen, self.colors['track_centerline'], False, 
                                centerline_points, 1)
        else:
            # Fallback to original centerline
            centerline_points = [self.world_to_screen(x, y) 
                                for x, y in zip(self.track.centerline_x, self.track.centerline_y)]
            if len(centerline_points) > 1:
                pygame.draw.lines(self.screen, self.colors['track_centerline'], False, 
                                centerline_points, 1)
    
    def draw_car(self, car):
        """Draw a single car."""
        # Check if car is eliminated
        if car.eliminated:
            # Draw eliminated cars in gray, semi-transparent
            color = (100, 100, 100)  # Gray
            alpha = 128  # Semi-transparent
        else:
            # Get car color based on strategy
            color = self.colors.get(car.strategy_type, self.colors['balanced'])
            alpha = 255  # Fully opaque
            
            # If car just collided, flash yellow
            if car.collision_flag:
                color = self.colors['collision']
        
        # Car dimensions (in meters, then scaled)
        car_length = 4.0 * self.view_scale
        car_width = 2.0 * self.view_scale
        
        # Car position
        car_x, car_y = self.world_to_screen(car.x, car.y)
        
        # Create car rectangle
        car_rect = pygame.Surface((car_length, car_width), pygame.SRCALPHA)
        if car.eliminated:
            # Draw eliminated car with transparency
            car_rect.set_alpha(alpha)
            pygame.draw.rect(car_rect, color, (0, 0, car_length, car_width))
            # Draw X mark on eliminated cars
            pygame.draw.line(car_rect, (255, 0, 0), (0, 0), (car_length, car_width), 2)
            pygame.draw.line(car_rect, (255, 0, 0), (car_length, 0), (0, car_width), 2)
        else:
            pygame.draw.rect(car_rect, color, (0, 0, car_length, car_width))
        
        # Draw direction indicator (front of car)
        front_x = car_length * 0.4
        front_y = car_width / 2
        pygame.draw.circle(car_rect, (255, 255, 255), (int(front_x), int(front_y)), 3)
        
        # Rotate car based on yaw
        angle_deg = np.degrees(car.yaw)
        rotated_car = pygame.transform.rotate(car_rect, -angle_deg)
        
        # Get rotated rect center
        rot_rect = rotated_car.get_rect(center=(car_x, car_y))
        
        # Draw car
        self.screen.blit(rotated_car, rot_rect)
        
        # Draw car ID and lane
        if car.eliminated:
            id_text = self.small_font.render(f"{car.car_id} ELIM", True, (255, 0, 0))
        else:
            id_text = self.small_font.render(f"{car.car_id} L{int(car.lane)}", True, self.colors['text'])
        id_rect = id_text.get_rect(center=(car_x, car_y - car_width - 10))
        self.screen.blit(id_text, id_rect)
        
        # Draw speed indicator (small bar) - only for active cars
        if not car.eliminated:
            max_speed = car.get_max_speed()
            speed_ratio = min(car.velocity / max_speed, 1.0) if max_speed > 0 else 0
            bar_length = 20
            bar_height = 3
            bar_x = car_x - bar_length / 2
            bar_y = car_y + car_width / 2 + 5
            
            # Background bar
            pygame.draw.rect(self.screen, (50, 50, 50), 
                            (bar_x, bar_y, bar_length, bar_height))
            # Speed bar (green to red)
            speed_color = (int(255 * (1 - speed_ratio)), int(255 * speed_ratio), 0)
            pygame.draw.rect(self.screen, speed_color, 
                            (bar_x, bar_y, int(bar_length * speed_ratio), bar_height))
    
    def draw_collision_indicator(self, x, y):
        """Draw a collision indicator that fades out."""
        screen_x, screen_y = self.world_to_screen(x, y)
        # Draw explosion effect
        for radius in [15, 25, 35]:
            alpha = max(0, 255 - radius * 5)
            color = (255, 200, 0, alpha)
            # Create surface with alpha
            surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, color, (radius, radius), radius)
            self.screen.blit(surf, (screen_x - radius, screen_y - radius))
    
    def draw_stats(self, collisions, near_misses):
        """Draw statistics overlay."""
        # Background panel
        panel_width = 250
        panel_height = 200
        panel_surface = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        panel_surface.fill((0, 0, 0, 200))
        self.screen.blit(panel_surface, (10, 10))
        
        # Stats text
        y_offset = 20
        line_height = 25
        
        # Count active vs eliminated cars
        active_cars = [c for c in self.cars if not c.eliminated]
        eliminated_count = len(self.cars) - len(active_cars)
        
        stats = [
            f"Time: {self.timestamp:.1f}s",
            f"Collisions: {collisions}",
            f"Near Misses: {near_misses}",
            f"Active Cars: {len(active_cars)}",
            f"Eliminated: {eliminated_count}",
            "",
            "Strategy Colors:",
            "Red = Aggressive",
            "Blue = Balanced",
            "Green = Cautious"
        ]
        
        for i, stat in enumerate(stats):
            if stat:
                text = self.small_font.render(stat, True, self.colors['text'])
                self.screen.blit(text, (20, 10 + y_offset + i * line_height))
        
        # Lap counts
        lap_y = 10 + y_offset + len(stats) * line_height + 10
        lap_text = self.font.render("Lap Counts:", True, self.colors['text'])
        self.screen.blit(lap_text, (20, lap_y))
        
        # Count active vs eliminated cars
        active_cars = [c for c in self.cars if not c.eliminated]
        eliminated_count = len(self.cars) - len(active_cars)
        
        # Show top 5 cars by lap count (only active cars)
        active_cars = [c for c in self.cars if not c.eliminated]
        sorted_cars = sorted(active_cars, key=lambda c: (c.lap_count, -c.s_position), reverse=True)
        for i, car in enumerate(sorted_cars[:5]):
            lap_y += line_height
            color = self.colors.get(car.strategy_type, self.colors['balanced'])
            lap_info = f"Car {car.car_id}: {car.lap_count} laps"
            text = self.small_font.render(lap_info, True, color)
            self.screen.blit(text, (30, lap_y))
    
    def update(self, timestamp, collisions, near_misses, dt=0.05):
        """
        Update visualization.
        
        Args:
            timestamp: Current simulation time
            collisions: List of new collision events
            near_misses: Number of near misses
            dt: Time step for aging collision indicators
        """
        self.timestamp = timestamp
        self.total_collisions += len(collisions)
        
        # Add collision indicators
        for collision in collisions:
            self.collision_indicators.append({
                'x': collision['x'],
                'y': collision['y'],
                'age': 0.0
            })
        
        # Update collision indicator ages
        for indicator in self.collision_indicators[:]:
            indicator['age'] += dt
            if indicator['age'] > 1.0:  # Fade out after 1 second
                self.collision_indicators.remove(indicator)
    
    def render(self, collisions, near_misses):
        """
        Render one frame.
        
        Args:
            collisions: Total collision count
            near_misses: Total near miss count
        """
        try:
            # Clear screen
            self.screen.fill(self.colors['background'])
            
            # Draw track
            self.draw_track()
            
            # Draw collision indicators
            for indicator in self.collision_indicators:
                self.draw_collision_indicator(indicator['x'], indicator['y'])
            
            # Draw all cars
            for car in self.cars:
                self.draw_car(car)
            
            # Draw stats
            self.draw_stats(collisions, near_misses)
            
            # Update display
            pygame.display.flip()
        except Exception as e:
            print(f"Error in render: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def handle_events(self):
        """
        Handle pygame events (quit, etc.).
        
        Returns:
            True if should continue, False if should quit
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
        return True
    
    def tick(self, fps=60):
        """Tick the clock (limit FPS)."""
        self.clock.tick(fps)
    
    def quit(self):
        """Clean up pygame."""
        pygame.quit()

