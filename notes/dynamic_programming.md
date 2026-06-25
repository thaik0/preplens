# Dynamic Programming Notes

These notes summarize the DP patterns from the problems completed this week. The main goal is not to memorize solutions, but to recognize the **state**, **choice**, **transition**, **base case**, and **loop direction**.

---

## 1. Core DP Mental Model

For any DP problem, write these before coding:

```text
1. What does dp[...] mean?
2. What choices do I have at this state?
3. What smaller subproblem(s) does this depend on?
4. What are the base cases?
5. What direction should I fill the table or recurse?
6. Can the space be compressed?
```

A good DP state should answer one clear question.

Examples:

```text
dp[i] = best answer up to index i
dp[i] = number of ways to decode s[i:]
dp[amt] = number of ways/min coins to make amount amt
dp[i][j] = answer involving two positions
dfs(r, c) = answer starting from grid cell (r, c)
```

DP usually becomes easier once the state is precise.

---

## 2. Big DP Categories

### A. 1-D DP

State usually depends on previous or future indices.

Examples:

- 70. Climbing Stairs
- 746. Min Cost Climbing Stairs
- 198. House Robber
- 213. House Robber II
- 91. Decode Ways
- 139. Word Break
- 300. Longest Increasing Subsequence
- 152. Maximum Product Subarray

Common forms:

```text
dp[i] = best answer ending at i
dp[i] = best answer from i onward
dp[i] = number of ways to reach i
dp[i] = whether prefix ending at i is valid
```

Key rule:

```text
If dp[i] depends on earlier states, iterate forward.
If dp[i] depends on future states, iterate backward.
```

---

### B. Amount / Knapsack DP

State involves building an amount or target sum.

Examples:

- 322. Coin Change
- 518. Coin Change II
- 416. Partition Equal Subset Sum
- 494. Target Sum

Common state:

```text
dp[amt] = answer for amount amt
```

Important loop rule:

```text
Unlimited reuse of items -> loop amount forward.
Use each item once       -> loop amount backward.
```

Why?

```text
Forward loop can reuse the current item in the same iteration.
Backward loop prevents the current item from being used twice.
```

---

### C. 2-D String DP

State involves two positions or two prefixes/suffixes.

Examples:

- 1143. Longest Common Subsequence
- 97. Interleaving String
- 72. Edit Distance
- 115. Distinct Subsequences

Common state:

```text
dp[i][j] = answer involving word1[i:] and word2[j:]
```

or

```text
dp[i][j] = answer involving word1[:i] and word2[:j]
```

Important: do not mix prefix and suffix definitions.

```text
Prefix DP usually fills top-left to bottom-right.
Suffix DP usually fills bottom-right to top-left.
```

Matrix rule:

```text
dp[row][col]
row = vertical
col = horizontal
```

If you define:

```text
rows = word1
cols = word2
```

then draw it that way. A transposed drawing is okay only if the code is also transposed.

---

### D. Grid DP / DFS + Memo

State is usually a cell.

Examples:

- 62. Unique Paths
- 64. Minimum Path Sum
- 329. Longest Increasing Path in a Matrix

Common state:

```text
dp[r][c] = answer at or starting from cell (r, c)
```

For DFS + memo:

```text
dfs(r, c) = best answer starting from cell (r, c)
```

Pattern:

```text
1. Define dfs(r, c)
2. If memo exists, return it
3. Try valid neighbors
4. Store result
5. Answer may be max/min over all starts
```

For Longest Increasing Path:

```text
dfs(r, c) = longest increasing path starting from matrix[r][c]
```

No visited set is needed because strictly increasing moves cannot form a cycle.

---

### E. State-Machine DP

State is a small fixed set of situations.

Example:

- 309. Best Time to Buy and Sell Stock with Cooldown

Use variables instead of a table when the states are few and fixed.

```text
hold = best profit after today if holding stock
sold = best profit after today if just sold today
rest = best profit after today if not holding and not just sold
```

Transitions:

```text
new_hold = max(old_hold, old_rest - price)
new_sold = old_hold + price
new_rest = max(old_rest, old_sold)
```

Key insight:

