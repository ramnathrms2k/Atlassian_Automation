"""
SSH to Jira app nodes, gather connection counts, DB connections, and system metrics.
"""
import os
import re
import logging
from typing import Any

import paramiko

from app.dbconfig_parser import parse_db_host_port, parse_db_from_server_xml
from app.config_loader import get_config, get_servers_full_hostnames

logger = logging.getLogger(__name__)


def _ssh_run(host: str, user: str, command: str, timeout: int = 30) -> tuple[str, str, int]:
    """Run command over SSH; return (stdout, stderr, exit_code)."""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            host,
            username=user,
            timeout=10,
            allow_agent=True,
            look_for_keys=True,
        )
        _, stdout, stderr = client.exec_command(command, timeout=timeout)
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        code = stdout.channel.recv_exit_status()
        return (out, err, code)
    finally:
        client.close()


def _get_dbconfig_remote(host: str, user: str, path: str, timeout: int) -> str:
    out, err, code = _ssh_run(host, user, f"cat {path}", timeout)
    if code != 0:
        logger.warning("Failed to read dbconfig on %s: %s", host, err or out)
        return ""
    return out


def _parse_xmx_mb(content: str) -> int | None:
    """
    Parse all -Xmx and JVM_MAXIMUM_MEMORY from setenv.sh; return the largest heap in MB.
    Uses the maximum so we get the main Jira JVM heap (setenv often has 512m for something
    else and a much larger -Xmx for the actual Jira process).
    """
    if not content:
        return None

    def to_mb(num: int, suffix: str) -> int:
        s = (suffix or "m").lower()
        if s == "k":
            return num // 1024
        if s == "m":
            return num
        if s == "g":
            return num * 1024
        return num

    candidates: list[int] = []
    for m in re.finditer(r"-Xmx(\d+)([kKmMgG])?", content):
        candidates.append(to_mb(int(m.group(1)), m.group(2)))
    for m in re.finditer(r"JVM_MAXIMUM_MEMORY\s*=\s*[\"']?(\d+)([kKmMgG])?", content, re.I):
        candidates.append(to_mb(int(m.group(1)), m.group(2)))
    return max(candidates) if candidates else None


def _parse_jstat_gc(output: str) -> dict[str, float] | None:
    """
    Parse `jstat -gc <pid>` output. Returns heap_used_mb, heap_capacity_mb, non_heap_mb.
    Columns: S0C S1C S0U S1U EC EU OC OU MC MU CCSC CCSU ...
    Heap used = S0U+S1U+EU+OU (KB), capacity = S0C+S1C+EC+OC (KB), non-heap = MU+CCSU (KB).
    """
    lines = [l.strip() for l in output.strip().splitlines() if l.strip()]
    if len(lines) < 2:
        return None
    parts = lines[-1].split()
    if len(parts) < 12:
        return None
    try:
        s0u = float(parts[2])
        s1u = float(parts[3])
        eu = float(parts[5])
        ou = float(parts[7])
        s0c = float(parts[0])
        s1c = float(parts[1])
        ec = float(parts[4])
        oc = float(parts[6])
        mu = float(parts[9])
        ccsu = float(parts[11])
    except (ValueError, IndexError):
        return None
    heap_used_kb = s0u + s1u + eu + ou
    heap_capacity_kb = s0c + s1c + ec + oc
    non_heap_kb = mu + ccsu
    return {
        "heap_used_mb": round(heap_used_kb / 1024, 1),
        "heap_capacity_mb": round(heap_capacity_kb / 1024, 1),
        "non_heap_mb": round(non_heap_kb / 1024, 1),
    }


def _parse_ss_tpn(output: str) -> list[dict]:
    """
    Parse `ss -tpn` output. Lines like:
    ESTAB  0  0  192.168.1.1:8080  10.0.0.2:45678  users:(("java",pid=1234,fd=20))
    Return list of {local_addr, local_port, remote_addr, remote_port, pid, process}.
    """
    rows = []
    for line in output.splitlines():
        line = line.strip()
        if not line or line.startswith("State"):
            continue
        # ESTAB  0  0  local:port  remote:port  users:(("proc",pid=123,fd=1))
        parts = line.split()
        if len(parts) < 5:
            continue
        try:
            local = parts[3]
            remote = parts[4]
            local_host, _, local_port = local.rpartition(":")
            remote_host, _, remote_port = remote.rpartition(":")
            pid = None
            process = None
            if len(parts) >= 6:
                m = re.search(r'pid=(\d+)', parts[5])
                if m:
                    pid = int(m.group(1))
                m = re.search(r'\("([^"]+)"', parts[5])
                if m:
                    process = m.group(1)
            rows.append({
                "local_addr": local_host,
                "local_port": local_port,
                "remote_addr": remote_host,
                "remote_port": remote_port,
                "pid": pid,
                "process": process or "",
            })
        except (ValueError, IndexError):
            continue
    return rows


