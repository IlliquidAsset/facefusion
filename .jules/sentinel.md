# Sentinel Journal

This journal tracks critical learnings and patterns discovered during maintenance runs.

## Format
```markdown
## YYYY-MM-DD - [Title]
**Domain:** [Memory|Performance|UX|Dependencies|Docs]
**Learning:** [Insight]
**Action:** [How to apply next time]
```

## 2026-01-29 - BoundedVideoPool Implementation
**Domain:** Memory
**Learning:** cv2.VideoCapture objects must be explicitly released and cached in a bounded structure to prevent file descriptor and memory leaks. Inheriting from OrderedDict and overriding __setitem__ provides a clean LRU implementation.
**Action:** Use BoundedVideoPool pattern for any heavy resource caching.
