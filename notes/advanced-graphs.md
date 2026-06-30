# Advanced Graphs — Problem Solving Notes

## Algorithms and Patterns Used

### Dijkstra's Algorithm

Use Dijkstra when the graph has **nonnegative weighted edges** and you need the cheapest/shortest path.

Mental trigger:

```text
weighted graph + nonnegative costs + shortest/cheapest path
```

Core LeetCode style:

```python
dist = [float("inf")] * n
dist[start] = 0
heap = [(0, start)]  # cost, node

while heap:
    cost, node = heapq.heappop(heap)

    if cost > dist[node]:
        continue

    for nei, weight in graph[node]:
        new_cost = cost + weight

        if new_cost < dist[nei]:
            dist[nei] = new_cost
            heapq.heappush(heap, (new_cost, nei))
```

Important details:
- Heap entries should usually be `(cost, node)`, not `(node, cost)`.
- Python heaps sort by the first tuple element.
- `heapq.heappop(heap)`, not `heapq.pop(heap)`.
- `heapq.heappush(heap, val)`, not `heap.heappush(val)`.
- `heapq.heapify(list)` modifies the list in place and returns `None`.
- The heap may contain stale old states.
- Skip stale states with:

```python
if cost > dist[node]:
    continue
```

Mental rule:

```text
dist[node] = best known cost so far.
Heap may contain old worse versions.
Only expand a state if it still matches/improves the best known cost.
```

---

### Dijkstra with Expanded State

Sometimes the state is not just the node.

Use this when the problem has an extra constraint, such as:
- number of stops used
- number of moves left
- special resource used/not used
- current mode/state

Example state:

```text
(city, flights_used)
```

Then the best table becomes 2D:

```python
best[city][flights_used]
```

Mental trigger:

```text
If reaching the same node with different extra information changes what you can do next,
then the state must include that extra information.
```

Important:
- Do not use a single `dist[city]` if the number of flights/stops/resources matters.
- Only push a new state if it improves `best[state]`.
- Update `best[state]` before pushing to the heap.

---

### Bellman-Ford Style DP

Use Bellman-Ford when shortest path depends on the **number of edges used**, or when negative weights may exist.

For LeetCode, the biggest trigger is:

```text
shortest/cheapest path + at most K edges/stops
```

Mental model:

```text
Each round allows one more edge.
```

Template idea:

```python
prices = [float("inf")] * n
prices[src] = 0

for _ in range(k + 1):
    tmp = prices.copy()

    for s, d, price in edges:
        if prices[s] == float("inf"):
            continue

        tmp[d] = min(tmp[d], prices[s] + price)

    prices = tmp
```

Important:
- Use `tmp = prices.copy()`.
- The copy prevents one round from accidentally chaining multiple new edges.
- If `k` stops are allowed, then at most `k + 1` flights/edges are allowed.

Mental rule:

```text
Dijkstra = cheapest-first with a heap.
Bellman-Ford = layer-by-layer by number of edges.
```

---

### Minimum Spanning Tree

Use MST when the goal is:

```text
connect all nodes with minimum total edge cost
```

This is different from shortest path.

Shortest path asks:

```text
What is the cheapest path from A to B?
```

MST asks:

```text
What is the cheapest set of edges that connects everything?
```

---

### Prim's Algorithm

Prim grows one connected tree.

Mental model:

```text
Start from one node.
Repeatedly add the cheapest edge from the current tree to an unvisited node.
```

Common structure:

```python
heap = [(0, 0)]  # edge_cost, node
visited = set()
total = 0

while len(visited) < n:
    cost, node = heapq.heappop(heap)

    if node in visited:
        continue

    visited.add(node)
    total += cost

    for nei in unvisited_neighbors:
        heapq.heappush(heap, (edge_cost, nei))
```

Important:
- Heap stores the cost to add a new node to the tree.
- Only pay the cost when the popped node is newly added.
- Skip already visited nodes because the heap can contain duplicates.

