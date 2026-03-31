## 2024-05-23 - Initial Setup
**Learning:** Performance journaling helps track impactful changes and avoid repeating mistakes.
**Action:** Always check this journal before starting optimization tasks.

## 2024-05-23 - Platform Check Optimization
**Learning:** `platform.system()` calls are relatively expensive (~240ns) and should be cached if used frequently in loops or hot paths. Since the OS is static during runtime, this value should be cached at module level. Module-level caching provides a significant speedup (~5x).
**Action:** Use module-level constants (cached boolean results) for static system values instead of repeated function calls or string comparisons.

## 2025-05-23 - FaceDataset In-Memory Caching
**Learning:** The `FaceDataset` used for InstantID training repeatedly loaded and processed the same small set of images (max 1000) from disk every epoch. This I/O bound operation made training significantly slower (1.78s vs 0.11s for 10 epochs). For small datasets that fit in RAM, eager caching is a massive win.
**Action:** Default to in-memory caching for datasets known to be small (< 2GB) to eliminate I/O overhead.

## 2024-05-23 - Scalar Math Optimization
**Learning:** Using `numpy` functions (`arctan2`, `degrees`, `linspace`, `argmin`) for simple scalar calculations incurs significant overhead (e.g., array allocation, dispatch). Pure Python `math` operations are much faster (~6-7x) for single-value logic.
**Action:** Prefer `math` module over `numpy` when processing individual scalars, especially in hot loops like per-face angle estimation.

## 2025-05-23 - NumPy Array Allocation and Dtypes
**Learning:** `numpy.ones().astype(float32)` creates a default `float64` array then copies it to `float32`, which is ~82% slower than `numpy.ones(..., dtype=float32)`. Re-creating constant arrays (like normalization means) in tight loops adds unnecessary allocation overhead, even if small.
**Action:** Always use the `dtype` argument during array creation instead of `astype()` immediately after. Hoist constant array definitions to module level to avoid re-allocation in hot paths.

## 2025-05-24 - Missing Optimization Recovery
**Learning:** Sometimes documentation (AGENTS.md) describes optimizations that are missing from the codebase (likely lost in a revert or bad merge).
**Action:** When seeing performance claims in documentation, verify they exist in code. If missing, implementing them is a low-hanging fruit for performance wins (~40% in this case).
