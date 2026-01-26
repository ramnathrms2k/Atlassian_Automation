import sys
import os
import tarfile
import urllib.request
import difflib
import re
import glob
import shutil
import xml.etree.ElementTree as ET
import socket
import subprocess
import datetime
import textwrap

# --- CONFIGURATION LOADER ---
class Config:
    def __init__(self):
        self.defaults = {
            "JIRA_VERSION": "10.3.12",
            "JIRA_INSTALL_DIR": "/export/jira",
            "DB_VALIDATION_USER": "atlassian_readonly"
        }
        self.file_config = self._load_conf_file()
    
    def _load_conf_file(self):
        conf = {}
        conf_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "validator.conf")
        if os.path.exists(conf_path):
            try:
                with open(conf_path, 'r') as f:
                    for line in f:
                        if '=' in line and not line.strip().startswith('#'):
                            parts = line.split('=', 1)
                            conf[parts[0].strip()] = parts[1].strip().strip('"').strip("'")
            except: pass
        return conf

    def get(self, key):
        return os.environ.get(key, self.file_config.get(key, self.defaults.get(key)))

cfg = Config()
JIRA_VERSION = cfg.get("JIRA_VERSION")
JIRA_INSTALL_DIR = cfg.get("JIRA_INSTALL_DIR")
DB_VALIDATION_USER = cfg.get("DB_VALIDATION_USER")

# --- DOWNLOAD URLS ---
BASE_URL = "https://www.atlassian.com/software/jira/downloads/binary"
TAR_FILENAME = f"atlassian-jira-software-{JIRA_VERSION}.tar.gz"
DOWNLOAD_URL = f"{BASE_URL}/{TAR_FILENAME}"

class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'

class ReportLogger:
    def __init__(self):
        self.write_file = not os.environ.get('SKIP_FILE_WRITE')
        self.filename = None
        self.file_handle = None

        if self.write_file:
            self.hostname = socket.gethostname()
            self.timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            self.filename = f"jira_preflight_{self.hostname}_{self.timestamp}.txt"
            try:
                self.file_handle = open(self.filename, "w", encoding="utf-8")
                print(f"--> Log file created: {self.filename}") 
            except:
                self.write_file = False

    def log(self, text, color=None, end="\n"):
        if color and (sys.stdout.isatty() or os.environ.get('FORCE_COLOR')):
            print(f"{color}{text}{Colors.RESET}", end=end)
        else:
            print(text, end=end)
        
        if self.write_file and self.file_handle:
            ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
            clean_text = ansi_escape.sub('', text)
            self.file_handle.write(clean_text + end)
    
    def section(self, title, source=None):
        self.log(f"\n{'-'*80}", Colors.CYAN)
        self.log(f"   {title.upper()}", Colors.BOLD)
        if source:
            self.log(f"   Source: {source}", Colors.MAGENTA)
        self.log(f"{'-'*80}", Colors.CYAN)

    def kv(self, key, value, status=None):
        val_str = str(value)
        if status == "OK": val_str = f"{val_str} [OK]"; color = Colors.GREEN
        elif status == "FAIL": val_str = f"{val_str} [FAIL]"; color = Colors.RED
        elif status == "WARN": val_str = f"{val_str} [WARN]"; color = Colors.YELLOW
        else: color = Colors.RESET
        self.log(f"{key:<35}: ", Colors.BOLD, end="")
        self.log(val_str, color)

    def close(self):
        if self.write_file and self.file_handle:
            self.file_handle.close()
            print(f"--> Report saved locally to: {self.filename}")

logger = ReportLogger()

# --- UTILS ---
def check_disk_space(path):
    try:
        if not os.path.exists(path): return "N/A"
        total, used, free = shutil.disk_usage(path)
        return f"{free / (1024**3):.2f} GB Free ({(free/total)*100:.1f}%)"
    except: return "Error"

def check_writable(path):
    return "OK" if os.access(path, os.W_OK) else "FAIL"

def format_jvm_args(content, indent_padding):
    if len(content) > 100 and ("-D" in content or "-XX" in content):
        parts = content.split(' ')
        formatted = ""
        current_len = 0
        for part in parts:
            if current_len + len(part) > 95:
                formatted += f"\n{' ' * indent_padding} ↳ {part} "
                current_len = 0
            else:
                formatted += f"{part} "
                current_len += len(part)
        return formatted
    return content