Mental rule:

```text
Prim = grow one tree using the cheapest edge from visited to unvisited.
```

---

### Kruskal's Algorithm

Kruskal sorts all edges globally and uses Union-Find.

Mental model:

```text
Sort all edges by cost.
Add the cheapest edge if it connects two different components.
Skip it if it creates a cycle.
```

Common structure:

```python
edges.sort()

for cost, a, b in edges:
    if union(a, b):
        total += cost
        edges_used += 1

        if edges_used == n - 1:
            return total
```

Important:
- Kruskal usually needs all edges explicitly.
- Union-Find detects whether adding an edge creates a cycle.
- Stop after `n - 1` edges.

Mental rule:

```text
Kruskal = sort edges + Union-Find.
```

---

### Topological Sort / Kahn's Algorithm

Use topological sort when the graph is directed and represents ordering constraints.

Mental trigger:

```text
A must come before B
prerequisites
alien alphabet order
dependency graph
```

Kahn's algorithm:
1. Build graph and indegree.
2. Start with all nodes with indegree `0`.
3. Pop nodes from queue.
4. Decrease indegree of neighbors.
5. If a neighbor reaches indegree `0`, add it to queue.
6. If result length is smaller than number of nodes, there is a cycle.

Important:
- Kahn's algorithm can detect cycles.
- If not all nodes are processed, some nodes were trapped in a cycle.

Mental rule:

```text
Topological sort = ordering directed constraints.
Kahn's detects cycles by checking whether all nodes were processed.
```

---

### Edge-Using DFS / Postorder

Some graph problems are not about visiting each node once. They are about using each **edge** exactly once.

Mental trigger:

```text
Use all tickets/edges exactly once.
Build a valid path using all directed edges.
```

In these problems, normal visited-node DFS is usually wrong.

Postorder idea:

```text
A node can only be finalized after all its outgoing edges/children are fully processed.
```

Mental rule:

```text
Preorder = record when entering.
Postorder = record when done.
```

For edge-using DFS:
- Consume edges as you traverse them.
- Append the node after all outgoing edges are used.
- Reverse the result at the end.

Python note:

```python
res[::-1]
```

returns a reversed copy of a list.

---

## General Things Learned

### 1. Problem state matters

In basic graph problems, the state is often just:

```text
node
```

In advanced graphs, the state may be:

```text
node + extra information
```

Examples:
- `(city, flights_used)`
- `(row, col)`
- `(row, col, current_time)`
- conceptually, `(airport, remaining tickets)`

Mental rule:

```text
If reaching the same node in two different ways changes future options, include that difference in the state.
```

---

### 2. The cost function can change

In normal shortest path:

```text
new_cost = old_cost + edge_weight
```

But not always.

For bottleneck path problems:

```text
new_cost = max(old_cost, next_cell_cost)
```

Mental rule:

```text
Dijkstra works when the path cost only gets worse/greater as you extend the path.
The update does not always have to be addition.
```

---

### 3. Heap details matter

Common heap mistakes:
- Wrong tuple order.
- Forgetting that `heapq.heapify()` returns `None`.
- Using `heap.pop()` instead of `heapq.heappop(heap)`.
- Using `heap.heappush(...)` instead of `heapq.heappush(heap, ...)`.
- Pushing states without checking if they improve `best`.

Important pattern:

```python
if new_cost < best[state]:
    best[state] = new_cost
    heapq.heappush(heap, (new_cost, state))
```

Mental rule:

```text
If a state is worth pushing, update best immediately.
```

---

### 4. Greedy can be valid when there is a theorem behind it

Prim and Kruskal are greedy algorithms.

Prim greedily takes:

```text
the cheapest edge from the current tree to an unvisited node
```

Kruskal greedily takes:

```text
the cheapest global edge that does not create a cycle
```

