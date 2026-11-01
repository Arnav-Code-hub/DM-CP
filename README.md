# Route Optimization Using Graph Theory

A Discrete Mathematics project with **Warshall's algorithm as the primary
algorithm** and Floyd–Warshall as its shortest-path extension. Both run in C.
The browser displays the graph, matrices, and calculation steps; it does not
calculate reachability or shortest paths.

## Run on Windows

Install GCC (MinGW) and Python 3 if they are not already available. In PowerShell,
open this project directory and run:

```powershell
gcc -std=c11 -Wall -Wextra -Wpedantic -O2 main.c -o route.exe
python server.py
```

Open **http://127.0.0.1:8000** in your browser. Keep the terminal running;
press Ctrl+C to stop. Open the server address, rather than opening index.html
directly. Recompile after changing main.c. If port 8000 is occupied, stop the
other server before launching this one.

No pip packages, JavaScript packages, external fonts, or internet connection
are needed after installing GCC and Python.

## Use

1. Load the fictional city example, or add/remove locations (1–10 vertices).
2. Select a road's endpoints and save its integer weight. **Close road** removes
   that directed edge. Add the reverse edge separately for two-way roads.
3. Select **Warshall** and press **Start** to calculate and animate reachability.
4. Pause and use **Next Step** or **Previous Step** to inspect one `(k, i, j)`
   operation. The outlined cell is the target; gold marks the operand positions;
   green marks a changed value. Operands in the explanation always come from
   the previous k stage, even if their displayed cells have already been updated.
5. Select **Floyd–Warshall**, choose source/destination, and press Start. At the
   end, inspect the highlighted shortest route, total distance, and final matrix.
6. **Reset** rewinds the calculation. **Load city example** restores the graph.
   Graph edits and algorithm changes clear previous results. Refreshing the page
   also restores the example; graph changes are kept only in browser memory.

The example's College → Airport shortest route is
**College → Hospital → Shopping Mall → Airport**, distance **11**.
Close Shopping Mall → Airport and it becomes **13** through Railway Station.
Close Railway Station → Airport as well and Airport becomes unreachable from
College. Use Fast playback for the 125-operation example.

## Mathematics for the viva

Vertices represent locations; directed weighted edges represent roads.
The input is an adjacency matrix. No edge is `null` in JSON or `x` in C input;
**0 is a valid weight**, not an absent edge. Weights are integers −1000…1000.
Negative weights model abstract costs rather than physical road distances.

**Warshall** uses Boolean algebra:

```text
R^k[i][j] = R^(k-1)[i][j] OR
           (R^(k-1)[i][k] AND R^(k-1)[k][j])
```

Initially R[i][j] records edge presence, and R[i][i] = 1 because zero-length
paths count. The result is the **reflexive transitive closure**. A value of 1
means a path exists; a value of 0 means unreachable. Weights do not affect
reachability.

**Floyd–Warshall** uses minimum and addition:

```text
D^k[i][j] = min(D^(k-1)[i][j], D^(k-1)[i][k] + D^(k-1)[k][j])
```

Initially direct edges supply distances, absent paths are infinity, and
D[i][i] = min(0, self-loop weight) when a self-loop exists, otherwise 0.
The next-hop matrix records the first vertex to visit on each improved route.
Equal-cost candidates keep the existing route. At stage k, paths may use
vertices A through k as intermediates. Previous/current matrices are kept
separately so every step matches these recurrences exactly.

A negative final diagonal identifies a negative cycle. If source i can reach
such a cycle and the cycle can reach destination j, no finite shortest distance
exists for that pair. The final UI displays **−∞** and suppresses its route.
Raw finite recurrence values remain in the trace for teaching; they are not
claimed to be shortest distances for cycle-affected pairs. Unaffected pairs
still have valid results. Infinity arithmetic is guarded, and bounded input
with 64-bit integers keeps intermediate additions within range.

Each algorithm performs V³ evaluations: **O(V³) time and O(V²) working space**.
C streams the calculation trace; the browser retains it for backward playback,
using an additional O(V³) space. The teaching interface limits V to 10.

## Files and interface

- `main.c`: validates numeric input, computes both algorithms, writes JSON.
- `server.py`: serves only index.html and POST /api/run on 127.0.0.1:8000;
  validates input and launches the C executable without a shell.
- `index.html`: basic CSS, SVG graph, editor, and step playback.
- `test_project.py`: standard-library algorithm and HTTP tests.

POST /api/run accepts:

```json
{"algorithm":"floyd","matrix":[[null,4],[null,null]]}
```

Use `warshall` for Boolean reachability. The response contains `initial`,
`steps`, and `final`. Each step has zero-based `k`, `i`, `j`, `old`, `left`,
`right`, `candidate`, `value`, and `changed`. Floyd–Warshall also returns
all-pairs `paths` and Boolean `affected` matrices. A null path means unreachable
or negative-cycle-affected; use `affected` to distinguish them.

The C program can also run directly. For example:

```powershell
"floyd 3 x 4 10 x x 3 x x x" | .\route.exe
```

Input is the algorithm name, vertex count, then V² row-major matrix entries.
Output is one JSON object. The program rejects invalid or extra tokens.

## Verify

```powershell
python -m unittest -v
```

The tests compile C with warnings enabled and cover reachability, route
reconstruction, every trace recurrence, exhaustive small-graph route checks,
closures, unreachable pairs, zero/negative weights, self-loops, negative cycles,
input limits, and the real HTTP-to-C connection. The test command rebuilds
route.exe. This server is for a local classroom demonstration, not deployment.
