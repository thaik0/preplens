# Basic Graphs — NeetCode 150 Notes

## Core Graph Patterns

### DFS / BFS traversal
Use when you need to explore all reachable nodes/cells from a starting point.

Common uses:
- islands
- connected components
- reachable nodes
- marking visited regions
- graph cloning

Mental rule:
> DFS/BFS = traverse relationships.

---

### Multi-source BFS
Use when many sources spread outward at the same time and you want the nearest distance.

Common uses:
- Walls and Gates / Islands and Treasure
- Rotting Oranges

Mental rule:
> If many cells are asking for distance to the nearest target, start BFS from all targets at once.

---

### Reverse search
Use when it is easier to start from the cells that are definitely safe / valid / reachable.

Common uses:
- Pacific Atlantic Water Flow
- Surrounded Regions

Mental rule:
> Instead of asking who is trapped, ask who can escape.

---

### Topological sort
Use for directed prerequisite/order problems.

Common uses:
- Course Schedule
- Course Schedule II

Mental rule:
> Directed graph + prerequisites/order = topological sort or DFS cycle detection.

---

### Union-Find / DSU
Use when the problem is about connected groups merging over time.

Common uses:
- Redundant Connection
- Graph Valid Tree
- Connected Components

Mental rule:
> Union-Find = maintain connected groups.  
> If two nodes are already connected, adding an edge between them creates a cycle.

---

## DFS on an Adjacency List

Use DFS when you want to explore as far as possible along one path before backtracking.

For an adjacency list, each node maps to its neighbors.

```python

visited = set()

def dfs(node):

    if node in visited:

        return

    visited.add(node)

    for nei in graph[node]:

        dfs(nei)
```

## 1. Number of Islands

Pattern: grid DFS/BFS

Key idea: each island is one connected component of `"1"` cells.

Algorithm:
1. Scan every cell.
2. When you find a `"1"`, increment island count.
3. DFS/BFS from that cell and mark the whole island visited.
4. Continue scanning.

Important:
- Mark visited by either using a `visited` set or changing `"1"` to `"0"`.
- Only move up, down, left, right.

Complexity:
- Time: `O(mn)`
- Space: `O(mn)` worst case recursion/visited

Mental note:
> Number of Islands = count connected components in a grid.

---

## 2. Max Area of Island

Pattern: grid DFS/BFS with component size

Key idea: instead of only counting islands, return the size of each island.

Algorithm:
1. Scan every cell.
2. When you find land, DFS/BFS and count how many land cells are connected.
3. Update max area.

DFS shape:

```python
def dfs(r, c):
    if out_of_bounds or grid[r][c] == 0:
        return 0

    grid[r][c] = 0
    area = 1

    for dr, dc in dirs:
        area += dfs(r + dr, c + dc)

    return area
```

Complexity:
- Time: `O(mn)`
- Space: `O(mn)` worst case recursion

Mental note:
> Max Area of Island = Number of Islands, but DFS returns size.

---

## 3. Clone Graph

Pattern: DFS/BFS with hashmap

Key idea: need a mapping from original nodes to cloned nodes.

Important:
- Use a dictionary, not a set.
- The dictionary maps `old_node -> cloned_node`.
- Create the copy before cloning neighbors to avoid infinite recursion on cycles.

DFS shape:

```python
old_to_new = {}

def clone(node):
    if node in old_to_new:
        return old_to_new[node]

    copy = Node(node.val)
    old_to_new[node] = copy

    for nei in node.neighbors:
        copy.neighbors.append(clone(nei))

    return copy
```

Complexity:
- Time: `O(V + E)`
- Space: `O(V)`

Mental note:
> Clone Graph = DFS with old-to-new hashmap.

---

## 4. Walls and Gates / Islands and Treasure

Pattern: multi-source BFS

Key idea: do not BFS from every empty room. Start from all gates/treasures at once.

Algorithm:
1. Add every gate/treasure `0` to the queue.
2. BFS outward.
3. When reaching an `INF` room, set its distance to `current_distance + 1`.
4. Do not revisit assigned rooms.

Core move:

```python
for r in range(rows):
    for c in range(cols):
        if grid[r][c] == 0:
            q.append((r, c))
```

Then:

```python
if grid[nr][nc] == INF:
    grid[nr][nc] = grid[r][c] + 1
    q.append((nr, nc))
```

Complexity:
- Time: `O(mn)`
- Space: `O(mn)`

Mental note:
> Multi-source BFS: put all sources in the queue first. The first time a cell is reached is the shortest distance from the nearest source.

---

## 5. Rotting Oranges