These work because of MST properties, especially the cut property.

Mental rule:

```text
MST greedy choices are safe because the cheapest edge crossing a cut can be part of an MST.
```

---

### 5. Graph construction is often the hard part

Advanced graph problems often do not give the graph directly.

Common examples:
- Words imply character ordering.
- Tickets imply directed edges.
- Grid cells imply neighboring states.
- Points imply a complete graph with Manhattan distances.
- Words imply an implicit graph through wildcard patterns.

Mental rule:

```text
Before choosing the algorithm, figure out what the nodes and edges are.
```

---

## Problem-by-Problem Breakdown

## Word Ladder

Core pattern:

```text
BFS on an implicit graph
```

Overarching idea:
- Words are nodes.
- One-letter transformations are edges.
- Because each transformation has equal cost, BFS finds the shortest path.

Key optimization:
- Do not compare every word to every other word.
- Use wildcard buckets.

Example:

```text
hot -> *ot, h*t, ho*
dot -> *ot, d*t, do*
```

Words sharing a pattern are neighbors.

Important implementation details:
- Queue stores words, not patterns.
- Patterns are only a lookup tool.
- Mark visited when enqueueing.
- Clear pattern buckets after use to avoid repeated scans.
- Use `deque([(beginWord, 1)])` when queue items are tuples.

Mental note:

```text
Word Ladder = shortest path in an implicit unweighted graph.
Use wildcard buckets to generate neighbors efficiently.
```

---

## Cheapest Flights Within K Stops

Core patterns:
- Bellman-Ford style DP
- Dijkstra with expanded state

Overarching idea:
- This is shortest path with an edge limit.
- `k` stops means at most `k + 1` flights.

Why normal Dijkstra is awkward:
- Reaching the same city with different numbers of flights used are different states.
- A cheaper path to a city might use too many stops.
- A more expensive path might leave more stop budget.

Bellman-Ford idea:
- Each round allows one more flight.
- Use a copy so one round does not chain multiple flights.

Dijkstra-state idea:
- State is `(city, flights_used)`.
- Use `best[city][flights_used]`.

Mental note:

```text
If the number of edges matters, Bellman-Ford is often cleaner than Dijkstra.
If using Dijkstra, expand the state to include flights_used.
```

---

## Network Delay Time

Core pattern:

```text
standard Dijkstra
```

Overarching idea:
- Directed weighted graph.
- Start from one node.
- Find shortest time to every other node.
- Answer is the maximum shortest time.
- If any node is unreachable, return `-1`.

Important Dijkstra details:
- Heap stores `(time, node)`.
- Use `dist[node]`.
- Skip stale entries with `if time > dist[node]: continue`.
- At the end, take `max(dist[1:])` for 1-indexed nodes.

Mental note:

```text
Network Delay = clean LeetCode-style Dijkstra.
Find shortest path from source to all nodes, then take the maximum.
```

---

## Min Cost to Connect All Points

Core pattern:

```text
Minimum Spanning Tree
```

Overarching idea:
- Need to connect all points.
- Cost between points is Manhattan distance.
- Goal is minimum total connection cost, not shortest path from one point.

Two MST approaches:

### Prim
- Grow one connected tree.
- Heap stores candidate edges from the tree to unvisited points.
- Good when the graph is dense or edges can be generated on the fly.

### Kruskal
- Generate all pairwise edges.
- Sort by cost.
- Use Union-Find to add edges that do not create cycles.
- Good when edges are already given as a list.

Mental note:

```text
Connect all nodes with minimum total cost = MST.
Prim = heap + visited.
Kruskal = sorted edges + Union-Find.
```

---

## Swim in Rising Water

Core pattern:

```text
Dijkstra on a grid with bottleneck cost
```

Overarching idea:
- Each cell is a node.
- Moving to a cell may require waiting until water reaches that elevation.
- Path cost is the maximum elevation seen so far, not the sum of elevations.

