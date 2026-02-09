# Storage growth projection

Based on current data in `data/` and the 60-second collection interval.

## What grows

| Item | Growth | Notes |
|------|--------|--------|
| `data/monitoring_{env}.csv` | **Grows** | One row appended per collection (every 60s). |
| `data/latest_{env}.json` | **Fixed** | Overwritten each run; ~15–35 KB per env. |
| App logs | **None** | No file logging by default (stdout/stderr only). |

So only the **CSV files** contribute to disk growth.

## Measured sizes (reference)

- **VMW-Jira** CSV: ~2.17 MB for 878 rows → **~2.5 KB per row** (header ~11 KB once).
- One data row: **~2.3 KB** (typical; depends on number of app/DB nodes and columns).

Collection interval: **60 seconds** → **1 row per minute** per environment.

## Per-environment projection

| Period | Rows | CSV size (approx.) |
|--------|------|---------------------|
| **1 day** | 1,440 | **~3.4 MB** |
| **1 week** | 10,080 | **~24 MB** |
| **1 month (30 days)** | 43,200 | **~101 MB** |

Formula: `rows = (days × 24 × 60)`, `size ≈ 11 KB + rows × 2.5 KB`.

Environments with fewer nodes/columns may use **~2–2.5 KB/row**; with more nodes, **~2.5–3 KB/row**.

## All environments (e.g. 3 envs)

| Period | Total CSV (3 envs) |
|--------|---------------------|
| 1 week | **~72 MB** |
| 1 month | **~303 MB** |

## Cleanup / archive criteria (suggested)

1. **Retention by age**  
   Keep only the last N days (e.g. 30). Delete or archive CSV rows (or rotate files) older than that.

2. **Max size per CSV**  
   When `monitoring_{env}.csv` exceeds a cap (e.g. 100 MB), archive the oldest half or move to `data/archive/` and start a new file.

3. **Cron + script**  
   - Option A: Truncate/rewrite CSV to last 30 days (rewrite header + recent rows).  
   - Option B: `gzip` and move old CSVs to `data/archive/` and optionally delete after 90 days.

4. **No change to app**  
   The app only appends; it does not delete. Cleanup can be external (cron job or manual).

## Summary for one environment

- **1 week:** ~**24 MB**  
- **1 month:** ~**101 MB**  
- Use **~2.5 KB/row** and **1 row/min** for your own interval or env count.
