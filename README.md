# Accessible Campus Navigator

A desktop application that helps students find **accessible routes** between locations on a fictional college campus.

> **Note:** The campus used in this application is entirely fictional and created for demonstration purposes only.

## Features

- **Standard & Accessible Routing** — find shortest paths that respect wheelchair, ramp, elevator, and stair-avoidance requirements.
- **BFS & Dijkstra Algorithms** — demonstrates both unweighted (BFS) and weighted (Dijkstra) shortest-path algorithms.
- **Visual Campus Map** — interactive Tkinter canvas showing locations, edges, and highlighted routes.
- **Obstacle Reporting** — report and view active accessibility issues (e.g., broken ramp, elevator out of service).
- **Statistics Dashboard** — route distance, estimated travel time, and accessibility information at a glance.
- **Fully Offline** — no internet connection, external APIs, or third-party packages required.

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3 |
| GUI | Tkinter + ttk |
| Data Format | JSON |
| Algorithms | BFS (collections.deque), Dijkstra (heapq) |
| Testing | unittest |

## Project Structure

```
AccessibleCampusNavigator/
│
├── main.py                    # Application entry point
├── campus_data.json           # Fictional campus graph data
├── obstacles.json             # Reported accessibility obstacles
├── README.md
├── requirements.txt
│
├── core/                      # Graph & algorithm logic
│   ├── graph.py               # Campus graph data structure
│   ├── algorithms.py          # BFS and Dijkstra implementations
│   └── accessibility.py       # Accessibility mode filters
│
├── services/                  # Data and file handling
│   ├── data_manager.py        # Load/save campus data
│   └── obstacle_manager.py    # Load/save obstacle reports
│
├── gui/                       # Tkinter user interface
│   ├── main_window.py         # Main window and dashboard
│   ├── map_view.py            # Canvas-based campus map
│   └── dialogs.py             # Help and About dialogs
│
└── tests/                     # Unit test suite
    ├── test_graph.py
    ├── test_algorithms.py
    └── test_accessibility.py
```

## How to Run

```bash
# Run the application
python main.py

# Run all unit tests
python -m unittest discover -s tests
```

## Requirements

**No third-party packages required.** This project uses only the Python standard library.

See `requirements.txt` for the full list of standard library modules used.

## Accessibility Modes

| Mode | Behaviour |
|------|-----------|
| Standard | Normal shortest path, no filtering |
| Wheelchair Accessible | Avoids stairs, prefers ramps and elevators |
| Avoid Stairs | Excludes all stair edges |
| Prefer Ramps | Lowers cost of ramp-equipped edges |
| Require Elevator | Only uses paths with elevator access between floors |

## Academic Context

This project was developed as a mini project for academic evaluation, demonstrating:

1. Python programming
2. Graph data structures
3. BFS algorithm
4. Dijkstra's shortest-path algorithm
5. JSON file handling
6. Tkinter GUI development
7. File handling and exception handling
8. Basic software architecture
9. Unit testing

## License

Academic project — for educational purposes only.