Transition:

```python
new_time = max(current_time, grid[nr][nc])
```

Important Dijkstra details:
- Initialize with `grid[0][0]`.
- Use `best[r][c]`.
- Only push a neighbor if it improves `best[nr][nc]`.
- Update `best[nr][nc]` before pushing.

Mental note:

```text
Swim in Rising Water = Dijkstra where path cost is max along the path.
Not all Dijkstra costs are sums.
```

---

## Alien Dictionary

Core pattern:

```text
build ordering graph + topological sort
```

Overarching idea:
- The dictionary is sorted according to an unknown alphabet.
- Adjacent words reveal ordering constraints.
- The first differing character gives the only useful ordering rule.

Example:

```text
wrt
wrf
```

First differing characters:

```text
t before f
t -> f
```

Important details:
- Include all unique characters, even if they have no edges.
- Only use the first differing character between adjacent words.
- Avoid double-counting duplicate edges.
- Invalid prefix case:

```text
["abc", "ab"]
```

This is invalid because a longer word appears before its own prefix.

Use Kahn's algorithm:
- Build indegrees.
- Process indegree `0` characters.
- If result length is smaller than number of unique characters, there is a cycle.

Mental note:

```text
Alien Dictionary = infer graph edges from adjacent words, then topo sort.
Only the first differing character matters.
Kahn's algorithm detects cycles.
```

---

## Reconstruct Itinerary

Core pattern:

```text
edge-using DFS with postorder
```

Overarching idea:
- Tickets are directed edges.
- Airports are nodes.
- Need to use every ticket exactly once.
- Need lexicographically smallest valid itinerary.

Why normal DFS is not enough:
- This is not about visiting every airport once.
- Airports can appear multiple times.
- The constraint is using every ticket exactly once.

Key idea:
- Use sorted adjacency or min-heaps for lexical order.
- During DFS, consume outgoing tickets.
- Append airport after all outgoing tickets are used.
- Reverse the result at the end.

Postorder reasoning:

```text
A node should only be finalized after all outgoing edges from it are exhausted.
```

Python note:

```python
res[::-1]
```

reverses the list.

Mental note:

```text
Reconstruct Itinerary = edge-using DFS, not visited-node DFS.
Append in postorder, then reverse.
Use min-heaps/sorted adjacency for lexical order.
```

---

## Quick Pattern Table

| Situation | Pattern |
|---|---|
| Unweighted shortest path | BFS |
| Weighted shortest path, nonnegative edges | Dijkstra |
| Shortest path with edge limit | Bellman-Ford style DP |
| Same node with different resources/stops | Expanded state Dijkstra |
| Connect all nodes with minimum total cost | MST |
| Grow one MST from a start node | Prim |
| Sort edges and avoid cycles | Kruskal |
| Directed ordering constraints | Topological sort |
| Need to detect directed cycle through indegrees | Kahn's algorithm |
| Use every edge exactly once | Edge-using DFS / postorder |
| Graph not directly given | Identify nodes, edges, and neighbor generation |

---

## Final Mental Checklist for Advanced Graphs

Before coding, ask:

```text
1. What are the nodes?
2. What are the edges?
3. Is the graph directed or undirected?
4. Are edges weighted?
5. Are weights all nonnegative?
6. Do I need shortest path, connectivity, ordering, or minimum connection cost?
7. Is the state just the node, or node + extra information?
8. Do I need to visit nodes, or use edges?
9. Can I build neighbors directly, or is the graph implicit?
10. What should be stored in the heap/queue?
```

Algorithm triggers:

```text
Shortest path, unweighted -> BFS
Shortest path, weighted -> Dijkstra
Shortest path with edge limit -> Bellman-Ford / expanded-state Dijkstra
Minimum total connection cost -> MST
Ordering constraints -> Topological sort
Use all edges exactly once -> Postorder edge-using DFS
```