```text
Cooldown rule: you can only buy from old_rest, not old_sold.
```

For state-machine DP, O(1) memory is often clearer than a `dp[day][state]` table.

---

### F. Palindrome DP / Center Expansion

Examples:

- 647. Palindromic Substrings
- 5. Longest Palindromic Substring

Important palindrome trick:

```text
Every palindrome expands from a center.
```

There are two center types:

```text
Odd length:  center at i
Even length: center between i and i + 1
```

When expanding:

```text
while l >= 0 and r < len(s) and s[l] == s[r]:
    l -= 1
    r += 1
```

After the loop ends, `l` and `r` have moved one step too far.

So the valid palindrome is:

```python
s[l + 1 : r]
```

---

## 3. Problem Notes

### 72. Edit Distance

Main lesson: draw the visual representation correctly.

State used:

```text
dp[i][j] = minimum edits to convert word1[i:] into word2[j:]
```

Base cases:

```text
If word1 is empty: insert the rest of word2.
dp[len(word1)][j] = len(word2) - j

If word2 is empty: delete the rest of word1.
dp[i][len(word2)] = len(word1) - i
```

Transition:

```text
If word1[i] == word2[j]:
    dp[i][j] = dp[i+1][j+1]

Else:
    insert  = 1 + dp[i][j+1]
    delete  = 1 + dp[i+1][j]
    replace = 1 + dp[i+1][j+1]

    dp[i][j] = min(insert, delete, replace)
```

Meaning of operations:

```text
insert:
    Insert word2[j], so move j forward.

delete:
    Delete word1[i], so move i forward.

replace:
    Replace word1[i] with word2[j], so move both forward.
```

Complexity:

```text
Time:  O(mn)
Space: O(mn)
```

Space optimization:

```text
Only need current row and next row.
Space becomes O(n), where n = len(word2).
```

Visual warning:

```text
If word1 = "horse" and word2 = "ros",
suffix DP with rows = word1 and cols = word2 is a 6 x 4 table.
The extra row/column represents the empty suffix.
```

---

### 518. Coin Change II

Main lesson: code the comfortable 2-D version first, then optimize.

2-D state:

```text
dp[amt][j] = number of ways to make amt using coins[j:]
```

Choices:

```text
skip coin j:
    dp[amt][j + 1]

use coin j:
    dp[amt - coins[j]][j]
```

The use case stays at `j` because coins can be reused unlimited times.

Base cases:

```text
dp[0][j] = 1
```

There is one way to make amount 0: choose no coins.

Recurrence:

```text
dp[amt][j] = dp[amt][j + 1]

if coins[j] <= amt:
    dp[amt][j] += dp[amt - coins[j]][j]
```

Important lesson:

```text
Every cell always has the skip option.
Only some cells also have the use option.
```

1-D optimization:

```text
dp[amt] = number of ways to make amt using coins processed so far
```

Code pattern:

```python
dp = [0] * (amount + 1)
dp[0] = 1

for coin in coins:
    for amt in range(coin, amount + 1):
        dp[amt] += dp[amt - coin]
```

Why it works:

```text
Old dp[amt] already means ways without this coin.
dp[amt - coin] adds ways that use this coin.
```

Loop direction:

```text
Amount loops forward because coins can be reused.
```

---

### 494. Target Sum

Main lesson: memoized recursion first, then mathematical optimization.

Recursive state:

```text
dp(i, val) = number of ways to assign signs from nums[i:] 
             given current sum val
```

Choices:

```text
+ nums[i]
- nums[i]
```

Base case:

```text
if i == len(nums):
    return 1 if val == target else 0
```

Transition:

```text
dp(i, val) = dp(i + 1, val + nums[i]) + dp(i + 1, val - nums[i])
```

Memo key:

```text
(i, val)
```

This is 2-D DP even though it uses a dictionary, because the state has two variables.

Optimization: subset-sum transformation.

Let:

```text
P = sum of numbers assigned +
N = sum of numbers assigned -

P - N = target
P + N = total
```

Add equations:

```text
2P = target + total
P = (target + total) / 2
```

So the problem becomes:

