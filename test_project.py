"""Run with: python -m unittest -v"""
import http.client
import importlib
import itertools
import json
from pathlib import Path
import random
import subprocess
import threading
import unittest

ROOT = Path(__file__).resolve().parent
EXE = ROOT / "route.exe"


def run_engine(algorithm, matrix):
    data = f"{algorithm} {len(matrix)}\n" + "\n".join(
        " ".join("x" if value is None else str(value) for value in row)
        for row in matrix
    )
    result = subprocess.run([str(EXE)], input=data, text=True,
                            capture_output=True, timeout=5)
    if result.returncode:
        raise AssertionError(result.stderr)
    return json.loads(result.stdout)


class Algorithms(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        build = subprocess.run(
            ["gcc", "-std=c11", "-Wall", "-Wextra", "-Wpedantic", "-O2",
             str(ROOT / "main.c"), "-o", str(EXE)],
            capture_output=True, text=True, timeout=30)
        assert build.returncode == 0, build.stderr
        assert not build.stderr, build.stderr

    def test_warshall_transitive_and_reflexive(self):
        result = run_engine("warshall", [[None, 0, None], [None, None, 4], [None]*3])
        self.assertEqual(result["final"], [[1, 1, 1], [0, 1, 1], [0, 0, 1]])

    def test_city_routes_and_closures(self):
        matrix = [[None]*5 for _ in range(5)]
        for i, j, w in [(0,1,4), (0,2,10), (1,2,3), (2,3,6),
                        (1,4,5), (4,3,2), (3,0,12)]:
            matrix[i][j] = w
        result = run_engine("floyd", matrix)
        self.assertEqual(result["final"][0][3], 11)
        self.assertEqual(result["paths"][0][3], [0, 1, 4, 3])
        matrix[4][3] = None
        self.assertEqual(run_engine("floyd", matrix)["final"][0][3], 13)
        matrix[2][3] = None
        result = run_engine("floyd", matrix)
        self.assertIsNone(result["final"][0][3])
        self.assertIsNone(result["paths"][0][3])

    def test_zero_negative_and_disconnected(self):
        result = run_engine("floyd", [[None, 0, 8], [None, None, -2], [None]*3])
        self.assertEqual(result["final"][0][2], -2)
        self.assertEqual(result["paths"][0][2], [0, 1, 2])
        self.assertIsNone(result["paths"][2][0])
        self.assertEqual(result["paths"][2][2], [2])
        self.assertFalse(any(map(any, result["affected"])))

    def test_negative_cycle_only_invalidates_affected_pairs(self):
        result = run_engine("floyd", [[None, 2, None, None],
            [None, None, -3, None], [None, 1, None, None], [None]*4])
        self.assertTrue(result["affected"][0][2])
        self.assertIsNone(result["paths"][0][2])
        self.assertFalse(result["affected"][3][3])
        self.assertEqual(result["paths"][3][3], [3])
        self.assertFalse(result["affected"][0][0])

    def test_self_loops_and_single_vertex(self):
        for weight in (None, 0, 5):
            result = run_engine("floyd", [[weight]])
            self.assertEqual(result["final"], [[0]])
            self.assertEqual(result["paths"], [[[0]]])
        result = run_engine("floyd", [[-1]])
        self.assertEqual(result["affected"], [[True]])
        self.assertIsNone(result["paths"][0][0])

    def test_each_step_uses_previous_k_matrix(self):
        matrix = [[None, 0, 8], [None, None, -2], [1, None, None]]
        for algorithm in ("warshall", "floyd"):
            result = run_engine(algorithm, matrix)
            current = [row[:] for row in result["initial"]]
            steps = iter(result["steps"])
            self.assertEqual(len(result["steps"]), 27)
            for k in range(3):
                previous = [row[:] for row in current]
                for i in range(3):
                    for j in range(3):
                        step = next(steps)
                        old, left, right = previous[i][j], previous[i][k], previous[k][j]
                        if algorithm == "warshall":
                            candidate = int(bool(left and right))
                            value = int(bool(old or candidate))
                        else:
                            candidate = None if left is None or right is None else left + right
                            value = old if candidate is None else candidate if old is None else min(old, candidate)
                        self.assertEqual(step, dict(k=k, i=i, j=j, old=old,
                            left=left, right=right, candidate=candidate,
                            value=value, changed=value != old))
                        current[i][j] = value
            self.assertEqual(current, result["final"])

    def test_routes_match_exhaustive_simple_paths(self):
        rng = random.Random(42)
        for _ in range(6):
            n = 4
            matrix = [[rng.choice([None, 0, 2, 7]) if i != j else None
                       for j in range(n)] for i in range(n)]
            result = run_engine("floyd", matrix)
            for i in range(n):
                for j in range(n):
                    distances = [0] if i == j else []
                    if i != j:
                        others = [v for v in range(n) if v not in (i, j)]
                        for size in range(len(others)+1):
                            for middle in itertools.permutations(others, size):
                                path = (i, *middle, j)
                                weights = [matrix[a][b] for a, b in zip(path, path[1:])]
                                if None not in weights:
                                    distances.append(sum(weights))
                    expected = min(distances) if distances else None
                    self.assertEqual(result["final"][i][j], expected)
                    path = result["paths"][i][j]
                    if expected is None:
                        self.assertIsNone(path)
                    else:
                        self.assertEqual((path[0], path[-1]), (i, j))
                        self.assertEqual(sum(matrix[a][b] for a, b in zip(path, path[1:])), expected)

    def test_maximum_size_and_weights(self):
        matrix = [[None]*10 for _ in range(10)]
        for i in range(9):
            matrix[i][i+1] = -1000
        result = run_engine("floyd", matrix)
        self.assertEqual(result["final"][0][9], -9000)
        self.assertEqual(result["paths"][0][9], list(range(10)))
        self.assertEqual(len(result["steps"]), 1000)

    def test_c_rejects_invalid_input(self):
        for data in ("floyd 0", "floyd 11", "other 1 x", "floyd 1 1001",
                     "floyd 1 -1001", "floyd 1 1.2", "floyd 2 x", "floyd 1 x extra",
                     "floyd 1 9999999999999999999999999999"):
            result = subprocess.run([str(EXE)], input=data, text=True,
                                    capture_output=True, timeout=5)
            self.assertNotEqual(result.returncode, 0, data)


class HTTPIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        server = importlib.import_module("server")
        cls.httpd = server.HTTPServer(("127.0.0.1", 0), server.Handler)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join()

    def request(self, path, data=None, origin=None):
        connection = http.client.HTTPConnection(*self.httpd.server_address, timeout=5)
        headers = {"Content-Type": "application/json"}
        if origin:
            headers["Origin"] = origin
        connection.request("GET" if data is None else "POST", path,
                           None if data is None else json.dumps(data), headers)
        response = connection.getresponse()
        body = response.read()
        connection.close()
        return response.status, body

    def test_serves_only_interface(self):
        status, body = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn(b"Warshall", body)
        self.assertEqual(self.request("/main.c")[0], 404)

    def test_runs_c_algorithm(self):
        status, body = self.request("/api/run", {"algorithm": "floyd", "matrix": [[None, 5], [None, None]]})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["paths"][0][1], [0, 1])

    def test_rejects_invalid_requests(self):
        for data in (None, [], {}, {"algorithm": "floyd", "matrix": []},
                     {"algorithm": "floyd", "matrix": [[True]]},
                     {"algorithm": "floyd", "matrix": [[1.5]]},
                     {"algorithm": "floyd", "matrix": [[1001]]},
                     {"algorithm": "floyd", "matrix": [[None], [None]]}):
            if data is not None:
                self.assertEqual(self.request("/api/run", data)[0], 400)
        self.assertEqual(self.request("/api/run", {}, "https://example.com")[0], 403)


if __name__ == "__main__":
    unittest.main()