Pattern: multi-source BFS by levels

Key idea: all rotten oranges spread at the same time.

Algorithm:
1. Add all initially rotten oranges to the queue.
2. Count fresh oranges.
3. BFS level by level.
4. Each BFS layer = one minute.
5. When a fresh orange rots, decrement fresh count.
6. At the end, if fresh remains, return `-1`; otherwise return minutes.

Common bug:
- Increment minutes only when at least one orange rots during that layer.

Complexity:
- Time: `O(mn)`
- Space: `O(mn)`

Mental note:
> Rotting Oranges = multi-source BFS where each level is one minute.

---

## 6. Pacific Atlantic Water Flow

Pattern: reverse DFS/BFS from borders

Key idea: instead of starting from every cell and asking whether water can reach both oceans, start from the oceans and move inward.

Water normally flows from high to low. Reverse search moves from ocean inward to cells that are greater than or equal to the current height.

Algorithm:
1. DFS/BFS from Pacific borders.
2. DFS/BFS from Atlantic borders.
3. A cell that appears in both visited sets can reach both oceans.

Reverse movement rule:

```python
if heights[nr][nc] >= heights[r][c]:
    dfs(nr, nc)
```

Complexity:
- Time: `O(mn)`
- Space: `O(mn)`

Mental note:
> Pacific Atlantic = reverse search from oceans. Find cells that can reach each ocean by moving backward.

---

## 7. Surrounded Regions

Pattern: reverse DFS/BFS from border

Key idea: do not try to find surrounded `O`s directly. Find `O`s that are not surrounded.

A region is captured only if it cannot reach the border.

Algorithm:
1. DFS/BFS from every border `O`.
2. Mark all reachable `O`s as safe, such as `"S"`.
3. Scan board:
   - `"O" -> "X"` because it is surrounded.
   - `"S" -> "O"` because it is border-connected and safe.

Complexity:
- Time: `O(mn)`
- Space: `O(mn)` worst case recursion/queue

Mental note:
> Surrounded Regions = reverse DFS from border `O`s, mark safe, flip the rest.

---

## 8. Course Schedule

Pattern: directed graph cycle detection

Key idea: courses form a directed graph. If there is a cycle, it is impossible to finish all courses.

For prerequisite pair `[course, prereq]`, the edge is:

```text
prereq -> course
```

DFS states:
- `visiting`: currently in recursion stack
- `done`: already proven safe

Algorithm:
1. Build adjacency list.
2. DFS each course.
3. If DFS reaches a node already in `visiting`, there is a cycle.
4. If no cycles, return `True`.

Complexity:
- Time: `O(V + E)`
- Space: `O(V + E)`

Mental note:
> Course Schedule I = detect cycle in directed prerequisite graph.

---

## 9. Course Schedule II

Pattern: topological sort with indegree / Kahn's algorithm

Key idea: return an ordering of courses such that prerequisites come first.

For prerequisite pair `[course, prereq]`:

```text
prereq -> course
indegree[course] += 1
```

Meaning:
> `indegree[course] = number of prerequisites still unfinished`

Algorithm:
1. Build graph and indegree array.
2. Add all courses with indegree `0` to queue.
3. Pop course, append to result.
4. For each neighbor, decrement indegree.
5. If neighbor indegree becomes `0`, add it to queue.
6. If result has all courses, return result; otherwise return `[]`.

Complexity:
- Time: `O(V + E)`
- Space: `O(V + E)`

Mental note:
> Course Schedule II = topological sort. Start with courses that have no prerequisites.

---

## 10. Graph Valid Tree

Pattern: connectedness + edge count

Key idea: for an undirected graph:

```text
connected + exactly n - 1 edges = tree
```

Algorithm:
1. If `len(edges) != n - 1`, return `False`.
2. Build undirected graph.
3. DFS/BFS from node `0`.
4. Return whether all `n` nodes were visited.

Why no explicit cycle check?
- A connected undirected graph with `n - 1` edges cannot have a cycle.
- If it had a cycle, it would have an extra edge.

Complexity:
- Time: `O(n + e)`
- Space: `O(n + e)`

Mental note:
> Graph Valid Tree = check edge count, then check connected.

---

## 11. Number of Connected Components in an Undirected Graph

Pattern: DFS/BFS connected components

Key idea: every time you find an unvisited node, it starts a new component.

Algorithm:
1. Build undirected graph.
2. Initialize `count = 0`.
3. Loop through nodes `0` to `n - 1`.
4. If node is unvisited:
   - increment count
   - DFS/BFS to mark its whole component

Common bugs:
- Since graph is undirected, add both directions:

