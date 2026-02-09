#!/usr/bin/env python3
"""
Backfill an existing monitoring CSV with Z-score, trend, and prediction columns.
Usage: python scripts/backfill_csv_zscore.py <input.csv> <output.csv>
Example: python scripts/backfill_csv_zscore.py ~/Downloads/monitoring_*.csv data/monitoring_VMW-Jira.csv
"""
import csv
import sys
from datetime import datetime, timezone

WINDOW_MINUTES = 60
N_MAX, M_MAX = 1.75, 2.75

def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None

def higher_is_better(key):
    return "mem_avail_pct" in key or "heap_avail_pct" in key

def z_color(z):
    if z is None:
        return ""
    a = abs(z)
    if a <= N_MAX:
        return "green"
    if a <= M_MAX:
        return "yellow"
    return "red"

def pred_label(trend_dir, key):
    if trend_dir == 0:
        return "neutral"
    if higher_is_better(key):
        return "improve" if trend_dir > 0 else "worsen"
    return "worsen" if trend_dir > 0 else "improve"

def parse_ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()

def main():
    if len(sys.argv) < 3:
        print("Usage: backfill_csv_zscore.py <input.csv> <output.csv>", file=sys.stderr)
        sys.exit(1)
    inp, out = sys.argv[1], sys.argv[2]

    with open(inp) as f:
        r = csv.DictReader(f)
        rows = list(r)
        base_columns = r.fieldnames

    metric_cols = [c for c in base_columns if c != "timestamp"]
    extended_columns = []
    for c in base_columns:
        extended_columns.append(c)
        if c != "timestamp":
            extended_columns.extend([c + "_z", c + "_z_color", c + "_trend", c + "_pred"])

    out_rows = []
    for i, row in enumerate(rows):
        ts = parse_ts(row["timestamp"])
        cutoff = ts - WINDOW_MINUTES * 60
        window = [r for r in rows if parse_ts(r["timestamp"]) >= cutoff]

        out_row = {}
        for col in metric_cols:
            vals = []
            for w in window:
                v = num(w.get(col))
                if v is not None:
                    vals.append(v)
            cur = num(row.get(col))
            out_row[col] = row.get(col, "")

            if cur is None:
                out_row[col + "_z"] = ""
                out_row[col + "_z_color"] = ""
            elif len(vals) < 2:
                out_row[col + "_z"] = ""
                out_row[col + "_z_color"] = "green"
            else:
                mean = sum(vals) / len(vals)
                var = sum((x - mean) ** 2 for x in vals) / len(vals)
                std = var ** 0.5
                if std == 0:
                    z = 0.0
                else:
                    z = (cur - mean) / std
                out_row[col + "_z"] = round(z, 3)
                out_row[col + "_z_color"] = z_color(z)

            if i == 0:
                out_row[col + "_trend"] = ""
                out_row[col + "_pred"] = "neutral"
            else:
                prev = num(rows[i - 1].get(col))
                if prev is None or cur is None:
                    out_row[col + "_trend"] = ""
                    out_row[col + "_pred"] = "neutral"
                elif cur > prev:
                    out_row[col + "_trend"] = "up"
                    out_row[col + "_pred"] = pred_label(1, col)
                elif cur < prev:
                    out_row[col + "_trend"] = "down"
                    out_row[col + "_pred"] = pred_label(-1, col)
                else:
                    out_row[col + "_trend"] = ""
                    out_row[col + "_pred"] = "neutral"

        out_row["timestamp"] = row["timestamp"]
        out_rows.append(out_row)

    import os
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=extended_columns, extrasaction="ignore")
        w.writeheader()
        w.writerows(out_rows)

    print(f"Wrote {len(out_rows)} rows to {out}")

if __name__ == "__main__":
    main()