def _parse_free_m(output: str) -> dict[str, Any]:
    """Parse `free -m` for Mem and Swap: total, used, available/free, utilization %."""
    result = {"total_mb": 0, "used_mb": 0, "available_mb": 0, "utilization_percent": 0.0}
    swap = {"swap_total_mb": 0, "swap_used_mb": 0, "swap_free_mb": 0, "swap_utilization_percent": 0.0}
    for line in output.strip().splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "Mem:" and len(parts) >= 7:
            total = _safe_int(parts[1], 0)
            used = _safe_int(parts[2], 0)
            available = _safe_int(parts[6], 0)
            if total > 0:
                result["total_mb"] = total
                result["used_mb"] = used
                result["available_mb"] = available
                result["utilization_percent"] = round(100.0 * used / total, 1)
        elif parts[0] == "Swap:" and len(parts) >= 4:
            stotal = _safe_int(parts[1], 0)
            sused = _safe_int(parts[2], 0)
            sfree = _safe_int(parts[3], 0)
            swap["swap_total_mb"] = stotal
            swap["swap_used_mb"] = sused
            swap["swap_free_mb"] = sfree
            swap["swap_utilization_percent"] = round(100.0 * sused / stotal, 1) if stotal > 0 else 0.0
    result.update(swap)
    return result


def _normalize_remote_addr(addr: str) -> set[str]:
    """Return set of forms to match: addr itself and, if IPv4-mapped IPv6, the plain IPv4."""
    if not addr:
        return set()
    addr = addr.strip()
    out = {addr}
    # ss often shows IPv4-mapped IPv6: [::ffff:10.74.203.24] or ::ffff:10.74.203.24
    m = re.match(r"^\[?::ffff:(\d+\.\d+\.\d+\.\d+)\]?$", addr)
    if m:
        out.add(m.group(1))
    return out


def _safe_int(v: Any, default: int = 0) -> int:
    """Convert to int; return default if not a valid integer string."""
    if v is None:
        return default
    try:
        return int(v)
    except (ValueError, TypeError):
        return default


def _parse_loadavg(output: str) -> list[float]:
    """Parse /proc/loadavg: first three numbers are 1, 5, 15 min load."""
    parts = output.strip().split()
    if len(parts) >= 3:
        return [float(parts[0]), float(parts[1]), float(parts[2])]
    return [0.0, 0.0, 0.0]


def _parse_proc_stat_cpu(output: str) -> float:
    """
    Parse first line of /proc/stat (cpu ...) and return utilization.
    We need two samples to get usage; here we return a single sample and
    the frontend can show "current" or we do one short sleep and sample again.
    For simplicity we do two quick reads with 1s sleep on the server.
    """
    lines = output.strip().splitlines()
    for line in lines:
        if line.startswith("cpu "):
            parts = line.split()
            # user nice system idle iowait irq softirq steal guest
            if len(parts) >= 5:
                try:
                    user = int(parts[1])
                    nice = int(parts[2])
                    system = int(parts[3])
                    idle = int(parts[4])
                    iowait = int(parts[5]) if len(parts) > 5 else 0
                    total = user + nice + system + idle + iowait
                    if total:
                        return round(100.0 * (total - idle - iowait) / total, 1)
                except (ValueError, IndexError):
                    pass
            break
    return 0.0


def _get_cpu_util_remote(host: str, user: str, timeout: int) -> float:
    """Read /proc/stat twice with 1s gap to compute CPU utilization."""
    cmd = "a=$(cat /proc/stat); sleep 1; b=$(cat /proc/stat); echo \"$a\"; echo '---'; echo \"$b\""
    out, _, code = _ssh_run(host, user, cmd, timeout=timeout)
    if code != 0:
        return 0.0
    parts = out.split("\n---\n")
    if len(parts) != 2:
        return 0.0
    def parse_idle(line):
        for l in line.splitlines():
            if l.startswith("cpu "):
                p = l.split()
                if len(p) >= 5:
                    return int(p[4]) + (int(p[5]) if len(p) > 5 else 0), sum(int(x) for x in p[1:6] if x.isdigit())
        return 0, 0
    idle1, total1 = parse_idle(parts[0])
    idle2, total2 = parse_idle(parts[1])
    if total2 - total1 == 0:
        return 0.0
    return round(100.0 * (1 - (idle2 - idle1) / (total2 - total1)), 1)


