"""
Flatten collect_all() output to a single row dict and column list for CSV/series.
Matches the frontend flattenSnapshot() structure (including Apdex).
"""
from datetime import datetime, timezone
from typing import Any


def flatten_snapshot(data: dict) -> tuple[list[str], dict[str, Any]]:
    """
    Flatten data from collect_all() to (columns, row).
    row keys match frontend: app_0_load_1m, app_0_apdex, db_0_load_1m, etc.
    """
    row: dict[str, Any] = {"timestamp": datetime.now(timezone.utc).isoformat()}
    columns = ["timestamp"]
    servers = data.get("servers") or []
    db_nodes = data.get("db_nodes") or []

    for i, s in enumerate(servers):
        prefix = f"app_{i}_"
        mem = s.get("memory") or {}
        load = s.get("load_avg_1_5_15") or [0, 0, 0]
        mem_used_pct = mem.get("utilization_percent")
        mem_avail_pct = (100 - mem_used_pct) if mem_used_pct is not None else ""
        swap_pct = mem.get("swap_utilization_percent")

        keys: list[tuple[str, Any]] = [
            (prefix + "load_1m", load[0] if len(load) > 0 else 0),
            (prefix + "load_5m", load[1] if len(load) > 1 else 0),
            (prefix + "load_15m", load[2] if len(load) > 2 else 0),
            (prefix + "cpu_percent", s.get("cpu_percent")),
            (prefix + "mem_util_pct", mem_used_pct),
            (prefix + "mem_avail_pct", mem_avail_pct),
            (prefix + "swap_util_pct", swap_pct),
            (prefix + "incoming", s.get("incoming_connections")),
            (prefix + "db_connections", s.get("db_connection_count")),
        ]

        main_pid = None
        by_pid = s.get("connections_by_pid") or {}
        if by_pid:
            main_pid = next(iter(by_pid.keys()))
        processes = s.get("processes") or []
        jvm_by_pid = s.get("jvm_by_pid") or {}
        if not main_pid and processes:
            for p in processes:
                pid = p.get("pid")
                if pid and str(pid) in jvm_by_pid:
                    main_pid = str(pid)
                    break
            if not main_pid and processes:
                main_pid = str(processes[0].get("pid", ""))

        main_process = None
        for p in processes:
            if str(p.get("pid", "")) == main_pid:
                main_process = p
                break

        heap_max_mb = s.get("heap_max_mb")
        heap_used_mb = jvm_by_pid.get(main_pid, {}).get("heap_used_mb") if main_pid else None
        non_heap_mb = jvm_by_pid.get(main_pid, {}).get("non_heap_mb") if main_pid else None
        heap_used_pct = (100 * heap_used_mb / heap_max_mb) if (heap_max_mb and heap_used_mb is not None) else ""
        heap_avail_pct = (
            (100 * max(0, heap_max_mb - heap_used_mb) / heap_max_mb)
            if (heap_max_mb and heap_used_mb is not None)
            else ""
        )
        non_heap_pct = (100 * non_heap_mb / heap_max_mb) if (heap_max_mb and non_heap_mb is not None) else ""
        rss_mb = (main_process.get("rss_kb") / 1024) if main_process and main_process.get("rss_kb") is not None else None
        rss_pct_heap = (100 * rss_mb / heap_max_mb) if (heap_max_mb and rss_mb is not None) else ""
        process_cpu = main_process.get("cpu_percent") if main_process else ""

        keys.extend([
            (prefix + "heap_used_mb", heap_used_mb),
            (prefix + "heap_used_pct", heap_used_pct),
            (prefix + "heap_avail_pct", heap_avail_pct),
            (prefix + "non_heap_pct", non_heap_pct),
            (prefix + "rss_pct_heap", rss_pct_heap),
            (prefix + "process_cpu", process_cpu),
        ])

        access5 = s.get("access_log_5m")
        keys.extend([
            (prefix + "access_requests", access5.get("request_count") if access5 else None),
            (prefix + "access_unique_users", access5.get("unique_users") if access5 else None),
            (prefix + "rt_99p_sec", access5.get("response_time_99p_sec") if access5 else None),
            (prefix + "rt_95p_sec", access5.get("response_time_95p_sec") if access5 else None),
            (prefix + "rt_90p_sec", access5.get("response_time_90p_sec") if access5 else None),
            (prefix + "rt_avg_sec", access5.get("response_time_avg_sec") if access5 else None),
            (prefix + "apdex", access5.get("apdex") if access5 else None),
            (prefix + "apdex_satisfied", access5.get("apdex_satisfied") if access5 else None),
            (prefix + "apdex_neutral", access5.get("apdex_neutral") if access5 else None),
            (prefix + "apdex_unsatisfied", access5.get("apdex_unsatisfied") if access5 else None),
        ])

        app5 = s.get("app_log_5m")
        keys.extend([
            (prefix + "app_log_lines", app5.get("line_count") if app5 else None),
            (prefix + "app_log_threads", app5.get("unique_threads") if app5 else None),
        ])

        for k, v in keys:
            columns.append(k)
            row[k] = v if v is not None else ""

    apdex_global = data.get("apdex_global")
    if apdex_global:
        columns.extend(["apdex_global", "apdex_global_satisfied", "apdex_global_neutral", "apdex_global_unsatisfied"])
        row["apdex_global"] = apdex_global.get("apdex") if apdex_global.get("apdex") is not None else ""
        row["apdex_global_satisfied"] = apdex_global.get("apdex_satisfied") if apdex_global.get("apdex_satisfied") is not None else ""
        row["apdex_global_neutral"] = apdex_global.get("apdex_neutral") if apdex_global.get("apdex_neutral") is not None else ""
        row["apdex_global_unsatisfied"] = apdex_global.get("apdex_unsatisfied") if apdex_global.get("apdex_unsatisfied") is not None else ""

    access_global = data.get("access_log_5m_global")
    if access_global:
        columns.extend([
            "access_global_requests",
            "access_global_unique_users",
            "rt_global_99p_sec",
            "rt_global_95p_sec",
            "rt_global_90p_sec",
            "rt_global_avg_sec",
        ])
        row["access_global_requests"] = access_global.get("request_count") if access_global.get("request_count") is not None else ""
        row["access_global_unique_users"] = access_global.get("unique_users") if access_global.get("unique_users") is not None else ""
        row["rt_global_99p_sec"] = access_global.get("response_time_99p_sec") if access_global.get("response_time_99p_sec") is not None else ""
        row["rt_global_95p_sec"] = access_global.get("response_time_95p_sec") if access_global.get("response_time_95p_sec") is not None else ""
        row["rt_global_90p_sec"] = access_global.get("response_time_90p_sec") if access_global.get("response_time_90p_sec") is not None else ""
        row["rt_global_avg_sec"] = access_global.get("response_time_avg_sec") if access_global.get("response_time_avg_sec") is not None else ""

    for i, d in enumerate(db_nodes):
        prefix = f"db_{i}_"
        mem = d.get("memory") or {}
        load = d.get("load_avg_1_5_15") or [0, 0, 0]
        mem_used_pct = mem.get("utilization_percent")
        mem_avail_pct = (100 - mem_used_pct) if mem_used_pct is not None else ""
        swap_pct = mem.get("swap_utilization_percent")
        keys = [
            (prefix + "load_1m", load[0] if len(load) > 0 else 0),
            (prefix + "load_5m", load[1] if len(load) > 1 else 0),
            (prefix + "load_15m", load[2] if len(load) > 2 else 0),
            (prefix + "cpu_percent", d.get("cpu_percent")),
            (prefix + "mem_util_pct", mem_used_pct),
            (prefix + "mem_avail_pct", mem_avail_pct),
            (prefix + "swap_util_pct", swap_pct),
            (prefix + "connections", d.get("incoming_connections")),
        ]
        for k, v in keys:
            columns.append(k)
            row[k] = v if v is not None else ""

    return columns, row
