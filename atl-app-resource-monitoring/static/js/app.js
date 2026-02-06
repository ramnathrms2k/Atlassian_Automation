(function () {
  const main = document.getElementById('main');
  const serverCards = document.getElementById('server-cards');
  const dbCards = document.getElementById('db-cards');
  const loading = document.getElementById('loading');
  const lastUpdated = document.getElementById('last-updated');
  const envBadge = document.getElementById('env-badge');
  const envSelect = document.getElementById('env-select');
  const btnRefresh = document.getElementById('btn-refresh');
  const btnMonitor = document.getElementById('btn-monitor');
  const intervalInput = document.getElementById('interval');
  const status = document.getElementById('status');

  let monitoring = false;
  let refreshTimer = null;
  let defaultInterval = 60;

  function getSelectedEnv() {
    const v = envSelect.value;
    return v || null;
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

  function renderServer(s) {
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
    if (mainProcess && mainPid) {
      processLabel = escapeHtml((mainProcess.comm || 'process') + ' (' + mainPid + ')');
      var appType = (s.app_type || 'jira').toLowerCase();
      var appVer = s.app_version || s.jira_version;
      if (appVer) {
        var productName = appType === 'confluence' ? 'Confluence' : 'Jira';
        processLabel += ' — ' + productName + ' ' + escapeHtml(appVer);
      }
      if (mainProcess.cpu_percent != null) {
        cpuDetail = 'process: ' + mainProcess.cpu_percent.toFixed(1) + '%';
      }
      if (heapMaxMb && mainJvm) {
        var rssMb = mainProcess.rss_kb != null ? mainProcess.rss_kb / 1024 : null;
        var heapUsedPct = mainJvm.heap_used_mb != null ? (100 * mainJvm.heap_used_mb / heapMaxMb).toFixed(1) : '—';
        var heapAvailPct = mainJvm.heap_used_mb != null ? (100 * Math.max(0, heapMaxMb - mainJvm.heap_used_mb) / heapMaxMb).toFixed(1) : '—';
        var nonHeapPct = mainJvm.non_heap_mb != null ? (100 * mainJvm.non_heap_mb / heapMaxMb).toFixed(1) : '—';
        var rssPctHeap = (rssMb != null && heapMaxMb > 0) ? (100 * rssMb / heapMaxMb).toFixed(1) : '—';
        memUsedDetail = 'heap: ' + heapUsedPct + '%, non-heap: ' + nonHeapPct + '%, RSS/heap: ' + rssPctHeap + '%';
        memAvailDetail = 'heap avail: ' + heapAvailPct + '%';
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
      html += '<div class="metrics-grid">';
      html += metric('Process', processLabel);
      html += metric('Load avg (1/5/15)', load[0].toFixed(2) + ' / ' + load[1].toFixed(2) + ' / ' + load[2].toFixed(2));
      html += metric('System CPU %', cpu + '%', cpu > 80, cpuDetail);
      html += metric('Memory used', (memUsedPct != null ? memUsedPct + '%' : '—'), memUsedPct > 85, memUsedDetail);
      html += metric('Memory available', (memAvailPct != null ? memAvailPct + '%' : '—'), false, memAvailDetail);
      html += metric('Swap used', (swapTotal > 0 && swapPct != null ? swapPct + '%' : (swapTotal === 0 ? 'N/A' : '—')), swapPct > 80);
      html += metric('Incoming (app port)', String(incoming));
      html += metric('DB connections', String(dbCount));
      html += '</div>';

      if (dbHost) {
        html += '<div class="db-info">DB: ' + escapeHtml(dbHost) + (dbPort ? ':' + dbPort : '') + '</div>';
      }
    }

    html += '</div>';
    return html;
  }

  function renderDbNode(d) {
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
      html += '<div class="metrics-grid">';
      html += metric('DB type', dbType);
      html += metric('Load avg (1/5/15)', load[0].toFixed(2) + ' / ' + load[1].toFixed(2) + ' / ' + load[2].toFixed(2));
      html += metric('System CPU %', cpu + '%', cpu > 80);
      html += metric('Memory used', (memUsedPct != null ? memUsedPct + '%' : '—'), memUsedPct > 85);
      html += metric('Memory available', (memAvailPct != null ? memAvailPct + '%' : '—'));
      html += metric('Swap used', (swapTotal > 0 && swapPct != null ? swapPct + '%' : (swapTotal === 0 ? 'N/A' : '—')), swapPct > 80);
      html += metric('Connections', String(conn));
      html += '</div>';
    }
    html += '</div>';
    return html;
  }

  function metric(label, value, warn, detail) {
    var c = warn ? ' metric-value warn' : ' metric-value';
    var out = '<div class="metric"><div class="metric-label">' + escapeHtml(label) + '</div><div class="' + c.trim() + '">' + escapeHtml(String(value)) + '</div>';
    if (detail) {
      out += '<div class="metric-detail">' + escapeHtml(detail) + '</div>';
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

  function fetchMetrics() {
    setStatus('Fetching…');
    return fetch(apiUrl('/api/metrics'))
      .then(function (r) {
        if (!r.ok) throw new Error(r.statusText);
        return r.json();
      })
      .then(function (data) {
        loading.style.display = 'none';
        if (data.error) {
          serverCards.innerHTML = '<div class="card"><div class="card-header"><span class="card-error">' + escapeHtml(data.error) + '</span></div></div>';
          dbCards.innerHTML = '';
        } else {
          const list = data.servers || [];
          serverCards.innerHTML = list.map(renderServer).join('');
          const dbList = data.db_nodes || [];
          dbCards.innerHTML = dbList.length ? dbList.map(renderDbNode).join('') : '<p class="section-empty">No DB nodes discovered from app config.</p>';
        }
        setLastUpdated();
        setStatus('');
        return data;
      })
      .catch(function (e) {
        loading.style.display = 'none';
        serverCards.innerHTML = '<div class="card"><div class="card-header"><span class="card-error">Request failed: ' + escapeHtml(e.message) + '</span></div></div>';
        setStatus('Request failed', true);
      });
  }

  function startMonitoring() {
    if (monitoring) return;
    monitoring = true;
    btnRefresh.disabled = true;
    btnMonitor.textContent = 'Stop monitoring';
    btnMonitor.classList.add('monitoring');
    const sec = Math.max(10, parseInt(intervalInput.value, 10) || 60);
    intervalInput.value = sec;
    setStatus('Monitoring every ' + sec + 's');
    function tick() {
      if (!monitoring) return;
      fetchMetrics().then(function () {
        refreshTimer = setTimeout(tick, sec * 1000);
      });
    }
    tick();
  }

  function stopMonitoring() {
    monitoring = false;
    if (refreshTimer) {
      clearTimeout(refreshTimer);
      refreshTimer = null;
    }
    btnRefresh.disabled = false;
    btnMonitor.textContent = 'Start monitoring';
    btnMonitor.classList.remove('monitoring');
    setStatus('');
  }

  btnRefresh.addEventListener('click', function () {
    if (monitoring) return;
    fetchMetrics();
  });

  btnMonitor.addEventListener('click', function () {
    if (monitoring) stopMonitoring();
    else startMonitoring();
  });

  function loadConfigAndMetrics() {
    fetch(apiUrl('/api/config'))
      .then(function (r) { return r.json(); })
      .then(function (c) {
        defaultInterval = c.refresh_interval_seconds || 60;
        intervalInput.value = defaultInterval;
        if (c.environment) envBadge.textContent = c.environment;
        const envs = c.environments || [];
        if (envs.length && !envSelect.options.length) {
          envSelect.innerHTML = envs.map(function (e) {
            return '<option value="' + escapeHtml(e) + '">' + escapeHtml(e) + '</option>';
          }).join('');
          if (c.environment && envSelect.querySelector('option[value="' + c.environment + '"]')) {
            envSelect.value = c.environment;
          }
        }
        return c;
      })
      .then(function () { return fetchMetrics(); })
      .catch(function () {});
  }

  envSelect.addEventListener('change', function () {
    const env = getSelectedEnv();
    if (env) envBadge.textContent = env;
    if (monitoring) return;
    loadConfigAndMetrics();
  });

  // Load config (populate dropdown), then fetch metrics for selected environment
  loadConfigAndMetrics();
})();