def _parse_ps(output: str) -> list[dict]:
    """Parse `ps -o pid,rss,%cpu,comm -q <pids>` or similar. rss in KB."""
    rows = []
    lines = output.strip().splitlines()
    if len(lines) < 2:
        return rows
    header = lines[0].split()
    try:
        pid_idx = header.index("PID")
    except ValueError:
        return rows
    rss_idx = header.index("RSS") if "RSS" in header else -1
    cpu_idx = header.index("%CPU") if "%CPU" in header else -1
    comm_idx = header.index("COMMAND") if "COMMAND" in header else (len(header) - 1)
    for line in lines[1:]:
        parts = line.split(None, comm_idx)
        if len(parts) <= pid_idx:
            continue
        try:
            pid = int(parts[pid_idx])
            rss_kb = int(parts[rss_idx]) if rss_idx >= 0 and rss_idx < len(parts) else 0
            cpu = float(parts[cpu_idx]) if cpu_idx >= 0 and cpu_idx < len(parts) else 0.0
            comm = parts[comm_idx] if len(parts) > comm_idx else ""
            rows.append({"pid": pid, "rss_kb": rss_kb, "cpu_percent": cpu, "comm": comm.strip()})
        except (ValueError, IndexError):
            continue
    return rows


def collect_node(host: str, config: dict) -> dict[str, Any]:
    """
    Gather metrics for one Jira app node. Returns a dict with:
    - host, db_host, db_port
    - incoming_connections (to jira_app_port)
    - db_connections (count and list with pid)
    - connections_by_pid (incoming + db grouped by pid)
    - load_avg_1_5_15
    - memory (total_mb, used_mb, available_mb, utilization_percent)
    - cpu_percent
    - processes (list of {pid, rss_kb, cpu_percent, comm})
    - error (if any)
    """
    user = config.get("ssh_user", "svcjira")
    timeout = config.get("app", {}).get("ssh_command_timeout", 30)
    paths = config.get("paths", {})
    app_type = (config.get("app_type") or "jira").lower()
    app_port = config.get("app_port") or config.get("jira_app_port", 8080)
    dbconfig_path = paths.get("dbconfig", "/export/jirahome/dbconfig.xml")
    server_xml_path = paths.get("server_xml", "/export/confluence/conf/server.xml")

    result = {
        "host": host,
        "app_type": app_type,
        "app_version": None,
        "db_host": None,
        "db_port": None,
        "heap_max_mb": None,
        "jira_version": None,
        "jvm_by_pid": {},
        "incoming_connections": 0,
        "db_connections": [],
        "db_connection_count": 0,
        "connections_by_pid": {},
        "load_avg_1_5_15": [0.0, 0.0, 0.0],
        "memory": {},
        "cpu_percent": 0.0,
        "processes": [],
        "error": None,
    }

    # 1) DB config (Jira: dbconfig.xml; Confluence: server.xml)
    try:
        if app_type == "confluence":
            xml_content = _get_dbconfig_remote(host, user, server_xml_path, timeout)
            db_info = parse_db_from_server_xml(xml_content)
        else:
            xml_content = _get_dbconfig_remote(host, user, dbconfig_path, timeout)
            db_info = parse_db_host_port(xml_content)
        if db_info:
            result["db_host"], result["db_port"] = db_info
    except Exception as e:
        result["error"] = str(e)
        return result

    # Resolve DB host to IP(s) on the node so we match ss output (which often shows IPs)
    db_hosts_to_match = set()
    if result["db_host"]:
        dh = result["db_host"].strip()
        db_hosts_to_match.add(dh)
        dh_safe = dh.replace("'", "'\"'\"'")  # escape single quotes for shell
        out, _, _ = _ssh_run(host, user, f"getent hosts '{dh_safe}' 2>/dev/null | awk '{{print $1}}'", timeout)
        for ip in out.strip().splitlines():
            ip = ip.strip()
            if ip and not ip.startswith("#"):
                db_hosts_to_match.add(ip)

    # 2) ss -tpn
    out, err, code = _ssh_run(host, user, "ss -tpn 2>/dev/null || netstat -tpn 2>/dev/null", timeout)
    if code != 0:
        result["error"] = err or "Failed to get connections"
        # Still try memory/load
    else:
        connections = _parse_ss_tpn(out)
        try:
            jira_port_int = int(app_port)
        except (TypeError, ValueError):
            jira_port_int = 8080
        db_port_int = result["db_port"] if isinstance(result["db_port"], int) else _safe_int(result.get("db_port"), 0)
        for c in connections:
            try:
                lp = int(c.get("local_port") or 0)
                rp = int(c.get("remote_port") or 0)
            except (TypeError, ValueError):
                continue
            remote_addr = (c.get("remote_addr") or "").strip()
            if lp == jira_port_int:
                result["incoming_connections"] += 1
            # Match remote addr (ss may show IPv4-mapped IPv6 e.g. [::ffff:10.74.203.24])
            remote_forms = _normalize_remote_addr(remote_addr)
            is_db = (
                result["db_host"]
                and db_port_int
                and rp == db_port_int
                and bool(remote_forms & db_hosts_to_match)
            )
            if is_db:
                result["db_connections"].append(c)
                result["db_connection_count"] += 1
            pid = c.get("pid")
            if pid:
                key = str(pid)
                if key not in result["connections_by_pid"]:
                    result["connections_by_pid"][key] = {"incoming": 0, "db": 0, "pid": pid}
                if lp == jira_port_int:
                    result["connections_by_pid"][key]["incoming"] += 1
                if is_db:
                    result["connections_by_pid"][key]["db"] += 1

    # 2b) Max heap (Xmx) from setenv.sh; Jira version from pom.properties (relative to setenv path)
    setenv_path = paths.get("setenv", "/export/jira/bin/setenv.sh")
    try:
        setenv_out, _, setenv_code = _ssh_run(host, user, f"cat {setenv_path} 2>/dev/null", timeout)
        if setenv_code == 0 and setenv_out:
            xmx = _parse_xmx_mb(setenv_out)
            if xmx and xmx > 0:
                result["heap_max_mb"] = xmx
    except Exception:
        pass
    try:
        # App base = parent of setenv's directory (e.g. /export/jira/bin/setenv.sh -> /export/jira)
        app_base = os.path.dirname(os.path.dirname(setenv_path))
        if app_type == "confluence":
            pom_relative = "confluence/META-INF/maven/com.atlassian.confluence/confluence-webapp/pom.properties"
        else:
            pom_relative = "atlassian-jira/META-INF/maven/com.atlassian.jira/jira-webapp-dist/pom.properties"
        pom_path = f"{app_base}/{pom_relative}"
        pom_out, _, pom_code = _ssh_run(host, user, f"cat {pom_path} 2>/dev/null", timeout)
        if pom_code == 0 and pom_out:
            for line in pom_out.splitlines():
                line = line.strip()
                if line.startswith("version="):
                    ver = line.split("=", 1)[1].strip()
                    result["app_version"] = ver
                    if app_type == "jira":
                        result["jira_version"] = ver
                    break
    except Exception:
        pass

    # 3) Memory
    out, _, _ = _ssh_run(host, user, "free -m", timeout)
    result["memory"] = _parse_free_m(out)

    # 4) Load average
    out, _, _ = _ssh_run(host, user, "cat /proc/loadavg", timeout)
    result["load_avg_1_5_15"] = _parse_loadavg(out)

    # 5) CPU (two samples)
    try:
        result["cpu_percent"] = _get_cpu_util_remote(host, user, timeout)
    except Exception:
        result["cpu_percent"] = 0.0

    # 6) Process stats for PIDs we care about (Java/jira)
    pids = list(result["connections_by_pid"].keys())
    if pids:
        pid_list = ",".join(pids[:50])  # limit
        out, _, _ = _ssh_run(host, user, f"ps -p {pid_list} -o pid,rss,%cpu,comm 2>/dev/null", timeout)
        result["processes"] = _parse_ps(out)
    else:
        # No PIDs from ss; try to get java processes
        out, _, _ = _ssh_run(host, user, "pgrep -f 'jira\\|java' 2>/dev/null | head -20 | xargs ps -o pid,rss,%cpu,comm -p 2>/dev/null", timeout)
        result["processes"] = _parse_ps(out)

    # 7) JVM heap/non-heap via jstat -gc for each Java PID (use same JVM's jstat via /proc/pid/exe)
    for p in result["processes"]:
        pid = p.get("pid")
        comm = (p.get("comm") or "").lower()
        if pid is None or "java" not in comm:
            continue
        try:
            # Use jstat from the same Java install as the process
            cmd = (
                f"JSTAT=$(dirname $(readlink -f /proc/{pid}/exe 2>/dev/null))/jstat 2>/dev/null; "
                f"if [ -x \"$JSTAT\" ]; then $JSTAT -gc {pid} 2>/dev/null; else jstat -gc {pid} 2>/dev/null; fi"
            )
            out, _, code = _ssh_run(host, user, cmd, timeout)
            if code == 0 and out:
                parsed = _parse_jstat_gc(out)
                if parsed:
                    result["jvm_by_pid"][str(pid)] = parsed
        except Exception:
            pass

    return result