```text
How many subsets sum to (target + total) // 2?
```

Edge checks:

```python
total = sum(nums)

if abs(target) > total or (total + target) % 2:
    return 0

subset_target = (total + target) // 2
```

Then 1-D subset-count DP:

```python
dp = [0] * (subset_target + 1)
dp[0] = 1

for num in nums:
    for amt in range(subset_target, num - 1, -1):
        dp[amt] += dp[amt - num]
```

Loop direction:

```text
Backward because each num can only be used once.
```

---

### 309. Best Time to Buy and Sell Stock with Cooldown

Main lesson: for state DP, O(1) space can be easier.

States:

```text
hold = best profit if holding stock after today
sold = best profit if sold today
rest = best profit if not holding and not sold today
```

Transitions:

```text
new_hold = max(old_hold, old_rest - price)
new_sold = old_hold + price
new_rest = max(old_rest, old_sold)
```

Initialization:

```python
hold = -prices[0]
sold = float("-inf")
rest = 0
```

Answer:

```text
max(sold, rest)
```

Do not return `hold`, because holding means the stock has not been cashed out.

Key distinction:

```text
Buy and sell are actions.
Hold, sold, and rest are states after the day ends.
```

---

### 97. Interleaving String

Main lesson: be careful with indexing.

State:

```text
dp[i][j] = whether s1[:i] and s2[:j] can form s3[:i+j]
```

Length check:

```python
if len(s1) + len(s2) != len(s3):
    return False
```

Transition:

```text
dp[i][j] is true if either:

1. s1 contributed the last character:
   dp[i-1][j] and s1[i-1] == s3[i+j-1]

2. s2 contributed the last character:
   dp[i][j-1] and s2[j-1] == s3[i+j-1]
```

Prefix indexing rule:

```text
If dp uses prefixes of length i and j,
actual character indices are i - 1 and j - 1.
```

---

### 329. Longest Increasing Path in a Matrix

Main lesson: hards often combine multiple concepts.

State:

```text
dfs(r, c) = longest increasing path starting from matrix[r][c]
```

Transition:

```text
Try all 4 neighbors.
Only move to neighbors with a larger value.
```

Memoization:

```text
Once dfs(r, c) is computed, it never changes.
```

Answer:

```text
max dfs(r, c) over all cells
```

Why no visited set?

```text
Strictly increasing moves cannot form a cycle.
```

Complexity:

```text
Time: O(rows * cols)
Space: O(rows * cols)
```

Main insight:

```text
This hard is a combination hard:
grid traversal + DFS + memoization + DP state.
```

---

### 1143. Longest Common Subsequence

Main lesson: if indexes feel complicated, draw the table.

State:

```text
dp[i][j] = length of LCS between text1[i:] and text2[j:]
```

Transition:

```text
If text1[i] == text2[j]:
    dp[i][j] = 1 + dp[i+1][j+1]

Else:
    dp[i][j] = max(dp[i+1][j], dp[i][j+1])
```

Meaning:

```text
If chars match, use both.
If chars do not match, skip one character from either string.
```

Loop direction:

```text
Bottom-right to top-left for suffix DP.
```

---

### 647. Palindromic Substrings

Main lesson:

```text
Palindromes originate from a center.
```

For each index:

```text
expand(i, i)     # odd length
expand(i, i + 1) # even length
```

Count each successful expansion.

Complexity:

```text
Time: O(n^2)
Space: O(1)
```

---

### 5. Longest Palindromic Substring

Same center expansion as Palindromic Substrings.

Main indexing lesson:

```text
After the expansion loop ends, l and r are one step too far.
The palindrome is s[l + 1 : r].
```

Track the longest substring found.

---

### 416. Partition Equal Subset Sum

Main lesson:

```text
When each item can only be used once, loop backward.
```

Reduction:

```text
If total sum is odd, return False.
Otherwise target = total // 2.
```

State:

```text
dp[amt] = can we make amt using numbers processed so far?
```

Base case:

```python
dp[0] = True
```

Transition:

```python
for num in nums:
    for amt in range(target, num - 1, -1):
        dp[amt] = dp[amt] or dp[amt - num]
```

