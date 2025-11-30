"""
Track System: Racing Circuit Track with Turns and Curves
"""
import numpy as np
from scipy.interpolate import interp1d, CubicSpline
from scipy.optimize import minimize_scalar
try:
    from scipy.ndimage import gaussian_filter1d
    HAS_SCIPY_NDIMAGE = True
except ImportError:
    HAS_SCIPY_NDIMAGE = False


class Track:
    """
    Represents a closed-loop racing circuit track with turns, curves, and straights.
    """
    
    def __init__(self, radius_x=60, radius_y=40, width=12, num_points=1000, num_lanes=5):
        """
        Initialize racing circuit track.
        
        Args:
            radius_x: Horizontal scale factor (meters)
            radius_y: Vertical scale factor (meters)
            width: Track width (meters)
            num_points: Number of points for discretization
            num_lanes: Number of lanes (default: 5)
        """
        self.radius_x = radius_x
        self.radius_y = radius_y
        self.width = width
        self.num_points = num_points
        self.num_lanes = num_lanes
        self.lane_width = width / num_lanes
        
        # Generate parametric curve points
        self._generate_centerline()
        self._compute_arc_lengths()
        # Generate lanes after arc lengths are computed
        self._generate_lanes()
    
    def _generate_centerline(self):
        """Generate centerline points for a smooth, non-overlapping racing circuit."""
        # Define key waypoints for the track (ensures no overlap)
        # These define a smooth racing circuit with corners and elevation changes
        
        scale_x = self.radius_x
        scale_y = self.radius_y
        
        # Define waypoints in order (x, y) - creates a closed loop
        waypoints = np.array([
            [scale_x * 1.0, scale_y * 0.0],      # Start/Finish
            [scale_x * 0.8, scale_y * 0.3],      # Turn 1 entry
            [scale_x * 0.4, scale_y * 0.6],      # Turn 1 apex
            [scale_x * 0.0, scale_y * 0.8],      # Turn 1 exit
            [scale_x * -0.4, scale_y * 0.9],     # Back straight start
            [scale_x * -0.8, scale_y * 0.85],   # Back straight middle
            [scale_x * -1.0, scale_y * 0.7],    # Turn 2 entry (hairpin)
            [scale_x * -0.9, scale_y * 0.4],    # Turn 2 apex
            [scale_x * -0.7, scale_y * 0.2],    # Turn 2 exit
            [scale_x * -0.5, scale_y * 0.0],    # Short straight
            [scale_x * -0.3, scale_y * -0.2],   # Turn 3 entry
            [scale_x * -0.1, scale_y * -0.4],   # Turn 3 apex
            [scale_x * 0.1, scale_y * -0.5],    # Turn 3 exit
            [scale_x * 0.4, scale_y * -0.6],    # Turn 4 entry
            [scale_x * 0.7, scale_y * -0.7],    # Turn 4 apex
            [scale_x * 0.9, scale_y * -0.6],    # Turn 4 exit
            [scale_x * 1.0, scale_y * -0.3],    # Final turn entry
            [scale_x * 1.0, scale_y * -0.1],    # Final turn exit
        ])
        
        # Close the loop by adding start point at the end
        waypoints_closed = np.vstack([waypoints, waypoints[0:1]])
        
        # Parameterize by arc length
        waypoint_distances = np.zeros(len(waypoints_closed))
        for i in range(1, len(waypoints_closed)):
            dx = waypoints_closed[i, 0] - waypoints_closed[i-1, 0]
            dy = waypoints_closed[i, 1] - waypoints_closed[i-1, 1]
            waypoint_distances[i] = waypoint_distances[i-1] + np.sqrt(dx**2 + dy**2)
        
        # Normalize to [0, 1]
        waypoint_params = waypoint_distances / waypoint_distances[-1]
        
        # Create cubic splines for smooth interpolation
        cs_x = CubicSpline(waypoint_params, waypoints_closed[:, 0], bc_type='periodic')
        cs_y = CubicSpline(waypoint_params, waypoints_closed[:, 1], bc_type='periodic')
        
        # Generate points along the spline
        t_smooth = np.linspace(0, 1, self.num_points, endpoint=False)
        self.centerline_x = cs_x(t_smooth)
        self.centerline_y = cs_y(t_smooth)
        
        # Light smoothing to ensure perfect smoothness
        if HAS_SCIPY_NDIMAGE:
            self.centerline_x = gaussian_filter1d(self.centerline_x, sigma=1.0)
            self.centerline_y = gaussian_filter1d(self.centerline_y, sigma=1.0)
        else:
            # Simple smoothing using moving average
            window = 3
            self.centerline_x = np.convolve(self.centerline_x, np.ones(window)/window, mode='same')
            self.centerline_y = np.convolve(self.centerline_y, np.ones(window)/window, mode='same')
        
        # Store parameter values
        self.t_params = np.linspace(0, 2 * np.pi, self.num_points, endpoint=False)
        
        # Compute total track length
        self.total_length = self._compute_total_length()
    
    def _compute_total_length(self):
        """Compute total track length using numerical integration."""
        dx = np.diff(self.centerline_x)
        dy = np.diff(self.centerline_y)
        ds = np.sqrt(dx**2 + dy**2)
        return np.sum(ds)
    
    def _compute_arc_lengths(self):
        """Precompute cumulative arc lengths for each point."""
        dx = np.diff(self.centerline_x)
        dy = np.diff(self.centerline_y)
        ds = np.sqrt(dx**2 + dy**2)
        
        # Cumulative arc length from start
        self.arc_lengths = np.concatenate([[0], np.cumsum(ds)])
        
        # Create interpolation functions for x(s) and y(s)
        self.x_interp = interp1d(self.arc_lengths, self.centerline_x, 
                                 kind='linear', bounds_error=False, 
                                 fill_value='extrapolate')
        self.y_interp = interp1d(self.arc_lengths, self.centerline_y, 
                                 kind='linear', bounds_error=False, 
                                 fill_value='extrapolate')
    
    def _generate_lanes(self):
        """Generate lane centerlines (5 lanes total)."""
        self.lanes = []
        
        # Compute normal vectors for each point on centerline
        dx = np.diff(self.centerline_x)
        dy = np.diff(self.centerline_y)
        ds = np.sqrt(dx**2 + dy**2)
        
        # Normalize tangent vectors
        tangent_x = dx / (ds + 1e-6)
        tangent_y = dy / (ds + 1e-6)
        
        # Rotate 90 degrees to get normal (pointing outward from center)
        normal_x = -tangent_y
        normal_y = tangent_x
        
        # Extend to full length
        normal_x = np.concatenate([normal_x, [normal_x[-1]]])
        normal_y = np.concatenate([normal_y, [normal_y[-1]]])
        
        # Generate lanes (0 = innermost, num_lanes-1 = outermost)
        for lane_id in range(self.num_lanes):
            # Lane offset from centerline
            # Lane 0 is at -width/2 + lane_width/2 (innermost)
            # Lane num_lanes-1 is at width/2 - lane_width/2 (outermost)
            offset = -self.width / 2 + self.lane_width / 2 + lane_id * self.lane_width
            
            # Generate lane centerline
            lane_x = self.centerline_x + offset * normal_x
            lane_y = self.centerline_y + offset * normal_y
            
            # Create interpolation functions for this lane
            lane_x_interp = interp1d(self.arc_lengths, lane_x, 
                                     kind='linear', bounds_error=False, 
                                     fill_value='extrapolate')
            lane_y_interp = interp1d(self.arc_lengths, lane_y, 
                                     kind='linear', bounds_error=False, 
                                     fill_value='extrapolate')
            
            self.lanes.append({
                'x': lane_x,
                'y': lane_y,
                'x_interp': lane_x_interp,
                'y_interp': lane_y_interp
            })
    
    def get_target_point(self, s, lookahead_distance, lane=None):
        """
        Get target point on specified lane at arc-length s + lookahead_distance.
        
        Args:
            s: Current arc-length position (meters)
            lookahead_distance: Distance ahead to look (meters)
            lane: Lane number (0 to num_lanes-1). If None, uses centerline.
        
        Returns:
            (target_x, target_y): Target point coordinates
        """
        # Normalize s to be within [0, total_length)
        s = s % self.total_length
        
        # Compute target arc-length
        target_s = (s + lookahead_distance) % self.total_length
        
        # Get target point on specified lane or centerline
        if lane is not None and 0 <= lane < self.num_lanes:
            target_x = self.lanes[lane]['x_interp'](target_s)
            target_y = self.lanes[lane]['y_interp'](target_s)
        else:
            # Default to centerline
            target_x = self.x_interp(target_s)
            target_y = self.y_interp(target_s)
        
        return target_x, target_y
    
    def project_car_position(self, x, y):
        """
        Project car position (x, y) onto track centerline.
        Returns the arc-length s along the centerline.
        
        Args:
            x: Car x position
            y: Car y position
        
        Returns:
            s: Arc-length position along centerline (meters)
        """
        # Find closest point on centerline
        distances = np.sqrt((self.centerline_x - x)**2 + (self.centerline_y - y)**2)
        closest_idx = np.argmin(distances)
        
        # Get arc-length at closest point
        s = self.arc_lengths[closest_idx]
        
        # Refine by checking nearby points for better accuracy
        # Use a small neighborhood around closest point
        search_range = min(50, len(self.arc_lengths) // 10)
        start_idx = max(0, closest_idx - search_range)
        end_idx = min(len(self.arc_lengths), closest_idx + search_range)
        
        # Find minimum distance in neighborhood
        local_distances = np.sqrt(
            (self.centerline_x[start_idx:end_idx] - x)**2 + 
            (self.centerline_y[start_idx:end_idx] - y)**2
        )
        local_closest = np.argmin(local_distances)
        refined_idx = start_idx + local_closest
        
        return self.arc_lengths[refined_idx]
    
    def get_centerline_points(self):
        """Get all centerline points for visualization."""
        return self.centerline_x, self.centerline_y
    
    def get_track_boundaries(self):
        """
        Get inner and outer track boundaries.
        Returns (inner_x, inner_y, outer_x, outer_y)
        """
        # Compute normal vectors (pointing outward)
        dx = np.diff(self.centerline_x)
        dy = np.diff(self.centerline_y)
        ds = np.sqrt(dx**2 + dy**2)
        
        # Normalize tangent vectors
        tangent_x = dx / (ds + 1e-6)
        tangent_y = dy / (ds + 1e-6)
        
        # Rotate 90 degrees to get normal (outward)
        normal_x = -tangent_y
        normal_y = tangent_x
        
        # Extend to full length
        normal_x = np.concatenate([normal_x, [normal_x[-1]]])
        normal_y = np.concatenate([normal_y, [normal_y[-1]]])
        
        # Compute boundaries
        half_width = self.width / 2
        inner_x = self.centerline_x - half_width * normal_x
        inner_y = self.centerline_y - half_width * normal_y
        outer_x = self.centerline_x + half_width * normal_x
        outer_y = self.centerline_y + half_width * normal_y
        
        return inner_x, inner_y, outer_x, outer_y