def _detect_db_type(host: str, user: str, port: int, timeout: int) -> str:
    """Detect DB type (MySQL, PostgreSQL, etc.) on the DB host by version or listener process."""
    out_mysql, _, code_mysql = _ssh_run(host, user, "mysql --version 2>/dev/null", timeout)
    if code_mysql == 0 and out_mysql:
        m = re.search(r"Ver\s+([\d.]+)", out_mysql, re.I)
        if m:
            return "MySQL " + m.group(1).strip()
        return "MySQL"
    out_psql, _, code_psql = _ssh_run(host, user, "psql --version 2>/dev/null", timeout)
    if code_psql == 0 and out_psql:
        m = re.search(r"\(PostgreSQL\)\s+([\d.]+)", out_psql, re.I)
        if m:
            return "PostgreSQL " + m.group(1).strip()
        return "PostgreSQL"
    out_ss, _, _ = _ssh_run(host, user, f"ss -tlnp 2>/dev/null | grep ':{port}'", timeout)
    if out_ss:
        m = re.search(r'users:\(\("([^"]+)"', out_ss)
        if m:
            return m.group(1)
    return "Unknown"


def collect_db_node(db_host: str, db_port: int, config: dict) -> dict[str, Any]:
    """Gather system metrics and DB type from a DB host (same boxes as app node, Process → DB type)."""
    user = config.get("app", {}).get("db_ssh_user") or config.get("ssh_user", "svcjira")
    timeout = config.get("app", {}).get("ssh_command_timeout", 30)
    result = {
        "host": db_host,
        "port": db_port,
        "db_type": "—",
        "load_avg_1_5_15": [0.0, 0.0, 0.0],
        "memory": {},
        "cpu_percent": 0.0,
        "incoming_connections": 0,
        "error": None,
    }
    try:
        out, _, code = _ssh_run(db_host, user, "free -m", timeout)
        if code == 0:
            result["memory"] = _parse_free_m(out)
        out, _, code = _ssh_run(db_host, user, "cat /proc/loadavg", timeout)
        if code == 0:
            result["load_avg_1_5_15"] = _parse_loadavg(out)
        try:
            result["cpu_percent"] = _get_cpu_util_remote(db_host, user, timeout)
        except Exception:
            pass
        result["db_type"] = _detect_db_type(db_host, user, db_port, timeout)
        out, _, code = _ssh_run(db_host, user, f"ss -tn 2>/dev/null | awk '$4 ~ /:{db_port}$/ {{count++}} END {{print count+0}}'", timeout)
        if code == 0 and out.strip().isdigit():
            result["incoming_connections"] = int(out.strip())
    except Exception as e:
        result["error"] = str(e)
    return result