```python
graph[a].append(b)
graph[b].append(a)
```

- In DFS, recurse on `neighbor`, not the original node.

Complexity:
- Time: `O(n + e)`
- Space: `O(n + e)`

Mental note:
> Connected Components = count how many DFS/BFS starts are needed.

---

## 12. Redundant Connection

Pattern: Union-Find / DSU

Key idea: the graph started as a tree, then one extra edge was added.

As you process edges:
- If two nodes are already connected, adding this edge creates a cycle.
- That edge is redundant.

Union-Find skeleton:

```python
parent = [i for i in range(n + 1)]

def find(x):
    if x != parent[x]:
        parent[x] = find(parent[x])
    return parent[x]

def union(a, b):
    root_a = find(a)
    root_b = find(b)

    if root_a == root_b:
        return False

    parent[root_b] = root_a
    return True
```

Then:

```python
for a, b in edges:
    if not union(a, b):
        return [a, b]
```

Important:
- Nodes are usually `1`-indexed, so use `n + 1` size.
- Recursive `find` must return the root.
- `find(x)` gives the representative/root of x's component.
- `union(a, b)` merges components.

Complexity:
- Time: almost `O(n)` with path compression
- Space: `O(n)`

Mental note:
> Redundant Connection = Union-Find. If `find(a) == find(b)`, edge `[a, b]` creates a cycle.

---

## 13. Word Ladder

Pattern: BFS on an implicit graph

Key idea: each word is a node. Two words have an edge if they differ by exactly one character.

Since the problem asks for the shortest transformation length:

```text
Shortest path in unweighted graph = BFS
```

The graph is implicit, so do not compare every word to every other word. That is too slow.

Use wildcard buckets:

```text
hot -> *ot, h*t, ho*
dot -> *ot, d*t, do*
dog -> *og, d*g, do*
```

Words that share a wildcard pattern are one-letter neighbors.

Algorithm:
1. If `endWord` is not in `wordList`, return `0`.
2. Build `pattern -> list of words`.
3. BFS from `(beginWord, 1)`.
4. For each current word, generate its patterns.
5. Visit all words in matching pattern buckets.
6. Mark visited when enqueueing.
7. Clear used pattern buckets to avoid repeated scanning.

Queue syntax:

```python
q = deque([(beginWord, 1)])
```

This means the queue has one item: the tuple `(beginWord, 1)`.

Visited syntax:

```python
visited = {beginWord}
```

Optimized BFS shape:

```python
patterns = defaultdict(list)

for word in wordList:
    for i in range(len(word)):
        pattern = word[:i] + "*" + word[i+1:]
        patterns[pattern].append(word)

q = deque([(beginWord, 1)])
visited = {beginWord}

while q:
    word, level = q.popleft()

    if word == endWord:
        return level

    for i in range(len(word)):
        pattern = word[:i] + "*" + word[i+1:]

        for neighbor in patterns[pattern]:
            if neighbor not in visited:
                visited.add(neighbor)
                q.append((neighbor, level + 1))

        patterns[pattern] = []

return 0
```

Complexity:
- Time: `O(N * L^2)`
- Space: `O(N * L^2)`

Where:
- `N = number of words`
- `L = word length`

Mental note:
> Word Ladder = BFS on implicit graph. Use wildcard buckets to find one-letter neighbors quickly.

---

## Final Pattern Summary

| Problem | Main Pattern |
|---|---|
| Number of Islands | Grid DFS/BFS connected components |
| Max Area of Island | Grid DFS/BFS with component size |
| Clone Graph | DFS/BFS with old-to-new hashmap |
| Walls and Gates | Multi-source BFS |
| Rotting Oranges | Multi-source BFS by levels |
| Pacific Atlantic Water Flow | Reverse DFS/BFS from borders |
| Surrounded Regions | Reverse DFS/BFS from border safe cells |
| Course Schedule | Directed cycle detection |
| Course Schedule II | Topological sort |
| Graph Valid Tree | Connected + `n - 1` edges |
| Connected Components | Count DFS/BFS starts |
| Redundant Connection | Union-Find |
| Word Ladder | BFS on implicit graph with wildcard buckets |

## High-Level Memory Triggers

```text
Grid has islands/regions -> DFS/BFS
Nearest distance from many sources -> multi-source BFS
Border/ocean/safe escape -> reverse search from boundary
Prerequisites/order -> topological sort or directed cycle detection
Undirected connected groups/cycle from added edge -> Union-Find
Shortest transformation/path with equal edge weights -> BFS
Graph not directly given -> implicit graph neighbor generation
```