Backward loop prevents using the same num twice.

---

### 91. Decode Ways

Main lesson:

```text
A path is valid only if it reaches the end.
```

State:

```text
dp(i) = number of ways to decode s[i:]
```

Base cases:

```text
if i == len(s): return 1
if s[i] == "0": return 0
```

Transition:

```text
ways = dp(i + 1)

if s[i:i+2] is between "10" and "26":
    ways += dp(i + 2)
```

Important:

```text
Do not add +1 just for choosing a digit.
The base case counts completed valid paths.
```

---

### 322. Coin Change

Main lesson:

```text
DP can depend on many previous states.
```

State:

```text
dp[amt] = minimum number of coins needed to make amt
```

Base case:

```python
dp[0] = 0
```

Transition:

```text
For each amount, try every coin as the last coin.
```

```python
dp[amt] = min(dp[amt], 1 + dp[amt - coin])
```

This is different from Coin Change II:

```text
Coin Change I asks for minimum coins.
Coin Change II asks for number of combinations.
```

---

### 300. Longest Increasing Subsequence

O(n²) DP state:

```text
dp[i] = length of longest increasing subsequence starting at i
```

Transition:

```text
For every j > i:
    if nums[j] > nums[i]:
        dp[i] = max(dp[i], 1 + dp[j])
```

O(n log n) optimization:

```text
tails[k] = smallest possible tail value for an increasing subsequence of length k + 1
```

Key idea:

```text
A smaller tail is better because it leaves more room for future numbers.
```

The `tails` list is not necessarily the actual subsequence.

---

### 64. Minimum Path Sum

Main lesson:

```text
Be careful whether you are reading from grid or dp.
```

State:

```text
dp[r][c] = minimum path sum to reach cell (r, c)
```

Transition:

```text
dp[r][c] = grid[r][c] + min(dp[r-1][c], dp[r][c-1])
```

Do not accidentally use `grid[r-1][c]` instead of `dp[r-1][c]`.

---

### 139. Word Break

Main lesson:

```text
dp[i] often means the solution where a boundary is at index i.
```

State:

```text
dp[i] = whether s[:i] can be segmented
```

Transition:

```text
dp[i] is true if there exists j < i such that:
dp[j] is true and s[j:i] is in wordDict
```

Use a set for wordDict.

---

### 152. Maximum Product Subarray

Main lesson:

```text
Think about properties of the operation requested.
```

For multiplication, negatives can flip min into max.

State:

```text
max_here = maximum product ending here
min_here = minimum product ending here
```

Transition considers:

```text
nums[i]
nums[i] * max_here
nums[i] * min_here
```

Need both max and min because:

```text
negative * negative = positive
```

---

### 198. House Robber

Main lesson:

```text
Think about the choice and previous subproblems.
```

State:

```text
dp[i] = max money robbing houses up to i
```

Choice:

```text
rob current: nums[i] + dp[i-2]
skip current: dp[i-1]
```

Transition:

```text
dp[i] = max(dp[i-1], nums[i] + dp[i-2])
```

---

### 213. House Robber II

Main lesson:

```text
Circular constraint often means split into cases.
```

Since first and last houses are adjacent:

```text
answer = max(
    rob houses 0 through n-2,
    rob houses 1 through n-1
)
```

Use House Robber I as a helper.

---

### 62. Unique Paths

Main lesson:

```text
Grids are useful in 2-D DP.
grid[r][c] is the mental model.
```

State:

```text
dp[r][c] = number of ways to reach cell (r, c)
```

Transition:

```text
dp[r][c] = dp[r-1][c] + dp[r][c-1]
```

Base:

```text
First row and first column have 1 way each.
```

---

### 121. Best Time to Buy and Sell Stock

This is DP/greedy-like.

State idea:

```text
min_price_so_far
max_profit_so_far
```

Transition:

```text
At each price:
    possible profit = price - min_price_so_far
    update max_profit
    update min_price_so_far
```

---

### 53. Maximum Subarray

Main lesson:

```text
Drop dead weight at each step.
```

Kadane state:

```text
curr = best subarray sum ending here
best = best seen overall
```