# --- VALIDATORS ---
def validate_setenv():
    target_file = "setenv.sh"
    local_path = os.path.join(JIRA_INSTALL_DIR, "bin", target_file)
    logger.section("1. Binary Config Drift (setenv.sh)", source=local_path)
    
    if not os.path.exists(local_path):
        logger.log(f"CRITICAL: {local_path} not found!", Colors.RED)
        return None

    logger.log(f"Comparing against remote v{JIRA_VERSION}...", Colors.BLUE)
    
    # --- IMPROVED JRE EXTRACTION LOGIC (FROM USER) ---
    extracted_jre = None

    try:
        ftpstream = urllib.request.urlopen(DOWNLOAD_URL)
        tar = tarfile.open(fileobj=ftpstream, mode="r|gz")
        remote_lines = []
        for member in tar:
            if member.name.endswith(f"/bin/{target_file}"):
                f = tar.extractfile(member)
                remote_lines = f.read().decode('utf-8').splitlines()
                break
        
        with open(local_path, 'r') as f:
            local_lines = f.read().splitlines()

        # Apply User's Corner Case Logic
        for line in local_lines:
            if ("JAVA_HOME=" in line or "JRE_HOME=" in line) and not line.strip().startswith('#'):
                # 1. Clean trailing commands (semicolon logic)
                clean_line = line.split(';')[0]
                
                # 2. Split Key and Value
                parts = clean_line.split('=')
                
                # 3. Extract path
                if len(parts) >= 2:
                    extracted_jre = parts[1].strip().strip('"').strip("'")

        d_logic = [x.strip() for x in remote_lines if x.strip() and not x.strip().startswith('#')]
        l_logic = [x.strip() for x in local_lines if x.strip() and not x.strip().startswith('#')]
        
        diff_found = False
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, d_logic, l_logic).get_opcodes():
            if tag != 'equal':
                diff_found = True
                if tag in ['replace', 'insert']:
                    for k in range(j1, j2):
                        logger.log(f"[CUSTOM] {format_jvm_args(l_logic[k], 9)}", Colors.GREEN)
        
        if not diff_found: logger.log("No custom logic drift detected.", Colors.YELLOW)
        return extracted_jre
    except Exception as e:
        logger.log(f"Error checking setenv: {e}", Colors.RED)
        return None

def validate_java_env(jre_path):
    logger.section("2. Java Runtime & Security", source=f"{jre_path or 'Not Set'}")
    if not jre_path: return
    java_bin = os.path.join(jre_path, "bin", "java")
    if os.path.exists(java_bin):
        try:
            res = subprocess.run([java_bin, "-version"], capture_output=True, text=True)
            logger.log(f"--> Execution: {java_bin} -version", Colors.MAGENTA)
            for line in (res.stderr or res.stdout).splitlines(): logger.log(f"   {line}")
        except: logger.log(f"Failed to execute java", Colors.RED)
    
    cacerts_path = os.path.join(jre_path, "lib", "security", "cacerts")
    if not os.path.exists(cacerts_path): cacerts_path = os.path.join(jre_path, "jre", "lib", "security", "cacerts")
    if os.path.exists(cacerts_path):
        logger.log(f"\n--> Truststore Check: {cacerts_path}", Colors.MAGENTA)
        res = subprocess.run(["ls", "-latr", cacerts_path], capture_output=True, text=True)
        logger.log(f"   {res.stdout.strip()}")
        logger.kv("Cacerts Status", "Found", "OK")

def validate_server_xml():
    xml_path = os.path.join(JIRA_INSTALL_DIR, "conf", "server.xml")
    logger.section("3. Tomcat Config (server.xml)", source=xml_path)
    if not os.path.exists(xml_path): return
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        for i, conn in enumerate(root.findall(".//Connector"), 1):
            logger.log(f"--- Connector #{i} [Port: {conn.get('port')}] ---", Colors.MAGENTA)
            logger.kv("   Protocol", conn.get('protocol', 'HTTP/1.1'))
            logger.kv("   Scheme/Secure", f"{conn.get('scheme')} / {conn.get('secure')}")
            if conn.get('proxyName'): logger.kv("   Proxy Config", f"{conn.get('proxyName')}:{conn.get('proxyPort')}", "OK")
            else: logger.kv("   Proxy Config", "None (Direct Access)")
        
        logger.log("\n--- Active Valves ---", Colors.MAGENTA)
        for i, valve in enumerate(root.findall(".//Valve"), 1):
            cls = valve.get('className', '').split('.')[-1]
            det = "Custom"
            if 'AccessLogValve' in cls: 
                det = f"Pattern: {valve.get('pattern', 'common')} | Dir: {valve.get('directory', 'logs')}"
            elif 'RemoteIpValve' in cls: 
                det = f"Internal Proxies: {valve.get('internalProxies', 'Default/None')}"
            logger.kv(f"   {i}. {cls}", det)
    except: logger.log("Failed to parse server.xml", Colors.RED)

