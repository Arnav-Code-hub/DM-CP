"""Local classroom server. Compile main.c first, then run: python server.py"""
import json
import os
from pathlib import Path
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = Path(__file__).resolve().parent
ENGINE = ROOT / ("route.exe" if os.name == "nt" else "route")


class Handler(BaseHTTPRequestHandler):
    def respond(self, status, body, content_type="application/json; charset=utf-8"):
        if not isinstance(body, bytes):
            body = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def local_request(self):
        port = self.server.server_address[1]
        hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
        host = self.headers.get("Host", "")
        origin = self.headers.get("Origin")
        if host not in hosts or (origin and origin != f"http://{host}"):
            self.respond(403, {"error": "Use the local application address."})
            return False
        return True

    def do_GET(self):
        if not self.local_request():
            return
        if self.path not in ("/", "/index.html"):
            self.respond(404, {"error": "Not found."})
            return
        try:
            self.respond(200, (ROOT / "index.html").read_bytes(), "text/html; charset=utf-8")
        except OSError:
            self.respond(500, {"error": "index.html is missing or unreadable."})

    def do_POST(self):
        if not self.local_request():
            return
        if self.path != "/api/run":
            self.respond(404, {"error": "Not found."})
            return
        try:
            if self.headers.get_content_type() != "application/json":
                raise ValueError("Send application/json.")
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 16384:
                raise ValueError("Request must contain 1..16384 bytes.")
            self.connection.settimeout(5)
            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict) or data.get("algorithm") not in ("warshall", "floyd"):
                raise ValueError("Choose warshall or floyd.")
            matrix = data.get("matrix")
            if not isinstance(matrix, list) or not 1 <= len(matrix) <= 10:
                raise ValueError("Use 1..10 vertices.")
            for row in matrix:
                if not isinstance(row, list) or len(row) != len(matrix):
                    raise ValueError("The adjacency matrix must be square.")
                for weight in row:
                    if weight is not None and (type(weight) is not int or not -1000 <= weight <= 1000):
                        raise ValueError("Weights must be integers -1000..1000, or null for no road.")
        except (ValueError, OSError) as error:
            self.respond(400, {"error": str(error)})
            return

        text = f"{data['algorithm']} {len(matrix)}\n" + "\n".join(
            " ".join("x" if weight is None else str(weight) for weight in row)
            for row in matrix)
        try:
            result = subprocess.run([str(ENGINE)], input=text, text=True,
                                    capture_output=True, timeout=5, cwd=ROOT)
            if result.returncode:
                self.respond(500, {"error": result.stderr.strip() or "C calculation failed."})
            else:
                self.respond(200, result.stdout.encode("utf-8"))
        except FileNotFoundError:
            self.respond(503, {"error": "Compile main.c first; see README.md."})
        except subprocess.TimeoutExpired:
            self.respond(504, {"error": "C calculation timed out."})
        except OSError:
            self.respond(500, {"error": "Cannot start the C executable; rebuild it."})


if __name__ == "__main__":
    try:
        with HTTPServer(("127.0.0.1", 8000), Handler) as server:
            print("Open http://127.0.0.1:8000 — press Ctrl+C to stop.")
            server.serve_forever()
    except KeyboardInterrupt:
        pass
    except OSError as error:
        raise SystemExit(f"Cannot start server: {error}")