Transition:

```text
curr = max(nums[i], curr + nums[i])
best = max(best, curr)
```

Mental model:

```text
If the running sum is negative, it hurts future subarrays.
Drop it.
```

---

### 70. Climbing Stairs

State:

```text
dp[i] = number of ways to reach step i
```

Transition:

```text
dp[i] = dp[i-1] + dp[i-2]
```

This is Fibonacci-style DP.

---

### 55. Jump Game

Greedy / DP-like.

State idea:

```text
farthest = farthest index reachable so far
```

Transition:

```text
If i > farthest, return False.
Otherwise update farthest = max(farthest, i + nums[i]).
```

Main lesson:

```text
Sometimes one greedy state summarizes all previous possibilities.
```

---

### 746. Min Cost Climbing Stairs

State:

```text
dp[i] = min cost to reach step i
```

Transition:

```text
dp[i] = cost[i] + min(dp[i-1], dp[i-2])
```

Optimization:

```text
Only need two previous states, not the whole array.
```

---

## 4. Loop Direction Cheat Sheet

```text
1-D DP depending on previous states:
    loop forward

Suffix string DP depending on i+1/j+1:
    loop backward

Prefix string DP depending on previous prefixes:
    loop forward

Use each item once:
    loop amount backward

Unlimited item reuse:
    loop amount forward

State-machine over time:
    loop days forward

DFS + memo:
    recursion decides order
```

---

## 5. Space Optimization Cheat Sheet

Space optimization is usually possible when the recurrence only needs a fixed number of previous rows/states.

Examples:

```text
House Robber:
    dp[i] only depends on i-1 and i-2 -> O(1)

Edit Distance:
    dp[i][j] depends on current row and next row -> O(n)

Coin Change II:
    2-D amount/coin table can compress to O(amount)

Target Sum:
    subset-sum version compresses to O(subset_target)

Stock Cooldown:
    fixed states hold/sold/rest -> O(1)
```

Do not optimize too early. First make the state and recurrence clear.

---

## 6. Common Mistakes to Watch

### Mistake 1: Wrong matrix dimensions

If using suffix DP:

```text
Need len(string) + 1
```

because the empty suffix is a valid base case.

### Mistake 2: Drawing the matrix transposed

Code uses:

```python
dp[row][col]
```

So if rows are word1 and columns are word2, draw it that way.

### Mistake 3: Forgetting the skip case

In Coin Change II:

```text
Every cell has skip current coin.
Only if coin fits do we add use current coin.
```

### Mistake 4: Using current item multiple times accidentally

If each item can only be used once, loop backward.

### Mistake 5: Off-by-one in prefix DP

If state uses prefixes of length `i`, then the actual character is at `i - 1`.

### Mistake 6: Off-by-one after expanding pointers

If a while loop moves pointers until invalid, the answer may be one step back.

Example:

```python
s[l + 1 : r]
```

for longest palindrome.

### Mistake 7: Confusing actions and states

In Stock Cooldown:

```text
buy/sell = actions
hold/sold/rest = states
```

DP stores states, not necessarily actions.

---

## 7. Interview Explanation Template

When explaining a DP problem, say:

```text
I’ll define dp[...] as ...
At each state, I have these choices ...
The recurrence is ...
The base cases are ...
The answer is ...
The complexity is ...
```

Example:

```text
For Edit Distance, dp[i][j] is the minimum number of edits to convert
word1[i:] into word2[j:].

If the current characters match, no edit is needed.
Otherwise, I try insert, delete, and replace, and take the minimum.

The base cases are when either suffix is empty.
The answer is dp[0][0].
Time is O(mn), space is O(mn), with possible O(n) compression.
```

---

## 8. Personal Takeaways

Your strongest DP shapes so far:

```text
Grid DP / DFS memo
1-D DP after state is clear
Palindrome center expansion
```

Your main friction points:

```text
2-D indexing
prefix vs suffix definitions
matrix orientation
remembering skip/use cases
```

Best practice habit:

```text
For any 2-D DP, draw the table first.
Label rows, columns, base row/column, and dependency arrows.
Then code.
```