def collect_all(config: dict = None) -> dict[str, Any]:
    """Collect metrics from all configured servers. Optional config override."""
    cfg = config or get_config()
    hosts = get_servers_full_hostnames(cfg)
    results = []
    for host in hosts:
        try:
            results.append(collect_node(host, cfg))
        except Exception as e:
            logger.exception("Collect failed for %s", host)
            results.append({
                "host": host,
                "error": str(e),
                "incoming_connections": 0,
                "db_connection_count": 0,
                "connections_by_pid": {},
                "load_avg_1_5_15": [0, 0, 0],
                "memory": {},
                "cpu_percent": 0.0,
                "processes": [],
            })
    unique_dbs: set[tuple[str, int]] = set()
    for r in results:
        h, p = r.get("db_host"), r.get("db_port")
        if h and p is not None:
            unique_dbs.add((str(h).strip(), int(p)))
    db_nodes = []
    for db_host, db_port in sorted(unique_dbs):
        try:
            db_nodes.append(collect_db_node(db_host, db_port, cfg))
        except Exception as e:
            logger.exception("DB node collect failed for %s:%s", db_host, db_port)
            db_nodes.append({
                "host": db_host,
                "port": db_port,
                "db_type": "—",
                "load_avg_1_5_15": [0, 0, 0],
                "memory": {},
                "cpu_percent": 0.0,
                "incoming_connections": 0,
                "error": str(e),
            })
    return {
        "environment": cfg.get("environment", "default"),
        "refresh_interval_seconds": cfg.get("app", {}).get("refresh_interval_seconds", 60),
        "servers": results,
        "db_nodes": db_nodes,
    }
