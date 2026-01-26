import tarfile
import urllib.request
import sys
import os
import difflib
import socket
import datetime
import re

# --- CONFIGURATION ---
JIRA_VERSION = "10.3.12"
LOCAL_BIN_DIR = "/export/jira/bin" 
TARGET_FILE = "setenv.sh"

# Download URL pattern
BASE_URL = "https://www.atlassian.com/software/jira/downloads/binary"
TAR_FILENAME = f"atlassian-jira-software-{JIRA_VERSION}.tar.gz"
DOWNLOAD_URL = f"{BASE_URL}/{TAR_FILENAME}"

# --- DUAL OUTPUT HANDLER ---
class OutputLogger:
    """
    Handles writing to both the console (with colors) and a file (plain text).
    """
    def __init__(self):
        self.hostname = socket.gethostname()
        self.timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        self.readable_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Create a unique filename
        self.filename = f"jira_drift_{self.hostname}_{self.timestamp}.txt"
        
        try:
            self.file = open(self.filename, "w", encoding="utf-8")
            print(f"--> Report file created: {self.filename}")
        except IOError as e:
            print(f"[!] Error creating log file: {e}")
            sys.exit(1)

    def log(self, text, end="\n"):
        """
        Writes text to stdout (as-is) and to file (stripping ANSI colors).
        """
        # 1. Print to Console (Preserve Colors)
        print(text, end=end)
        
        # 2. Write to File (Strip Colors)
        # Regex to remove ANSI escape sequences like \033[31m
        ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
        clean_text = ansi_escape.sub('', text)
        self.file.write(clean_text + end)

    def close(self):
        self.file.close()
        print(f"\n--> Report saved successfully to: {self.filename}")

# Initialize Logger Global
logger = OutputLogger()

# --- PRESENTATION LAYER (THEME SAFE) ---
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    RED = '\033[31m'    
    GREEN = '\033[32m'  
    MAGENTA = '\033[35m' 
    CYAN = '\033[36m'   

    @staticmethod
    def colorize(text, color_code):
        # We always return the color code here; 
        # the Logger class handles stripping it for the file.
        return f"{color_code}{text}{Colors.RESET}"

class FileLine:
    def __init__(self, number, content):
        self.number = number
        self.content = content
        self.stripped = content.strip()
        self.is_comment = self.stripped.startswith('#')
        self.is_empty = len(self.stripped) == 0
        self.is_logic = not (self.is_comment or self.is_empty)

def print_header(title):
    # Build a metadata block for the file
    meta = (
        f"Date:     {logger.readable_time}\n"
        f"Hostname: {logger.hostname}\n"
        f"File:     {TARGET_FILE}\n"
        f"Target:   v{JIRA_VERSION}"
    )
    
    logger.log("\n" + Colors.colorize('='*80, Colors.CYAN))
    logger.log(Colors.colorize(title.center(80), Colors.BOLD))
    logger.log(Colors.colorize('='*80, Colors.CYAN))
    logger.log(meta)
    logger.log(Colors.colorize('-'*80, Colors.CYAN) + "\n")

def format_jvm_args(content, indent_padding):
    """Wraps long JVM arguments for readability."""
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

def print_diff_line(tag, line_obj, is_default=False):
    if is_default:
        prefix = "DEF"
        color = Colors.RED
        icon = "[-]" 
    else:
        prefix = "LOC"
        color = Colors.GREEN
        icon = "[+]"

    meta = f"{icon} {prefix} | Ln {line_obj.number:>4} |"
    colored_meta = Colors.colorize(meta, Colors.MAGENTA)
    
    content_display = format_jvm_args(line_obj.content, 17)
    colored_content = Colors.colorize(content_display, color)
    
    logger.log(f"{colored_meta} {colored_content}")

# --- CORE LOGIC ---
def get_streamed_default_lines(url, filename_pattern):
    logger.log(f"--> Fetching default {TARGET_FILE} (v{JIRA_VERSION}) from Atlassian...")
    try:
        ftpstream = urllib.request.urlopen(url)
        tar = tarfile.open(fileobj=ftpstream, mode="r|gz")
        for member in tar:
            if member.name.endswith(f"/bin/{filename_pattern}"):
                f = tar.extractfile(member)
                return f.read().decode('utf-8').splitlines()
        sys.exit(1)
    except Exception as e:
        logger.log(f"[!] Error: {e}")
        sys.exit(1)

def get_local_lines(path):
    full_path = os.path.join(path, TARGET_FILE)
    if not os.path.exists(full_path):
        logger.log(f"[!] Error: Local file not found at {full_path}")
        sys.exit(1)
    with open(full_path, 'r', encoding='utf-8') as f:
        return f.read().splitlines()

def parse_file_structure(raw_lines):
    return [FileLine(i+1, line) for i, line in enumerate(raw_lines)]

def compare_subset(default_objs, local_objs, label):
    d_text = [x.stripped for x in default_objs]
    l_text = [x.stripped for x in local_objs]
    matcher = difflib.SequenceMatcher(None, d_text, l_text)
    
    changes_found = False
    logger.log(Colors.colorize('--- ' + label + ' ---', Colors.BOLD) + "\n")
    
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal': continue
        changes_found = True
        
        if tag == 'replace':
            logger.log(Colors.colorize('>>> MODIFIED (Values Changed)', Colors.BOLD))
            for k in range(i1, i2): print_diff_line(tag, default_objs[k], is_default=True)
            for k in range(j1, j2): print_diff_line(tag, local_objs[k], is_default=False)
            logger.log("") 
                
        elif tag == 'delete':
            logger.log(Colors.colorize('>>> REMOVED (Missing in Local)', Colors.BOLD))
            for k in range(i1, i2): print_diff_line(tag, default_objs[k], is_default=True)
            logger.log("")

        elif tag == 'insert':
            logger.log(Colors.colorize('>>> ADDED (Custom to Local)', Colors.BOLD))
            for k in range(j1, j2): print_diff_line(tag, local_objs[k], is_default=False)
            logger.log("")

    if not changes_found:
        logger.log(f"No changes detected in {label}.")

# --- MAIN ---
if __name__ == "__main__":
    try:
        raw_default = get_streamed_default_lines(DOWNLOAD_URL, TARGET_FILE)
        raw_local = get_local_lines(LOCAL_BIN_DIR)
        
        struct_default = parse_file_structure(raw_default)
        struct_local = parse_file_structure(raw_local)
        
        def_logic = [x for x in struct_default if x.is_logic]
        loc_logic = [x for x in struct_local if x.is_logic]
        
        def_comments = [x for x in struct_default if x.is_comment]
        loc_comments = [x for x in struct_local if x.is_comment]
        
        print_header(f"DRIFT REPORT")
        compare_subset(def_logic, loc_logic, "ACTIVE CONFIGURATION")
        
        logger.log("\n" + "-"*80 + "\n")
        compare_subset(def_comments, loc_comments, "COMMENTS & ANNOTATIONS")
        
    finally:
        # Ensure file is closed properly even if script errors out
        logger.close()