def validate_topology():
    app_prop = os.path.join(JIRA_INSTALL_DIR, "atlassian-jira", "WEB-INF", "classes", "jira-application.properties")
    logger.section("4. Topology & Filesystem", source=app_prop)
    jira_home = None
    try:
        with open(app_prop, 'r') as f:
            for line in f:
                if line.startswith("jira.home"): jira_home = line.split('=')[1].strip()
    except: pass
    
    if not jira_home: return None, None
    logger.kv("Local Home", jira_home, check_writable(jira_home))
    logger.kv("Disk Space (Local)", check_disk_space(jira_home))
    
    cl_prop = os.path.join(jira_home, "cluster.properties")
    if os.path.exists(cl_prop):
        logger.log(f"\n   Source: {cl_prop}", Colors.MAGENTA)
        sh, nid = None, "N/A"
        with open(cl_prop, 'r') as f:
            for line in f:
                if line.startswith("jira.shared.home"): sh = line.split('=')[1].strip()
                if line.startswith("jira.node.id"): nid = line.split('=')[1].strip()
        logger.kv("Clustering", "ENABLED", "OK")
        logger.kv("Node ID", nid)
        if sh:
            logger.kv("Shared Home", sh, check_writable(sh))
            logger.kv("Disk Space (Shared)", check_disk_space(sh))
    else: logger.kv("Clustering", "DISABLED", "WARN")
    return jira_home, None

def validate_database(jira_home):
    if not jira_home: return None
    dbconfig = os.path.join(jira_home, "dbconfig.xml")
    logger.section("5. Database Connectivity", source=dbconfig)
    if not os.path.exists(dbconfig): return None
    try:
        tree = ET.parse(dbconfig)
        root = tree.getroot()
        url = root.findtext(".//url")
        user = DB_VALIDATION_USER if DB_VALIDATION_USER else root.findtext(".//username")
        
        logger.kv("Connection User", user, "OK" if DB_VALIDATION_USER else "WARN")
        
        db_type = root.findtext(".//database-type", "mysql").lower()
        host, port, name = "Unknown", "3306", "jiradb"
        
        if "postgres" in db_type:
            m = re.search(r'jdbc:postgresql://([^:/]+)(?::(\d+))?/([^?]+)', url)
            if m: host, port, name = m.group(1), m.group(2) or "5432", m.group(3)
        elif "address=" in url:
            m_host = re.search(r'host=([^)]+)', url)
            m_port = re.search(r'port=([^)]+)', url)
            m_name = re.search(r'\)/([^/?]+)', url)
            if m_host: host = m_host.group(1)
            if m_port: port = m_port.group(1)
            if m_name: name = m_name.group(1)
        else:
            m = re.search(r'jdbc:mysql://([^:/]+)(?::(\d+))?/([^?]+)', url)
            if m: host, port, name = m.group(1), m.group(2) or "3306", m.group(3)

        logger.kv("DB Host/Port", f"{host}:{port}")
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        if sock.connect_ex((host, int(port))) == 0: logger.kv("TCP Reachability", "Success", "OK")
        else: 
            logger.kv("TCP Reachability", "Failed", "FAIL")
            return db_type
            
        pw = os.environ.get('ATLASSIAN_DB_PASSWORD')
        if pw and "Unknown" not in name:
            logger.log("\n--> Querying Cluster Nodes...", Colors.BLUE)
            sql = f"SELECT node_id, node_state, ip FROM {name}.clusternode;"
            cmd = ["mysql", f"-h{host}", f"-P{port}", f"-u{user}", f"-p{pw}", "-N", "-B", "-e", sql]
            if "postgres" in db_type:
                cmd = ["psql", "-h", host, "-p", port, "-U", user, "-d", name, "-t", "-A", "-c", sql]
                os.environ['PGPASSWORD'] = pw
            
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0:
                logger.log(f"{'Node ID':<20} {'State':<15} {'IP/Host'}")
                logger.log("-" * 60)
                for line in res.stdout.strip().split('\n'):
                    p = re.split(r'[\t|]', line)
                    if len(p)>=3: logger.log(f"{p[0]:<20} {p[1]:<15} {p[2]}")
                logger.kv("Cluster Query", "Success", "OK")
            else: logger.log("Query Failed", Colors.RED)
        else:
            logger.log("\n--> Skipping SQL Query (Password not set in ATLASSIAN_DB_PASSWORD env var)", Colors.YELLOW)
        
        return db_type
    except Exception as e:
        logger.log(f"Error: {e}", Colors.RED)
        return "unknown"

def validate_libs(db_type):
    logger.section("6. Library Dependencies", source=os.path.join(JIRA_INSTALL_DIR, "lib"))
    pat = "*mysql*"
    if "postgres" in db_type: pat = "*postgres*"
    elif "mssql" in db_type: pat = "*mssql*"
    drivers = glob.glob(os.path.join(JIRA_INSTALL_DIR, "lib", pat))
    if drivers: 
        for d in drivers: logger.kv("Driver Found", os.path.basename(d), "OK")
    else: logger.kv("Driver Found", "NONE", "FAIL")

if __name__ == "__main__":
    logger.log(f"REPORT_METADATA_START|Hostname:{socket.gethostname()}|Date:{datetime.datetime.now()}|Target:{JIRA_VERSION}|REPORT_METADATA_END")
    logger.section(f"JIRA DC NODE VALIDATOR - v{JIRA_VERSION}")
    jre = validate_setenv()
    validate_java_env(jre)
    validate_server_xml()
    home, _ = validate_topology()
    dbt = validate_database(home) if home else None
    if dbt: validate_libs(dbt)
    logger.close()
