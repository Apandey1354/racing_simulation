# Multi-Car Racing Dynamics Simulation: Safety vs Speed Tradeoff

## Project Summary

This project simulates 10 autonomous cars racing around a closed-loop circuit track for 3 laps, using realistic agent-based driving models. The simulation evaluates how different speed settings and driving strategies (aggressive, balanced, cautious) affect accident rates and lap time efficiency.

**Key Features:**
- **Multiple Simulation Types**: Agent-Based, Discrete Event, Monte Carlo, and Markov Chain modeling
- **Realistic Physics**: IDM (Intelligent Driver Model) + Pure Pursuit steering
- **Multi-Lane Racing**: 5-lane system with intelligent lane-changing
- **Collision Detection**: Circle-based collision detection with elimination system
- **Comprehensive Analysis**: Best path identification, safety-speed tradeoff analysis, statistical results

## Table of Contents

1. [Installation](#installation)
2. [Quick Start](#quick-start)
3. [Simulation Types](#simulation-types)
4. [Configuration](#configuration)
5. [Output Files](#output-files)
6. [Code Organization](#code-organization)
7. [Technical Details](#technical-details)
8. [Examples](#examples)

## Installation

### Prerequisites
- Python 3.7 or higher
- pip package manager

### Setup

1. **Navigate to project directory**:
   ```bash
   cd racing_simulation
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

   This installs:
   - `numpy`: Numerical computations
   - `scipy`: Scientific computing (interpolation, optimization, statistics)
   - `matplotlib`: Plotting and visualization
   - `pyyaml`: Configuration file parsing
   - `tqdm`: Progress bars
   - `pygame`: Real-time visualization (optional)

## Quick Start

### Basic Usage

Run the default agent-based simulation:
```bash
python Phase2.py
```

Run with custom speed multiplier:
```bash
python Phase2.py --speed-multiplier 1.2
```

Run without visualization:
```bash
python Phase2.py --no-visualize
```

### Available Command-Line Options

```bash
python Phase2.py [OPTIONS]

Options:
  --config PATH              Path to configuration YAML file (default: config/parameters.yaml)
  --speed-multiplier FLOAT   Global speed multiplier (default: 1.0)
  --simulation-type TYPE     Simulation type: agent_based, discrete_event, monte_carlo, markov_chain (default: agent_based)
  --monte-carlo-runs INT     Number of runs for Monte Carlo simulation (default: 10)
  --no-plots                 Skip generating plots
  --no-visualize             Disable pygame real-time visualization
```

## Simulation Types

The project supports four different simulation modeling approaches:

### 1. Agent-Based Simulation (Default)

**Type**: `agent_based`

**Description**: Time-stepped simulation where each car is an independent agent with autonomous behavior. Cars make decisions based on their local environment (sensing nearby cars, track geometry).

**Use Case**: Standard racing simulation with realistic agent interactions.

**Example**:
```bash
python Phase2.py --simulation-type agent_based
```

**Characteristics**:
- Fixed time step (dt = 0.05s)
- Each car acts as independent agent
- Real-time decision making
- Suitable for detailed trajectory analysis

---

### 2. Discrete Event Simulation

**Type**: `discrete_event`

**Description**: Event-driven simulation using a priority queue. Events (collisions, lane changes, eliminations) are scheduled and processed in chronological order. More efficient for sparse event scenarios.

**Use Case**: When you want to focus on specific events rather than continuous updates.

**Example**:
```bash
python Phase2.py --simulation-type discrete_event
```

**Characteristics**:
- Event queue (priority queue by time)
- Events: collisions, lane changes, eliminations, updates
- More efficient for sparse events
- Better for analyzing event patterns

---

### 3. Monte Carlo Simulation

**Type**: `monte_carlo`

**Description**: Statistical simulation that runs multiple simulations with random parameter variations. Collects statistical results (mean, std, confidence intervals) across runs.

**Use Case**: Statistical analysis, uncertainty quantification, finding optimal parameters.

**Example**:
```bash
python Phase2.py --simulation-type monte_carlo --monte-carlo-runs 50
```

**Characteristics**:
- Multiple runs with random variations
- Statistical aggregation (mean, std, min, max)
- 95% confidence intervals
- Identifies robust parameter ranges

**Output**: 
- Statistics saved to `output/monte_carlo_results/monte_carlo_statistics.json`
- Individual run results available for analysis

---

### 4. Markov Chain Simulation

**Type**: `markov_chain`

**Description**: Probabilistic state transition modeling. Cars transition between states (aggressive, balanced, cautious, eliminated) based on performance metrics and transition probabilities.

**Use Case**: Modeling adaptive behavior, strategy changes based on performance.

**Example**:
```bash
python Phase2.py --simulation-type markov_chain
```

**Characteristics**:
- State space: {aggressive, balanced, cautious, eliminated}
- Transition probabilities depend on performance
- Adaptive strategy changes
- Models learning/adaptation behavior

**Transition Logic**:
- High collision rate → More likely to become cautious or eliminated
- Low collision rate + High speed → May become more aggressive
- Performance-based probability adjustments

---

## Configuration

Edit `config/parameters.yaml` to customize simulation parameters:

### Car Configuration
```yaml
num_cars: 10
strategy_distribution:
  aggressive: 3
  balanced: 4
  cautious: 3
```

### Track Configuration
```yaml
track:
  type: circuit
  radius_x: 80      # Track dimensions
  radius_y: 60
  width: 14
  num_lanes: 5      # Number of lanes
```

### Controller Parameters
```yaml
controller:
  desired_speed:
    aggressive: 25  # m/s
    balanced: 18
    cautious: 14
  a_max: 2.5        # Maximum acceleration (m/s²)
  b_max: 4.5        # Maximum braking (m/s²)
  min_gap: 2.0      # Minimum gap to leading car (m)
  reaction_time: 0.3
  lookahead_distance: 8.0
  wheelbase: 2.5
```

### Simulation Parameters
```yaml
simulation:
  laps: 3                    # Target number of laps
  dt: 0.05                   # Time step (s)
  collision_radius: 3.0      # Collision detection radius (m)
  time_limit: 300.0          # Maximum simulation time (s)
  near_miss_ttc_threshold: 2.0
  elimination:
    enabled: true
    elimination_chance: 6    # Threshold (1-10, if roll < 6, eliminate)
```

## Output Files

All outputs are organized in `output/run_YYYYMMDD_HHMM/`:

```
output/
└── run_YYYYMMDD_HHMM/
    ├── telemetry/              # Raw telemetry CSV files
    │   ├── car_0.csv
    │   ├── car_1.csv
    │   └── ... (one per car)
    │
    ├── visualizations/         # All plots and charts
    │   ├── lap_times.png
    │   ├── speed_traces.png
    │   ├── collisions_per_car.png
    │   ├── safety_vs_speed.png
    │   └── collision_heatmap.png
    │
    ├── results/                 # Summary results
    │   ├── results_summary.json
    │   └── results_summary.txt
    │
    └── best_path/               # Optimal path analysis
        ├── best_path_summary.json
        ├── best_path_trajectory.csv
        └── best_path_analysis.png
```

### Telemetry Data
Each car's CSV file contains:
- `timestamp`: Simulation time
- `car_id`: Car identifier
- `x, y`: Position coordinates
- `yaw`: Heading angle (radians)
- `velocity`: Speed (m/s)
- `acceleration`: Acceleration (m/s²)
- `lap`: Current lap number
- `s_position`: Arc-length position on track
- `collision_flag`: Whether collision occurred this step

### Visualizations
- **lap_times.png**: Lap time distribution per car
- **speed_traces.png**: Speed profiles over time
- **collisions_per_car.png**: Collision count per car
- **safety_vs_speed.png**: Safety-speed tradeoff scatter plot
- **collision_heatmap.png**: 2D spatial distribution of collisions

### Best Path Analysis
Identifies the best performing car based on:
- Lowest average lap time
- Fewest collisions
- Combined score: `lap_time + collisions × 5 seconds`

## Code Organization

The project is organized into modular components:

```
racing_simulation/
├── Phase2.py                    # Entry point
├── requirements.txt             # Dependencies
├── README.md                    # This file
│
├── simulation/                  # Core simulation modules
│   ├── __init__.py
│   ├── simulation.py           # Agent-based simulation engine
│   ├── simulation_types.py     # Simulation type enumeration
│   ├── discrete_event.py       # Discrete event simulation
│   ├── monte_carlo.py           # Monte Carlo simulation
│   ├── markov_chain.py          # Markov Chain simulation
│   ├── car.py                   # Car model (agent)
│   ├── track.py                 # Track geometry
│   ├── controller.py            # IDM + Pure Pursuit controller
│   ├── physics.py               # Kinematic bicycle model
│   ├── collision.py             # Collision detection
│   └── visualization.py         # Pygame visualization
│
├── config/                      # Configuration
│   └── parameters.yaml          # Simulation parameters
│
├── analysis/                    # Analysis tools
│   ├── __init__.py
│   ├── plot_results.py          # Result visualization
│   ├── heatmap.py               # Collision heatmap
│   ├── best_path.py             # Best path analysis
│   └── results_summary.py       # Results summary generation
│
└── output/                      # Output directory (auto-generated)
    └── README.md                # Output structure documentation
```

### Code Quality Features

✅ **Modular Design**: Each component is in its own module
✅ **Well-Documented**: All classes and functions have docstrings
✅ **Type Hints**: Function signatures include type information
✅ **Clear Naming**: Descriptive variable and function names
✅ **Error Handling**: Graceful error handling with informative messages
✅ **Easy to Extend**: New simulation types can be added easily

## Technical Details

### Models Used

#### 1. IDM (Intelligent Driver Model)
Longitudinal control for acceleration/braking:
```
a = a_max * (1 - (v/v0)^δ - (s*/s)²)
```
Where:
- `s* = s0 + v*T + (v*dv)/(2*√(a_max*b_max))` (desired gap)
- `v0`: Desired speed
- `s`: Current gap to leading car
- `dv`: Relative velocity

#### 2. Pure Pursuit Steering
Lateral control for steering:
```
δ = atan(2*L*sin(α) / lookahead)
```
Where:
- `α`: Angle to target point
- `L`: Wheelbase
- `lookahead`: Lookahead distance

#### 3. Kinematic Bicycle Model
Car dynamics:
```
x += v*cos(θ)*dt
y += v*sin(θ)*dt
θ += (v/L)*tan(δ)*dt
v += a*dt
```

#### 4. Collision Detection
Circle-based collision:
```
distance(car1, car2) < collision_radius
```

### Lane Changing Logic

Cars change lanes when:
1. Leading car is slower
2. Target lane is clear (no cars in danger zone)
3. Lane change timer has expired (prevents rapid changes)

### Elimination System

Cars are eliminated based on:
- **Random Chance**: Roll 1-10, eliminate if roll < threshold (default: 6)
- **Collision Count**: Tracks cumulative collisions
- **Collision Severity**: Tracks impact intensity

## Examples

### Example 1: Standard Agent-Based Simulation
```bash
python Phase2.py --speed-multiplier 1.0
```

### Example 2: Discrete Event Simulation
```bash
python Phase2.py --simulation-type discrete_event --no-visualize
```

### Example 3: Monte Carlo with 100 Runs
```bash
python Phase2.py --simulation-type monte_carlo --monte-carlo-runs 100 --no-visualize
```

### Example 4: Markov Chain with Visualization
```bash
python Phase2.py --simulation-type markov_chain --speed-multiplier 1.1
```

### Example 5: Fast Simulation (No Plots, No Visualization)
```bash
python Phase2.py --no-plots --no-visualize --simulation-type agent_based
```

## Real-Time Visualization

The simulation includes an optional **pygame-based real-time visualization**:

**Features**:
- Track with multiple lanes
- Color-coded cars by strategy:
  - 🔴 **Red** = Aggressive
  - 🔵 **Blue** = Balanced
  - 🟢 **Green** = Cautious
- Car ID numbers and speed indicators
- Collision flash effects
- Real-time statistics panel
- Eliminated cars shown in gray with 'X' mark

**Controls**:
- Close window or press **ESC** to stop simulation

**Note**: Visualization runs at 60 FPS and may slow down simulation for large numbers of cars.

## Troubleshooting

### Common Issues

1. **Import errors**
   ```bash
   pip install -r requirements.txt
   ```

2. **YAML parsing errors**
   - Check `config/parameters.yaml` syntax
   - Ensure proper indentation (YAML is space-sensitive)

3. **No plots generated**
   - Check matplotlib backend
   - Use `--no-plots` to skip if problematic

4. **Simulation too slow**
   - Reduce `num_cars` in config
   - Increase `dt` (time step) in config
   - Disable visualization: `--no-visualize`

5. **Pygame errors**
   - Install pygame: `pip install pygame`
   - Or run without visualization: `--no-visualize`

## Project Requirements Fulfillment

This project fulfills all requirements:

✅ **Code Organization**: Modular, well-commented, easy to run
✅ **Agent-Based Simulation**: Each car is an independent agent
✅ **Discrete Event Simulation**: Event-driven approach with priority queue
✅ **Monte Carlo Simulation**: Statistical analysis with multiple runs
✅ **Markov Chain Modeling**: Probabilistic state transitions
✅ **Comprehensive Documentation**: README, docstrings, comments
✅ **Easy to Use**: Simple command-line interface
✅ **Rich Outputs**: Visualizations, telemetry, analysis

## Citation

If you use this simulation in your research, please cite:

```
Multi-Car Racing Dynamics Simulation: Safety vs Speed Tradeoff
Anish Pandey, Dikshya Giri
Caldwell University
```

## License

This project is provided as-is for educational and research purposes.

## Contact

For questions or issues, please refer to the project documentation or contact the authors.

---

**Happy Racing! 🏎️**

