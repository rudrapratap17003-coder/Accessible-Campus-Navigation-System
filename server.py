"""
server.py — Localhost Web Server for Accessible Campus Navigator
==================================================================
Runs an offline-first HTTP server on http://localhost:8000 using only
Python's built-in `http.server` module (strictly no external web frameworks).

REST Endpoints:
    GET  /                          - Serve web/index.html dashboard
    GET  /api/campus                - Campus locations, pathways & metadata
    GET  /api/route                 - Compute accessible route (Dijkstra / BFS / Comparison)
    GET  /api/obstacles             - List active reported path disruptions
    POST /api/obstacles             - Report a new temporary accessibility obstacle
    POST /api/obstacles/resolve     - Mark a reported obstacle as resolved
    GET  /api/report                - JAIN Global Campus Data Audit Report

To run:
    python server.py
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import sys

from services.data_manager import load_campus_data, build_campus_graph
from services.obstacle_manager import ObstacleManager
from core.algorithms import dijkstra_shortest_path, bfs_shortest_path
from core.accessibility import AccessibilityMode, get_accessibility_badge
from generate_campus_report import generate_campus_report

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000


class CampusNavigatorHandler(BaseHTTPRequestHandler):
    """Request handler providing REST API and serving the single-page dashboard."""

    # Cached campus graph & data
    campus_graph = None
    campus_raw_data = None
    obstacle_mgr = None

    @classmethod
    def initialize_services(cls):
        """Pre-load campus graph and obstacle manager services."""
        cls.campus_graph, _ = build_campus_graph()
        cls.campus_raw_data = load_campus_data()
        cls.obstacle_mgr = ObstacleManager()

    def do_GET(self):
        """Handle GET requests for pages and API endpoints."""
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # 1. Dashboard UI
        if path in ("/", "/index.html"):
            self._serve_file("web/index.html", "text/html; charset=utf-8")

        # 2. Campus Data API
        elif path == "/api/campus":
            self._send_json(self.campus_raw_data)

        # 3. Pathfinding Route API
        elif path == "/api/route":
            self._handle_route_query(query)

        # 4. Obstacles List API
        elif path == "/api/obstacles":
            active = self.obstacle_mgr.get_active_obstacles()
            all_obs = self.obstacle_mgr.load_all_obstacles()
            self._send_json({
                "active_obstacles": active,
                "total_obstacles": len(all_obs),
            })

        # 5. Audit Report API
        elif path == "/api/report":
            report_text = generate_campus_report()
            self._send_text(report_text, "text/plain; charset=utf-8")

        else:
            self.send_error(404, "Endpoint Not Found")

    def do_POST(self):
        """Handle POST requests for reporting and resolving obstacles."""
        parsed = urlparse(self.path)
        path = parsed.path

        content_len = int(self.headers.get("Content-Length", 0))
        post_body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"

        try:
            body = json.loads(post_body)
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON body"}, status=400)
            return

        if path == "/api/obstacles":
            source = body.get("source")
            destination = body.get("destination")
            obstacle_type = body.get("obstacle_type", "hazard")
            description = body.get("description", "Pathway blocked")
            reported_by = body.get("reported_by", "Campus User")

            if not source or not destination:
                self._send_json({"error": "Both 'source' and 'destination' are required"}, status=400)
                return

            new_record = self.obstacle_mgr.report_obstacle(
                source=source,
                destination=destination,
                obstacle_type=obstacle_type,
                description=description,
                reported_by=reported_by,
            )
            self._send_json(new_record, status=201)

        elif path == "/api/obstacles/resolve":
            obs_id = body.get("id")
            if not obs_id:
                self._send_json({"error": "'id' is required"}, status=400)
                return

            resolved = self.obstacle_mgr.resolve_obstacle(obs_id)
            if resolved:
                self._send_json({"success": True, "id": obs_id})
            else:
                self._send_json({"error": f"Obstacle '{obs_id}' not found"}, status=404)

        else:
            self.send_error(404, "Endpoint Not Found")

    def _handle_route_query(self, query):
        """Compute route from query parameters and return JSON."""
        start_id = query.get("start", [""])[0]
        goal_id = query.get("goal", [""])[0]
        mode = query.get("mode", [AccessibilityMode.STANDARD])[0]
        algo = query.get("algo", ["dijkstra"])[0]

        if not start_id or not goal_id:
            self._send_json({"success": False, "message": "Missing 'start' or 'goal' parameter."}, status=400)
            return

        # Fetch active blocked edges from obstacle manager
        blocked_edges = self.obstacle_mgr.get_blocked_edges()

        # Run selected algorithm
        comparison = None
        if algo == "bfs":
            result = bfs_shortest_path(self.campus_graph, start_id, goal_id, mode=mode, blocked_edges=blocked_edges)
        elif algo == "compare":
            d_res = dijkstra_shortest_path(self.campus_graph, start_id, goal_id, mode=mode, blocked_edges=blocked_edges)
            b_res = bfs_shortest_path(self.campus_graph, start_id, goal_id, mode=mode, blocked_edges=blocked_edges)
            result = d_res
            comparison = {
                "dijkstra": d_res,
                "bfs": b_res,
            }
        else:  # default dijkstra
            result = dijkstra_shortest_path(self.campus_graph, start_id, goal_id, mode=mode, blocked_edges=blocked_edges)

        # Compute UI accessibility status badge
        # In prototype model, all connections are low-confidence / unknown unless verified
        badge_key, badge_label = get_accessibility_badge({"accessible": "unknown", "accessibility_confidence": "low"})

        self._send_json({
            "success": result.get("success", False),
            "primary": result,
            "comparison": comparison,
            "accessibility_badge": badge_key,
            "accessibility_badge_label": badge_label,
            "message": result.get("message", ""),
        })

    def _serve_file(self, relative_path, content_type):
        """Serve a static file from disk."""
        base_dir = Path(__file__).resolve().parent
        file_path = base_dir / relative_path

        if not file_path.is_file():
            self.send_error(404, "File Not Found")
            return

        content = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _send_json(self, data, status=200):
        """Send a JSON HTTP response."""
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_text(self, text, content_type="text/plain; charset=utf-8", status=200):
        """Send a plain text HTTP response."""
        payload = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        """Suppress noisy request logging during automated tests."""
        if "test" not in sys.argv[0]:
            super().log_message(format, *args)


def run_server(host=DEFAULT_HOST, port=DEFAULT_PORT):
    """Start the HTTP server on the specified host and port."""
    CampusNavigatorHandler.initialize_services()
    server_address = (host, port)
    httpd = HTTPServer(server_address, CampusNavigatorHandler)

    print("=" * 65)
    print("[*] ACCESSIBLE CAMPUS NAVIGATOR - LOCALHOST SERVER")
    print("=" * 65)
    print(f"Server running at:  http://{host}:{port}/")
    print(f"Campus Reference:   JAIN (Deemed-to-be University) - Global Campus")
    print(f"Technology:         Python 3 Standard Library (http.server)")
    print("Press Ctrl+C to stop the server.")
    print("=" * 65)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        httpd.server_close()
        print("Server stopped cleanly.")


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else DEFAULT_PORT
    run_server(port=port)
