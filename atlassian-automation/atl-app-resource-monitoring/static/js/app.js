(function () {
  const main = document.getElementById('main');
  const serverCards = document.getElementById('server-cards');
  const dbCards = document.getElementById('db-cards');
  const loading = document.getElementById('loading');
  const lastUpdated = document.getElementById('last-updated');
  const envBadge = document.getElementById('env-badge');
  const envSelect = document.getElementById('env-select');
  const btnDownloadCsv = document.getElementById('btn-download-csv');
  const status = document.getElementById('status');
  const zLegend = document.getElementById('z-legend');
  const plotPanel = document.getElementById('plot-panel');
  const plotTitle = document.getElementById('plot-title');
  const plotRangeSelect = document.getElementById('plot-range');
  const plotModeSelect = document.getElementById('plot-mode');
  const plotCollapseBtn = document.getElementById('plot-collapse');
  const plotCanvas = document.getElementById('plot-canvas');
  const plotCustomRange = document.getElementById('plot-custom-range');
  const plotCustomStart = document.getElementById('plot-custom-start');
  const plotCustomEnd = document.getElementById('plot-custom-end');
  const plotCustomApply = document.getElementById('plot-custom-apply');

  const REFRESH_INTERVAL_MS = 60000;
  let refreshDataTimer = null;
  let monitoringConfig = { csv_window_minutes: 480, z_score: { normal_max: 1, medium_max: 2, high_max: 3 } };
  let timeSeriesData = [];
  let timeSeriesColumns = null;
  let timeSeriesEnvironment = null;
  let selectedMetric = null;
  let chartInstance = null;
  let chartUpdate = function () {};
  let envServers = [];

  function getSelectedEnv() {
    const v = envSelect.value;
    return v || null;
  }

  function flattenSnapshot(data) {
    var row = { timestamp: new Date().toISOString() };
    var columns = ['timestamp'];
    var servers = data.servers || [];
    var dbNodes = data.db_nodes || [];
    for (var i = 0; i < servers.length; i++) {
      var s = servers[i];
      var mem = s.memory || {};
      var load = s.load_avg_1_5_15 || [0, 0, 0];
      var prefix = 'app_' + i + '_';
      var memUsedPct = mem.utilization_percent != null ? mem.utilization_percent : '';
      var memAvailPct = memUsedPct !== '' ? (100 - memUsedPct) : '';
      var swapPct = mem.swap_utilization_percent != null ? mem.swap_utilization_percent : '';
      var keys = [
        [prefix + 'load_1m', load[0]],
        [prefix + 'load_5m', load[1]],
        [prefix + 'load_15m', load[2]],
        [prefix + 'cpu_percent', s.cpu_percent != null ? s.cpu_percent : ''],
        [prefix + 'mem_util_pct', memUsedPct],
        [prefix + 'mem_avail_pct', memAvailPct],
        [prefix + 'swap_util_pct', swapPct],
        [prefix + 'incoming', s.incoming_connections != null ? s.incoming_connections : ''],
        [prefix + 'db_connections', s.db_connection_count != null ? s.db_connection_count : '']
      ];
      var mainPid = null;
      var byPid = s.connections_by_pid || {};
      if (Object.keys(byPid).length > 0) mainPid = Object.keys(byPid)[0];
      var processes = s.processes || [];
      var jvmByPid = s.jvm_by_pid || {};
      for (var k = 0; k < processes.length && !mainPid; k++) {
        if (jvmByPid[String(processes[k].pid)]) { mainPid = String(processes[k].pid); break; }
      }
      if (!mainPid && processes.length) mainPid = String(processes[0].pid);
      var mainProcess = null;
      for (k = 0; k < processes.length; k++) {
        if (String(processes[k].pid) === mainPid) { mainProcess = processes[k]; break; }
      }
      var heapMaxMb = s.heap_max_mb != null && s.heap_max_mb > 0 ? s.heap_max_mb : null;
      var heapUsedMb = null;
      var nonHeapMb = null;
      if (mainPid && jvmByPid[mainPid]) {
        heapUsedMb = jvmByPid[mainPid].heap_used_mb != null ? jvmByPid[mainPid].heap_used_mb : null;
        nonHeapMb = jvmByPid[mainPid].non_heap_mb != null ? jvmByPid[mainPid].non_heap_mb : null;
      }
      var heapUsedPct = (heapMaxMb && heapUsedMb != null) ? (100 * heapUsedMb / heapMaxMb) : '';
      var heapAvailPct = (heapMaxMb && heapUsedMb != null) ? (100 * Math.max(0, heapMaxMb - heapUsedMb) / heapMaxMb) : '';
      var nonHeapPct = (heapMaxMb && nonHeapMb != null) ? (100 * nonHeapMb / heapMaxMb) : '';
      var rssMb = mainProcess && mainProcess.rss_kb != null ? mainProcess.rss_kb / 1024 : null;
      var rssPctHeap = (heapMaxMb && rssMb != null && heapMaxMb > 0) ? (100 * rssMb / heapMaxMb) : '';
      var processCpu = mainProcess && mainProcess.cpu_percent != null ? mainProcess.cpu_percent : '';
      keys.push([prefix + 'heap_used_mb', heapUsedMb != null ? heapUsedMb : '']);
      keys.push([prefix + 'heap_used_pct', heapUsedPct]);
      keys.push([prefix + 'heap_avail_pct', heapAvailPct]);
      keys.push([prefix + 'non_heap_pct', nonHeapPct]);
      keys.push([prefix + 'rss_pct_heap', rssPctHeap]);
      keys.push([prefix + 'process_cpu', processCpu]);
      var access5 = s.access_log_5m;
      keys.push([prefix + 'access_requests', access5 && access5.request_count != null ? access5.request_count : '']);
      keys.push([prefix + 'access_unique_users', access5 && access5.unique_users != null ? access5.unique_users : '']);
      keys.push([prefix + 'rt_99p_sec', access5 && access5.response_time_99p_sec != null ? access5.response_time_99p_sec : '']);
      keys.push([prefix + 'rt_95p_sec', access5 && access5.response_time_95p_sec != null ? access5.response_time_95p_sec : '']);
      keys.push([prefix + 'rt_90p_sec', access5 && access5.response_time_90p_sec != null ? access5.response_time_90p_sec : '']);
      keys.push([prefix + 'rt_avg_sec', access5 && access5.response_time_avg_sec != null ? access5.response_time_avg_sec : '']);
      keys.push([prefix + 'apdex', access5 && access5.apdex != null ? access5.apdex : '']);
      keys.push([prefix + 'apdex_satisfied', access5 && access5.apdex_satisfied != null ? access5.apdex_satisfied : '']);
      keys.push([prefix + 'apdex_neutral', access5 && access5.apdex_neutral != null ? access5.apdex_neutral : '']);
      keys.push([prefix + 'apdex_unsatisfied', access5 && access5.apdex_unsatisfied != null ? access5.apdex_unsatisfied : '']);
      var app5 = s.app_log_5m;
      keys.push([prefix + 'app_log_lines', app5 && app5.line_count != null ? app5.line_count : '']);
      keys.push([prefix + 'app_log_threads', app5 && app5.unique_threads != null ? app5.unique_threads : '']);
      for (var j = 0; j < keys.length; j++) {
        columns.push(keys[j][0]);
        row[keys[j][0]] = keys[j][1];
      }
    }
    var apdexGlobal = data.apdex_global;
    if (apdexGlobal != null) {
      columns.push('apdex_global', 'apdex_global_satisfied', 'apdex_global_neutral', 'apdex_global_unsatisfied');
      row.apdex_global = apdexGlobal.apdex != null ? apdexGlobal.apdex : '';
      row.apdex_global_satisfied = apdexGlobal.apdex_satisfied != null ? apdexGlobal.apdex_satisfied : '';
      row.apdex_global_neutral = apdexGlobal.apdex_neutral != null ? apdexGlobal.apdex_neutral : '';
      row.apdex_global_unsatisfied = apdexGlobal.apdex_unsatisfied != null ? apdexGlobal.apdex_unsatisfied : '';
    }
    var accessGlobal = data.access_log_5m_global;
    if (accessGlobal != null) {
      columns.push('access_global_requests', 'access_global_unique_users', 'rt_global_99p_sec', 'rt_global_95p_sec', 'rt_global_90p_sec', 'rt_global_avg_sec');
      row.access_global_requests = accessGlobal.request_count != null ? accessGlobal.request_count : '';
      row.access_global_unique_users = accessGlobal.unique_users != null ? accessGlobal.unique_users : '';
      row.rt_global_99p_sec = accessGlobal.response_time_99p_sec != null ? accessGlobal.response_time_99p_sec : '';
      row.rt_global_95p_sec = accessGlobal.response_time_95p_sec != null ? accessGlobal.response_time_95p_sec : '';
      row.rt_global_90p_sec = accessGlobal.response_time_90p_sec != null ? accessGlobal.response_time_90p_sec : '';
      row.rt_global_avg_sec = accessGlobal.response_time_avg_sec != null ? accessGlobal.response_time_avg_sec : '';
    }
    for (i = 0; i < dbNodes.length; i++) {
      var d = dbNodes[i];
      mem = d.memory || {};
      load = d.load_avg_1_5_15 || [0, 0, 0];
      prefix = 'db_' + i + '_';
      memUsedPct = mem.utilization_percent != null ? mem.utilization_percent : '';
      memAvailPct = memUsedPct !== '' ? (100 - memUsedPct) : '';
      swapPct = mem.swap_utilization_percent != null ? mem.swap_utilization_percent : '';
      keys = [
        [prefix + 'load_1m', load[0]],
        [prefix + 'load_5m', load[1]],
        [prefix + 'load_15m', load[2]],
        [prefix + 'cpu_percent', d.cpu_percent != null ? d.cpu_percent : ''],
        [prefix + 'mem_util_pct', memUsedPct],
        [prefix + 'mem_avail_pct', memAvailPct],
        [prefix + 'swap_util_pct', swapPct],
        [prefix + 'connections', d.incoming_connections != null ? d.incoming_connections : '']
      ];
      for (j = 0; j < keys.length; j++) {
        columns.push(keys[j][0]);
        row[keys[j][0]] = keys[j][1];
      }
    }
    return { columns: columns, row: row };
  }

  function computeZScoreMap(series, currentRow, windowMs) {
    var cutoff = (currentRow.timestamp ? new Date(currentRow.timestamp).getTime() : Date.now()) - windowMs;
    var map = {};
    if (!series.length) return map;
    var keys = Object.keys(series[0].row || {}).filter(function (k) { return k !== 'timestamp'; });
    for (var ki = 0; ki < keys.length; ki++) {
      var key = keys[ki];
      var values = [];
      for (var i = 0; i < series.length; i++) {
        var ts = series[i].ts;
        if (ts < cutoff) continue;
        var v = series[i].row[key];
        if (v !== '' && v != null && !isNaN(Number(v))) values.push(Number(v));
      }
      var current = currentRow[key];
      if (current === '' || current == null || isNaN(Number(current))) continue;
      if (values.length < 2) {
        map[key] = 0;
        continue;
      }
      var sum = 0;
      for (i = 0; i < values.length; i++) sum += values[i];
      var mean = sum / values.length;
      var sq = 0;
      for (i = 0; i < values.length; i++) sq += (values[i] - mean) * (values[i] - mean);
      var std = Math.sqrt(sq / values.length);
      if (std === 0) {
        map[key] = 0;
        continue;
      }
      map[key] = (Number(current) - mean) / std;
    }
    return map;
  }

  function getZScoreClass(zScore) {
    if (zScore == null || isNaN(zScore)) return '';
    var abs = Math.abs(zScore);
    var n = monitoringConfig.z_score.normal_max != null ? monitoringConfig.z_score.normal_max : 1;
    var m = monitoringConfig.z_score.medium_max != null ? monitoringConfig.z_score.medium_max : 2;
    var h = monitoringConfig.z_score.high_max != null ? monitoringConfig.z_score.high_max : 3;
    if (abs <= n) return 'z-normal';
    if (abs <= m) return 'z-medium';
    if (abs <= h) return 'z-high';
    return 'z-extreme';
  }

  function computeTrendMap(series, currentRow) {
    var map = {};
    if (!series || series.length < 2) return map;
    var prevRow = series[series.length - 2].row;
    var keys = Object.keys(currentRow || {}).filter(function (k) { return k !== 'timestamp'; });
    for (var ki = 0; ki < keys.length; ki++) {
      var key = keys[ki];
      var cur = currentRow[key];
      var prev = prevRow[key];
      if (cur === '' || cur == null || prev === '' || prev == null) continue;
      var cn = Number(cur);
      var pn = Number(prev);
      if (isNaN(cn) || isNaN(pn)) continue;
      if (cn > pn) map[key] = 1;
      else if (cn < pn) map[key] = -1;
      else map[key] = 0;
    }
    return map;
  }

  function higherIsBetterForKey(key) {
    if (!key) return false;
    return key.indexOf('mem_avail_pct') !== -1 || key.indexOf('heap_avail_pct') !== -1 || key === 'apdex' || key.indexOf('apdex') === 0;
  }

  function getPredictionClass(trendDir, columnKey) {
    if (trendDir === 0) return 'pred-neutral';
    var higherBetter = higherIsBetterForKey(columnKey);
    if (trendDir > 0) return higherBetter ? 'pred-improve' : 'pred-worsen';
    return higherBetter ? 'pred-worsen' : 'pred-improve';
  }

  function getPredictionLabel(trendDir, columnKey) {
    if (trendDir === 0) return 'neutral';
    var higherBetter = higherIsBetterForKey(columnKey);
    if (trendDir > 0) return higherBetter ? 'improve' : 'worsen';
    return higherBetter ? 'worsen' : 'improve';
  }

  function getZScoreColorLabel(zScore) {
    if (zScore == null || isNaN(zScore)) return '';
    var abs = Math.abs(zScore);
    var n = monitoringConfig.z_score.normal_max != null ? monitoringConfig.z_score.normal_max : 1.75;
    var m = monitoringConfig.z_score.medium_max != null ? monitoringConfig.z_score.medium_max : 2.75;
    if (abs <= n) return 'green';
    if (abs <= m) return 'yellow';
    return 'red';
  }

  function computeTrendMapFromPrev(prevRow, currentRow) {
    var map = {};
    if (!prevRow || !currentRow) return map;
    var keys = Object.keys(currentRow).filter(function (k) { return k !== 'timestamp'; });
    for (var ki = 0; ki < keys.length; ki++) {
      var key = keys[ki];
      var cur = currentRow[key];
      var prev = prevRow[key];
      if (cur === '' || cur == null || prev === '' || prev == null) continue;
      var cn = Number(cur);
      var pn = Number(prev);
      if (isNaN(cn) || isNaN(pn)) continue;
      if (cn > pn) map[key] = 1;
      else if (cn < pn) map[key] = -1;
      else map[key] = 0;
    }
    return map;
  }

  function recentArrowSpan(columnKey, trendMap) {
    if (!trendMap || trendMap[columnKey] == null) return '';
    var dir = trendMap[columnKey];
    if (dir === 0) return '';
    var arrow = dir > 0 ? '\u2191' : '\u2193';
    return '<span class="metric-trend-recent" aria-label="recent ' + (dir > 0 ? 'up' : 'down') + '">' + arrow + '</span> ';
  }

  function predictionArrowSpan(columnKey, trendMap) {
    if (!trendMap || trendMap[columnKey] == null) return '';
    var dir = trendMap[columnKey];
    var predCl = getPredictionClass(dir, columnKey);
    return ' <span class="metric-trend-pred ' + predCl + '" aria-label="predicted ' + (dir > 0 ? 'up' : 'down') + '">\u2192</span>';
  }

  function arrowSpan(columnKey, zScoreMap, trendMap) {
    if (!trendMap || trendMap[columnKey] == null) return '';
    var recent = recentArrowSpan(columnKey, trendMap);
    var pred = predictionArrowSpan(columnKey, trendMap);
    return recent + pred;
  }

  function detailNum(val, columnKey, zScoreMap, trendMap) {
    if (val === '' || val == null) return escapeHtml('—');
    var cl = (zScoreMap && zScoreMap[columnKey] != null) ? getZScoreClass(zScoreMap[columnKey]) : '';
    var recent = trendMap ? recentArrowSpan(columnKey, trendMap) : '';
    var dk = columnKey ? ' data-column-key="' + escapeHtml(columnKey) + '"' : '';
    var numSpan = '<span class="metric-detail-num' + (cl ? ' ' + cl : '') + '"' + dk + '>' + escapeHtml(String(val)) + '</span>';
    var pred = trendMap ? predictionArrowSpan(columnKey, trendMap) : '';
    return recent + numSpan + pred;
  }

  function apiUrl(path, params) {
    const env = getSelectedEnv();
    const p = params || {};
    if (env) p.env = env;
    const q = new URLSearchParams(p).toString();
    return q ? path + '?' + q : path;
  }

  function setStatus(msg, isError) {
    status.textContent = msg || '';
    status.style.color = isError ? 'var(--danger)' : 'var(--text-muted)';
  }

  function setLastUpdated() {
    const d = new Date();
    lastUpdated.textContent = 'Last updated: ' + d.toLocaleTimeString();
  }

  function renderServer(s, serverIndex, zScoreMap, trendMap) {
    var idx = serverIndex != null ? serverIndex : 0;
    var prefix = 'app_' + idx + '_';
    var z = zScoreMap || {};
    var trend = trendMap || {};
    const err = s.error;
    const load = s.load_avg_1_5_15 || [0, 0, 0];
    const mem = s.memory || {};
    const cpu = s.cpu_percent != null ? s.cpu_percent : 0;
    const incoming = s.incoming_connections != null ? s.incoming_connections : 0;
    const dbCount = s.db_connection_count != null ? s.db_connection_count : 0;
    const dbHost = s.db_host;
    const dbPort = s.db_port;
    const byPid = s.connections_by_pid || {};
    const processes = s.processes || [];
    const heapMaxMb = s.heap_max_mb != null && s.heap_max_mb > 0 ? s.heap_max_mb : null;
    const jvmByPid = s.jvm_by_pid || {};
    const pidToProcess = {};
    processes.forEach(function (p) {
      pidToProcess[p.pid] = p;
    });

    var mainPid = null;
    var mainProcess = null;
    var mainJvm = null;
    if (Object.keys(byPid).length > 0) {
      mainPid = Object.keys(byPid)[0];
      mainProcess = pidToProcess[mainPid];
      mainJvm = jvmByPid[mainPid];
    } else if (processes.length > 0) {
      for (var i = 0; i < processes.length; i++) {
        if (jvmByPid[String(processes[i].pid)]) {
          mainPid = String(processes[i].pid);
          mainProcess = processes[i];
          mainJvm = jvmByPid[mainPid];
          break;
        }
      }
      if (!mainProcess) {
        mainProcess = processes[0];
        mainPid = mainProcess && mainProcess.pid != null ? String(mainProcess.pid) : null;
        mainJvm = mainPid ? jvmByPid[mainPid] : null;
      }
    }

    var processLabel = '—';
    var processCpuDetail = null;
    var memUsedDetail = null;
    var memAvailDetail = null;
    var cpuDetail = null;
    var heapUsedPctStr = '—';
    var heapAvailPctStr = '—';
    var nonHeapPctStr = '—';
    var rssPctHeapStr = '—';
    if (mainProcess && mainPid) {
      processLabel = escapeHtml((mainProcess.comm || 'process') + ' (' + mainPid + ')');
      var appType = (s.app_type || 'jira').toLowerCase();
      var appVer = s.app_version || s.jira_version;
      if (appVer) {
        var productName = appType === 'confluence' ? 'Confluence' : 'Jira';
        processLabel += ' — ' + productName + ' ' + escapeHtml(appVer);
      }
      if (mainProcess.cpu_percent != null) {
        cpuDetail = 'process: ' + detailNum(mainProcess.cpu_percent.toFixed(1) + '%', prefix + 'process_cpu', z, trend);
      }
      if (heapMaxMb && mainJvm) {
        var rssMb = mainProcess.rss_kb != null ? mainProcess.rss_kb / 1024 : null;
        heapUsedPctStr = mainJvm.heap_used_mb != null ? (100 * mainJvm.heap_used_mb / heapMaxMb).toFixed(1) : '—';
        heapAvailPctStr = mainJvm.heap_used_mb != null ? (100 * Math.max(0, heapMaxMb - mainJvm.heap_used_mb) / heapMaxMb).toFixed(1) : '—';
        nonHeapPctStr = mainJvm.non_heap_mb != null ? (100 * mainJvm.non_heap_mb / heapMaxMb).toFixed(1) : '—';
        rssPctHeapStr = (rssMb != null && heapMaxMb > 0) ? (100 * rssMb / heapMaxMb).toFixed(1) : '—';
        memUsedDetail = 'heap: ' + detailNum(heapUsedPctStr + '%', prefix + 'heap_used_pct', z, trend) + ', non-heap: ' + detailNum(nonHeapPctStr + '%', prefix + 'non_heap_pct', z, trend) + ', RSS/heap: ' + detailNum(rssPctHeapStr + '%', prefix + 'rss_pct_heap', z, trend);
        memAvailDetail = 'heap avail: ' + detailNum(heapAvailPctStr + '%', prefix + 'heap_avail_pct', z, trend);
      }
    }

    var html = '<div class="card">';
    html += '<div class="card-header">';
    html += '<h2 class="card-title">' + escapeHtml(s.host) + '</h2>';
    if (err) html += '<span class="card-error">' + escapeHtml(err) + '</span>';
    html += '</div>';

    if (!err) {
      var memUsedPct = mem.utilization_percent != null ? mem.utilization_percent : null;
      var memAvailPct = memUsedPct != null ? (100 - memUsedPct).toFixed(1) : null;
      var swapPct = mem.swap_utilization_percent != null ? mem.swap_utilization_percent : null;
      var swapTotal = mem.swap_total_mb != null ? mem.swap_total_mb : 0;
      var loadValHtml = detailNum(load[0].toFixed(2), prefix + 'load_1m', z, trend) + ' / ' + detailNum(load[1].toFixed(2), prefix + 'load_5m', z, trend) + ' / ' + detailNum(load[2].toFixed(2), prefix + 'load_15m', z, trend);
      html += '<div class="metrics-grid">';
      html += metric('Process', processLabel, false, null, null, null, false, false, null);
      html += metric('Load avg (1/5/15)', loadValHtml, false, null, null, z, false, true, null);
      html += metric('System CPU %', cpu + '%', cpu > 80, cpuDetail, prefix + 'cpu_percent', z, true, false, trend);
      html += metric('Memory used', (memUsedPct != null ? memUsedPct + '%' : '—'), memUsedPct > 85, memUsedDetail, prefix + 'mem_util_pct', z, true, false, trend);
      html += metric('Memory available', (memAvailPct != null ? memAvailPct + '%' : '—'), false, memAvailDetail, prefix + 'mem_avail_pct', z, true, false, trend);
      html += metric('Swap used', (swapTotal > 0 && swapPct != null ? swapPct + '%' : (swapTotal === 0 ? 'N/A' : '—')), swapPct > 80, null, prefix + 'swap_util_pct', z, false, false, trend);
      html += metric('Incoming (app port)', String(incoming), false, null, prefix + 'incoming', z, false, false, trend);
      html += metric('DB connections', String(dbCount), false, null, prefix + 'db_connections', z, false, false, trend);
      var access5 = s.access_log_5m;
      if (access5 != null) {
        var accessLabelHtml = detailNum(access5.unique_users != null ? access5.unique_users : '—', prefix + 'access_unique_users', z, trend) + ' users, ' + detailNum(access5.request_count != null ? access5.request_count : 0, prefix + 'access_requests', z, trend) + ' requests';
        var accessDetailHtml = null;
        if (access5.response_time_avg_sec != null) {
          var parts = [];
          if (access5.response_time_99p_sec != null) parts.push('99p: ' + detailNum(access5.response_time_99p_sec + 's', prefix + 'rt_99p_sec', z, trend));
          if (access5.response_time_95p_sec != null) parts.push('95p: ' + detailNum(access5.response_time_95p_sec + 's', prefix + 'rt_95p_sec', z, trend));
          if (access5.response_time_90p_sec != null) parts.push('90p: ' + detailNum(access5.response_time_90p_sec + 's', prefix + 'rt_90p_sec', z, trend));
          parts.push('avg: ' + detailNum(access5.response_time_avg_sec + 's', prefix + 'rt_avg_sec', z, trend));
          accessDetailHtml = parts.join(', ');
        }
        html += metric('Access log (5m)', accessLabelHtml, false, accessDetailHtml, null, z, true, true, null);
        if (access5.apdex != null) {
          var apdexDetail = 'satisfied: ' + detailNum(access5.apdex_satisfied != null ? access5.apdex_satisfied : '—', prefix + 'apdex_satisfied', z, trend) + ', neutral: ' + detailNum(access5.apdex_neutral != null ? access5.apdex_neutral : '—', prefix + 'apdex_neutral', z, trend) + ', not satisfied: ' + detailNum(access5.apdex_unsatisfied != null ? access5.apdex_unsatisfied : '—', prefix + 'apdex_unsatisfied', z, trend);
          var apdexValHtml = detailNum(Number(access5.apdex).toFixed(3), prefix + 'apdex', z, trend);
          html += metric('Apdex', apdexValHtml, false, apdexDetail, null, z, true, true, trend, 'apdex-score');
        }
      }
      var app5 = s.app_log_5m;
      if (app5 != null) {
        var appLogValHtml = detailNum(app5.unique_threads != null ? app5.unique_threads : '—', prefix + 'app_log_threads', z, trend) + ' threads, ' + detailNum(app5.line_count != null ? app5.line_count : 0, prefix + 'app_log_lines', z, trend) + ' lines';
        html += metric('App log (5m)', appLogValHtml, false, null, null, z, false, true, null);
      }
      html += '</div>';

      if (dbHost) {
        html += '<div class="db-info">DB: ' + escapeHtml(dbHost) + (dbPort ? ':' + dbPort : '') + '</div>';
      }
    }

    html += '</div>';
    return html;
  }

  function renderDbNode(d, dbIndex, zScoreMap, trendMap) {
    var idx = dbIndex != null ? dbIndex : 0;
    var prefix = 'db_' + idx + '_';
    var z = zScoreMap || {};
    var trend = trendMap || {};
    var err = d.error;
    var load = d.load_avg_1_5_15 || [0, 0, 0];
    var mem = d.memory || {};
    var cpu = d.cpu_percent != null ? d.cpu_percent : 0;
    var conn = d.incoming_connections != null ? d.incoming_connections : 0;
    var dbType = (d.db_type != null && d.db_type !== '—') ? d.db_type : '—';
    var title = escapeHtml(d.host) + (d.port != null ? ':' + d.port : '');
    var html = '<div class="card">';
    html += '<div class="card-header">';
    html += '<h2 class="card-title">' + title + '</h2>';
    if (err) html += '<span class="card-error">' + escapeHtml(err) + '</span>';
    html += '</div>';
    if (!err) {
      var memUsedPct = mem.utilization_percent != null ? mem.utilization_percent : null;
      var memAvailPct = memUsedPct != null ? (100 - memUsedPct).toFixed(1) : null;
      var swapPct = mem.swap_utilization_percent != null ? mem.swap_utilization_percent : null;
      var swapTotal = mem.swap_total_mb != null ? mem.swap_total_mb : 0;
      var dbLoadValHtml = detailNum(load[0].toFixed(2), prefix + 'load_1m', z, trend) + ' / ' + detailNum(load[1].toFixed(2), prefix + 'load_5m', z, trend) + ' / ' + detailNum(load[2].toFixed(2), prefix + 'load_15m', z, trend);
      html += '<div class="metrics-grid">';
      html += metric('DB type', dbType, false, null, null, null, false, false, null);
      html += metric('Load avg (1/5/15)', dbLoadValHtml, false, null, null, z, false, true, null);
      html += metric('System CPU %', cpu + '%', cpu > 80, null, prefix + 'cpu_percent', z, false, false, trend);
      html += metric('Memory used', (memUsedPct != null ? memUsedPct + '%' : '—'), memUsedPct > 85, null, prefix + 'mem_util_pct', z, false, false, trend);
      html += metric('Memory available', (memAvailPct != null ? memAvailPct + '%' : '—'), false, null, prefix + 'mem_avail_pct', z, false, false, trend);
      html += metric('Swap used', (swapTotal > 0 && swapPct != null ? swapPct + '%' : (swapTotal === 0 ? 'N/A' : '—')), swapPct > 80, null, prefix + 'swap_util_pct', z, false, false, trend);
      html += metric('Connections', String(conn), false, null, prefix + 'connections', z, false, false, trend);
      html += '</div>';
    }
    html += '</div>';
    return html;
  }

  function metric(label, value, warn, detail, columnKey, zScoreMap, detailIsHtml, valueIsHtml, trendMap, valueClass) {
    var c = ' metric-value';
    if (warn) c += ' warn';
    if (columnKey && zScoreMap && zScoreMap[columnKey] != null) {
      c += ' ' + getZScoreClass(zScoreMap[columnKey]);
    }
    if (valueClass) c += ' ' + valueClass;
    var valueOut = valueIsHtml ? value : escapeHtml(String(value));
    if (columnKey && trendMap && !valueIsHtml) {
      valueOut = recentArrowSpan(columnKey, trendMap) + valueOut + predictionArrowSpan(columnKey, trendMap);
    }
    var divAttr = columnKey ? ' data-column-key="' + escapeHtml(columnKey) + '"' : '';
    var out = '<div class="metric"' + divAttr + '><div class="metric-label">' + escapeHtml(label) + '</div><div class="' + c.trim() + '">' + valueOut + '</div>';
    if (detail) {
      out += '<div class="metric-detail">' + (detailIsHtml ? detail : escapeHtml(detail)) + '</div>';
    }
    out += '</div>';
    return out;
  }

  function escapeHtml(s) {
    if (s == null) return '';
    const div = document.createElement('div');
    div.textContent = s;
    return div.innerHTML;
  }

  function refreshData() {
    var env = getSelectedEnv();
    if (!env) {
      loading.style.display = 'none';
      serverCards.innerHTML = '';
      dbCards.innerHTML = '';
      if (btnDownloadCsv) btnDownloadCsv.style.display = 'none';
      return;
    }
    setStatus('Loading…');
    timeSeriesEnvironment = env;
    var latestUrl = '/api/metrics/latest?env=' + encodeURIComponent(env);
    var seriesUrl = '/api/monitoring/series?env=' + encodeURIComponent(env);
    Promise.all([
      fetch(latestUrl).then(function (r) { return r.status === 404 ? null : r.json(); }),
      fetch(seriesUrl).then(function (r) { return r.ok ? r.json() : { columns: [], rows: [] }; })
    ]).then(function (results) {
      if (getSelectedEnv() !== env) return;
      var data = results[0];
      var json = results[1];
      loading.style.display = 'none';
      var cols = json.columns || [];
      var rows = json.rows || [];
      if (rows.length && cols.length) {
        var baseCols = cols.filter(function (c) {
          return c === 'timestamp' || (!c.endsWith('_z_color') && !c.endsWith('_trend') && !c.endsWith('_pred') && !c.endsWith('_z'));
        });
        if (baseCols.length) timeSeriesColumns = baseCols;
        timeSeriesData = rows.map(function (r) {
          var ts = r.timestamp ? new Date(r.timestamp).getTime() : 0;
          return { ts: ts, row: r, data: null };
        });
      } else {
        timeSeriesData = [];
        timeSeriesColumns = null;
      }
      if (!data || data.error) {
        serverCards.innerHTML = '<div class="card"><div class="card-header"><span class="card-error">' + escapeHtml(data && data.error ? data.error : 'No data for this environment yet') + '</span></div></div>';
        dbCards.innerHTML = '';
      } else {
        var flat = flattenSnapshot(data);
        var windowMs = (monitoringConfig.csv_window_minutes || 480) * 60 * 1000;
        var zScoreMap = computeZScoreMap(timeSeriesData, flat.row, windowMs);
        var prevRow = timeSeriesData.length >= 2 ? timeSeriesData[timeSeriesData.length - 2].row : null;
        var trendMap = computeTrendMapFromPrev(prevRow, flat.row);
        var list = data.servers || [];
        var globalHtml = '';
        if (data.access_log_5m_global != null) {
          var ag = data.access_log_5m_global;
          var accessGlobalLabel = detailNum(ag.unique_users != null ? ag.unique_users : '—', 'access_global_unique_users', zScoreMap, trendMap) + ' users, ' + detailNum(ag.request_count != null ? ag.request_count : 0, 'access_global_requests', zScoreMap, trendMap) + ' requests';
          var accessGlobalDetail = null;
          if (ag.response_time_avg_sec != null) {
            var parts = [];
            if (ag.response_time_99p_sec != null) parts.push('99p: ' + detailNum(ag.response_time_99p_sec + 's', 'rt_global_99p_sec', zScoreMap, trendMap));
            if (ag.response_time_95p_sec != null) parts.push('95p: ' + detailNum(ag.response_time_95p_sec + 's', 'rt_global_95p_sec', zScoreMap, trendMap));
            if (ag.response_time_90p_sec != null) parts.push('90p: ' + detailNum(ag.response_time_90p_sec + 's', 'rt_global_90p_sec', zScoreMap, trendMap));
            parts.push('avg: ' + detailNum(ag.response_time_avg_sec + 's', 'rt_global_avg_sec', zScoreMap, trendMap));
            accessGlobalDetail = parts.join(', ');
          }
          globalHtml += '<div class="global-metrics-wrap">';
          globalHtml += metric('Access log (5m) — all nodes', accessGlobalLabel, false, accessGlobalDetail, null, zScoreMap, true, true, trendMap);
        }
        if (data.apdex_global && data.apdex_global.apdex != null) {
          var g = data.apdex_global;
          var apdexGlobalDetail = 'satisfied: ' + detailNum(g.apdex_satisfied != null ? g.apdex_satisfied : '—', 'apdex_global_satisfied', zScoreMap, trendMap) + ', neutral: ' + detailNum(g.apdex_neutral != null ? g.apdex_neutral : '—', 'apdex_global_neutral', zScoreMap, trendMap) + ', not satisfied: ' + detailNum(g.apdex_unsatisfied != null ? g.apdex_unsatisfied : '—', 'apdex_global_unsatisfied', zScoreMap, trendMap);
          var apdexGlobalVal = detailNum(Number(g.apdex).toFixed(3), 'apdex_global', zScoreMap, trendMap);
          if (globalHtml === '') globalHtml = '<div class="global-metrics-wrap">';
          globalHtml += metric('Apdex (all nodes)', apdexGlobalVal, false, apdexGlobalDetail, null, zScoreMap, true, true, trendMap, 'apdex-score');
        }
        if (globalHtml) globalHtml += '</div>';
        serverCards.innerHTML = globalHtml + list.map(function (s, i) { return renderServer(s, i, zScoreMap, trendMap); }).join('');
        var dbList = data.db_nodes || [];
        dbCards.innerHTML = dbList.length ? dbList.map(function (d, i) { return renderDbNode(d, i, zScoreMap, trendMap); }).join('') : '<p class="section-empty">No DB nodes discovered from app config.</p>';
      }
      if (btnDownloadCsv) btnDownloadCsv.style.display = timeSeriesData.length ? 'inline-block' : 'none';
      setLastUpdated();
      setStatus('');
      if (chartUpdate) chartUpdate();
    }).catch(function (e) {
      if (getSelectedEnv() !== env) return;
      loading.style.display = 'none';
      serverCards.innerHTML = '<div class="card"><div class="card-header"><span class="card-error">Request failed: ' + escapeHtml(e.message) + '</span></div></div>';
      dbCards.innerHTML = '';
      setStatus('Request failed', true);
    });
  }

  if (btnDownloadCsv) {
    btnDownloadCsv.addEventListener('click', function () {
      if (timeSeriesData.length) downloadCsv();
    });
  }

  function csvEscape(s) {
    if (s === undefined || s === null) return '';
    var str = String(s);
    return /,|"|\n/.test(str) ? '"' + str.replace(/"/g, '""') + '"' : str;
  }

  function buildExtendedColumns(baseColumns) {
    var ext = [];
    baseColumns.forEach(function (c) {
      ext.push(c);
      if (c !== 'timestamp') ext.push(c + '_z', c + '_z_color', c + '_trend', c + '_pred');
    });
    return ext;
  }

  function buildExtendedRow(flatRow, zScoreMap, trendMap, baseColumns) {
    var row = {};
    baseColumns.forEach(function (c) {
      row[c] = flatRow[c] !== undefined && flatRow[c] !== null ? flatRow[c] : '';
      if (c !== 'timestamp') {
        var z = zScoreMap && zScoreMap[c];
        row[c + '_z'] = (z != null && !isNaN(z)) ? (Math.round(z * 1000) / 1000) : '';
        row[c + '_z_color'] = getZScoreColorLabel(z);
        var t = trendMap && trendMap[c];
        row[c + '_trend'] = t === 1 ? 'up' : t === -1 ? 'down' : '';
        row[c + '_pred'] = getPredictionLabel(t, c);
      }
    });
    return row;
  }

  function parseCsvToRows(text) {
    var lines = text.trim().split(/\r?\n/);
    if (lines.length < 2) return { columns: [], rows: [] };
    var header = lines[0];
    var cols = [];
    var i = 0;
    while (i < header.length) {
      if (header[i] === '"') {
        i++;
        var cell = '';
        while (i < header.length && (header[i] !== '"' || header[i + 1] === '"')) {
          cell += header[i] === '"' ? '' : header[i];
          if (header[i] === '"') i++;
          i++;
        }
        if (header[i] === '"') i++;
        cols.push(cell);
      } else {
        var end = header.indexOf(',', i);
        if (end === -1) end = header.length;
        cols.push(header.slice(i, end).trim());
        i = end + 1;
      }
    }
    var rows = [];
    for (var L = 1; L < lines.length; L++) {
      var line = lines[L];
      var row = {};
      var idx = 0;
      var j = 0;
      while (j < line.length && idx < cols.length) {
        var val = '';
        if (line[j] === '"') {
          j++;
          while (j < line.length) {
            if (line[j] === '"' && line[j + 1] !== '"') { j++; break; }
            val += line[j] === '"' ? '' : line[j];
            if (line[j] === '"') j++;
            j++;
          }
        } else {
          var end = line.indexOf(',', j);
          if (end === -1) end = line.length;
          val = line.slice(j, end).trim();
          j = end + 1;
        }
        row[cols[idx]] = val;
        idx++;
      }
      rows.push(row);
    }
    return { columns: cols, rows: rows };
  }

  function downloadCsv() {
    if (!timeSeriesData.length || !timeSeriesColumns) return;
    var env = timeSeriesEnvironment || getSelectedEnv() || 'default';
    var startStr = timeSeriesData[0] && timeSeriesData[0].ts ? new Date(timeSeriesData[0].ts).toISOString().replace(/[:.]/g, '-') : new Date().toISOString().replace(/[:.]/g, '-');
    var windowMs = (monitoringConfig.csv_window_minutes || 480) * 60 * 1000;
    var extendedColumns = [];
    timeSeriesColumns.forEach(function (col) {
      extendedColumns.push(col);
      if (col !== 'timestamp') {
        extendedColumns.push(col + '_z');
        extendedColumns.push(col + '_z_color');
        extendedColumns.push(col + '_trend');
        extendedColumns.push(col + '_pred');
      }
    });
    var headerRow = extendedColumns.map(csvEscape).join(',');
    var csvRows = [headerRow];
    for (var i = 0; i < timeSeriesData.length; i++) {
      var currentRow = timeSeriesData[i].row;
      var rowTs = timeSeriesData[i].ts;
      var windowSeries = timeSeriesData.filter(function (r) { return r.ts >= rowTs - windowMs; });
      var zScoreMap = computeZScoreMap(windowSeries, currentRow, windowMs);
      var trendMap = i > 0 ? computeTrendMapFromPrev(timeSeriesData[i - 1].row, currentRow) : {};
      var rowCells = [];
      timeSeriesColumns.forEach(function (col) {
        rowCells.push(csvEscape(currentRow[col]));
        if (col !== 'timestamp') {
          var z = zScoreMap[col];
          rowCells.push(z != null && !isNaN(z) ? String(Math.round(z * 1000) / 1000) : '');
          rowCells.push(getZScoreColorLabel(z));
          var t = trendMap[col];
          rowCells.push(t === 1 ? 'up' : t === -1 ? 'down' : '');
          rowCells.push(getPredictionLabel(t, col));
        }
      });
      csvRows.push(rowCells.join(','));
    }
    var blob = new Blob([csvRows.join('\n')], { type: 'text/csv;charset=utf-8' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'monitoring_' + env + '_' + startStr + '.csv';
    a.click();
    URL.revokeObjectURL(a.href);
  }

  var TIME_RANGES = [
    { min: 5, label: '5 min' }, { min: 30, label: '30 min' }, { min: 60, label: '1 hr' }, { min: 120, label: '2 hr' },
    { min: 360, label: '6 hr' }, { min: 720, label: '12 hr' }, { min: 1080, label: '18 hr' }, { min: 1440, label: '1 day' },
    { min: 2880, label: '2 days' }, { min: 10080, label: '1 week' }, { min: 43200, label: '1 month' }
  ];

  var METRIC_LABELS = {
    load_1m: 'Load 1m', load_5m: 'Load 5m', load_15m: 'Load 15m',
    cpu_percent: 'CPU %', mem_util_pct: 'Memory utilization %', mem_avail_pct: 'Memory available %', swap_util_pct: 'Swap %',
    incoming: 'Incoming connections', db_connections: 'DB connections',
    heap_used_mb: 'Heap used (MB)', heap_used_pct: 'Heap used %', heap_avail_pct: 'Heap available %', non_heap_pct: 'Non-heap %',
    rss_pct_heap: 'RSS % of heap', process_cpu: 'Process CPU %',
    access_requests: 'Access requests (5m)', access_unique_users: 'Unique users (5m)',
    rt_99p_sec: 'Response time 99th %ile (sec)', rt_95p_sec: 'Response time 95th %ile (sec)',
    rt_90p_sec: 'Response time 90th %ile (sec)', rt_avg_sec: 'Response time avg (sec)',
    apdex: 'Apdex', apdex_satisfied: 'Apdex satisfied', apdex_neutral: 'Apdex neutral', apdex_unsatisfied: 'Apdex not satisfied',
    apdex_global: 'Apdex (all nodes)', apdex_global_satisfied: 'Apdex global satisfied', apdex_global_neutral: 'Apdex global neutral', apdex_global_unsatisfied: 'Apdex global not satisfied',
    access_global_requests: 'Access requests (5m) — all nodes', access_global_unique_users: 'Unique users (5m) — all nodes',
    rt_global_99p_sec: 'Response time 99th %ile (sec) — all nodes', rt_global_95p_sec: 'Response time 95th %ile (sec) — all nodes',
    rt_global_90p_sec: 'Response time 90th %ile (sec) — all nodes', rt_global_avg_sec: 'Response time avg (sec) — all nodes',
    app_log_lines: 'App log lines (5m)', app_log_threads: 'App log threads (5m)',
    connections: 'Connections'
  };

  function getMetricLabel(suffix) {
    if (METRIC_LABELS[suffix]) return METRIC_LABELS[suffix];
    return suffix.replace(/_/g, ' ').replace(/\b\w/g, function (c) { return c.toUpperCase(); });
  }

  function getPlotTitle(metricKey, useZ, servers) {
    var modeStr = useZ ? 'Z-Score' : 'Actual';
    if (metricKey === 'timestamp') return 'Timestamp (' + modeStr + ')';
    var match = metricKey.match(/^app_(\d+)_(.+)$/);
    if (match) {
      var idx = parseInt(match[1], 10);
      var serverName = (servers && servers[idx]) ? servers[idx] : ('App ' + idx);
      return serverName + ' · ' + getMetricLabel(match[2]) + ' (' + modeStr + ')';
    }
    match = metricKey.match(/^db_(\d+)_(.+)$/);
    if (match) {
      var dbIdx = parseInt(match[1], 10);
      return 'DB ' + dbIdx + ' · ' + getMetricLabel(match[2]) + ' (' + modeStr + ')';
    }
    return getMetricLabel(metricKey) + ' (' + modeStr + ')';
  }

  function updatePlotTitle() {
    if (!plotTitle || !selectedMetric) return;
    var useZ = plotModeSelect && plotModeSelect.value === 'z';
    plotTitle.textContent = getPlotTitle(selectedMetric, useZ, envServers);
  }

  function toDatetimeLocalStr(ts) {
    var d = new Date(ts);
    var y = d.getFullYear();
    var m = String(d.getMonth() + 1).padStart(2, '0');
    var day = String(d.getDate()).padStart(2, '0');
    var h = String(d.getHours()).padStart(2, '0');
    var min = String(d.getMinutes()).padStart(2, '0');
    return y + '-' + m + '-' + day + 'T' + h + ':' + min;
  }

  function fromDatetimeLocalStr(str) {
    if (!str || !str.trim()) return null;
    var ms = Date.parse(str);
    return isNaN(ms) ? null : ms;
  }

  function getPlotData(metricKey, rangeSpec, useZ) {
    if (!timeSeriesData.length) return { labels: [], values: [] };
    var filtered;
    if (typeof rangeSpec === 'object' && rangeSpec != null && 'startMs' in rangeSpec && 'endMs' in rangeSpec) {
      var startMs = rangeSpec.startMs;
      var endMs = rangeSpec.endMs;
      filtered = timeSeriesData.filter(function (r) { return r.ts >= startMs && r.ts <= endMs; });
    } else {
      var rangeMinutes = typeof rangeSpec === 'number' ? rangeSpec : (parseInt(rangeSpec, 10) || 5);
      var now = Date.now();
      var cutoff = now - rangeMinutes * 60 * 1000;
      filtered = timeSeriesData.filter(function (r) { return r.ts >= cutoff; });
    }
    var key = useZ && metricKey !== 'timestamp' ? metricKey + '_z' : metricKey;
    var labels = [];
    var values = [];
    filtered.forEach(function (r) {
      labels.push(new Date(r.ts).toISOString());
      var v = r.row[key];
      if (v !== '' && v != null && !isNaN(Number(v))) values.push(Number(v));
      else values.push(null);
    });
    return { labels: labels, values: values };
  }

  function updatePlotRangeOptions() {
    if (!plotRangeSelect || !timeSeriesData.length) return;
    var now = Date.now();
    var oldest = timeSeriesData[0].ts;
    var dataSpanMinutes = (now - oldest) / (60 * 1000);
    for (var i = 0; i < plotRangeSelect.options.length; i++) {
      var opt = plotRangeSelect.options[i];
      if (opt.value === 'custom') { opt.disabled = false; continue; }
      var rangeMin = parseInt(opt.value, 10);
      opt.disabled = !isNaN(rangeMin) && rangeMin > dataSpanMinutes;
    }
  }

  function setCustomRangeVisibility(show) {
    if (plotCustomRange) plotCustomRange.setAttribute('aria-hidden', show ? 'false' : 'true');
  }

  function setDefaultCustomRange() {
    if (!timeSeriesData.length || !plotCustomStart || !plotCustomEnd) return;
    var oldest = timeSeriesData[0].ts;
    var newest = timeSeriesData[timeSeriesData.length - 1].ts;
    plotCustomStart.value = toDatetimeLocalStr(oldest);
    plotCustomEnd.value = toDatetimeLocalStr(newest);
  }

  function getCustomRangeMs() {
    if (!plotCustomStart || !plotCustomEnd) return null;
    var startMs = fromDatetimeLocalStr(plotCustomStart.value);
    var endMs = fromDatetimeLocalStr(plotCustomEnd.value);
    if (startMs == null || endMs == null || startMs >= endMs) return null;
    return { startMs: startMs, endMs: endMs };
  }

  function drawChart() {
    if (!selectedMetric || !plotCanvas || typeof Chart === 'undefined') return;
    var useZ = plotModeSelect && plotModeSelect.value === 'z';
    var rangeSpec;
    if (plotRangeSelect && plotRangeSelect.value === 'custom') {
      rangeSpec = getCustomRangeMs();
      if (!rangeSpec) rangeSpec = timeSeriesData.length ? { startMs: timeSeriesData[0].ts, endMs: timeSeriesData[timeSeriesData.length - 1].ts } : 5;
    } else {
      rangeSpec = parseInt(plotRangeSelect.value, 10) || 5;
    }
    var data = getPlotData(selectedMetric, rangeSpec, useZ);
    if (chartInstance) chartInstance.destroy();
    chartInstance = new Chart(plotCanvas, {
      type: 'line',
      data: {
        labels: data.labels,
        datasets: [{
          label: useZ ? selectedMetric + ' (Z)' : selectedMetric,
          data: data.values,
          borderColor: '#00d4ff',
          backgroundColor: 'rgba(0, 212, 255, 0.2)',
          pointBackgroundColor: '#00d4ff',
          pointBorderColor: '#00d4ff',
          pointHoverBackgroundColor: '#00ffff',
          fill: true,
          tension: 0.2,
          spanGaps: true
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        aspectRatio: 2.5,
        plugins: { legend: { display: false } },
        scales: {
          x: {
            type: 'category',
            grid: { color: 'rgba(128, 128, 128, 0.3)' },
            ticks: { maxTicksLimit: 12, maxRotation: 45, color: '#b0b0b0' }
          },
          y: {
            beginAtZero: !useZ,
            grid: { color: 'rgba(128, 128, 128, 0.3)' },
            ticks: { color: '#b0b0b0' }
          }
        }
      }
    });
  }

  function showPlotPanel(metricKey) {
    selectedMetric = metricKey;
    if (!plotPanel) return;
    plotPanel.setAttribute('aria-hidden', 'false');
    plotPanel.classList.remove('collapsed');
    if (plotRangeSelect) plotRangeSelect.value = '5';
    if (plotCollapseBtn) plotCollapseBtn.textContent = 'Collapse';
    /* Use env that the series data belongs to so title matches data (VMW-Jira vs BIT-Jira) */
    var env = timeSeriesEnvironment || getSelectedEnv();
    if (env) {
      fetch('/api/config?env=' + encodeURIComponent(env))
        .then(function (r) { return r.json(); })
        .then(function (c) {
          envServers = c.servers || [];
          updatePlotTitle();
          updatePlotRangeOptions();
          drawChart();
        })
        .catch(function () {
          envServers = [];
          updatePlotTitle();
          updatePlotRangeOptions();
          drawChart();
        });
    } else {
      envServers = [];
      updatePlotTitle();
      updatePlotRangeOptions();
      drawChart();
    }
  }

  if (main) {
    main.addEventListener('click', function (e) {
      var el = e.target.closest('[data-column-key]');
      if (el) showPlotPanel(el.getAttribute('data-column-key'));
    });
  }

  if (plotRangeSelect) {
    plotRangeSelect.addEventListener('change', function () {
      var isCustom = plotRangeSelect.value === 'custom';
      setCustomRangeVisibility(isCustom);
      if (isCustom) setDefaultCustomRange();
      drawChart();
    });
  }
  if (plotCustomApply) plotCustomApply.addEventListener('click', drawChart);
  if (plotCustomStart && plotCustomEnd) {
    plotCustomStart.addEventListener('change', function () { if (plotRangeSelect && plotRangeSelect.value === 'custom') drawChart(); });
    plotCustomEnd.addEventListener('change', function () { if (plotRangeSelect && plotRangeSelect.value === 'custom') drawChart(); });
  }
  if (plotModeSelect) plotModeSelect.addEventListener('change', function () {
    updatePlotTitle();
    drawChart();
  });
  if (plotCollapseBtn) {
    plotCollapseBtn.addEventListener('click', function () {
      if (!plotPanel) return;
      plotPanel.classList.toggle('collapsed');
      plotCollapseBtn.textContent = plotPanel.classList.contains('collapsed') ? 'Expand' : 'Collapse';
    });
  }

  chartUpdate = function () {
    if (selectedMetric && plotPanel && plotPanel.getAttribute('aria-hidden') === 'false' && !plotPanel.classList.contains('collapsed')) drawChart();
  };

  function loadConfig() {
    fetch('/api/config')
      .then(function (r) { return r.json(); })
      .then(function (c) {
        if (c.environment) envBadge.textContent = c.environment;
        if (c.monitoring) {
          monitoringConfig = {
            csv_window_minutes: c.monitoring.csv_window_minutes != null ? c.monitoring.csv_window_minutes : 480,
            z_score: c.monitoring.z_score || { normal_max: 1.75, medium_max: 2.75, high_max: 2.75 }
          };
        }
        var envs = c.environments || [];
        if (envs.length && !envSelect.options.length) {
          envSelect.innerHTML = envs.map(function (e) {
            return '<option value="' + escapeHtml(e) + '">' + escapeHtml(e) + '</option>';
          }).join('');
          if (c.environment && envSelect.querySelector('option[value="' + c.environment + '"]')) {
            envSelect.value = c.environment;
          }
        }
        refreshData();
        if (zLegend) zLegend.textContent = 'Z: green |z|\u22641.75 \u2022 yellow \u22642.75 \u2022 red >2.75 \u2022 \u2191/\u2193 recent \u2022 \u2192 green=improve red=worsen';
        refreshDataTimer = setInterval(refreshData, REFRESH_INTERVAL_MS);
        return c;
      })
      .catch(function () {});
  }

  envSelect.addEventListener('change', function () {
    var env = getSelectedEnv();
    if (env) envBadge.textContent = env;
    refreshData();
  });

  loadConfig();
})();
