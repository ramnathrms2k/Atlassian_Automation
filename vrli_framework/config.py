# config.py
import re

VRLI_HOST = "lvn-rnd-unix-logs.lvn.broadcom.net"
BASE_URL = f"https://{VRLI_HOST}:9543/api/v1"

PRESETS = {
    "ANYTHING_BUT_SPACE": r"\S+", "INTEGER": r"-?\d+", 
    "IP4": r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",
    "HEX": r"[A-Fa-f0-9]+", "DECIMAL": r"-?\d*\.?\d+", 
    "LETTERS_NUM_UNDERSCORE": r"\w+", "MESSAGE_TEXT": r".*" 
}

KNOWN_DEFINITIONS = {
    "Jira_ResponseTime_ms": { 
        "regexPreset": "INTEGER", 
        "preContext": "\" \\d+ (\\d+ |- )", 
        "postContext": " \"",
        "pyRegex": r'" \d+ (\d+ |- )(?P<val>-?\d+) "' 
    },
    "Jira_UserID": { 
        "customRegex": "\\w{2}\\d{6}", 
        "preContext": "\\d+x\\d+x\\d ", 
        "postContext": "( \\[\\d+\\/\\w+\\/\\d+:\\d+:\\d+:\\d+ -0700] | \\[\\d+\\/\\w+\\/\\d+:\\d+:\\d+:\\d+ -0800] )",
        "pyRegex": r"\d+x\d+x\d (?P<val>\w{2}\d{6})(?: \[\d+\/\w+\/\d+:\d+:\d+:\d+ -0700] | \[\d+\/\w+\/\d+:\d+:\d+:\d+ -0800] )"
    },
    # --- NEW: Strict definition for Bot Users ---
    "Jira_Bot_UserID": { 
        # Match anything that is NOT a standard 2-letter 6-digit user ID
        # Context: "123x456x1 <BOT_USER> [20/Dec..."
        "customRegex": "(?!\\w{2}\\d{6})(.*)", 
        "preContext": "\\d+x\\d+x\\d ", 
        "postContext": "( \\[\\d+\\/\\w+\\/\\d+:\\d+:\\d+:\\d+ -0700] | \\[\\d+\\/\\w+\\/\\d+:\\d+:\\d+:\\d+ -0800] )",
        "pyRegex": r"\d+x\d+x\d (?P<val>(?!\w{2}\d{6})\S+)(?: \[\d+\/\w+\/\d+:\d+:\d+:\d+ -0700] | \[\d+\/\w+\/\d+:\d+:\d+:\d+ -0800] )"
    },
    "PSIRT_Issue": {
        "regexPreset": "ANYTHING_BUT_SPACE",
        "preContext": "PSIRT PSIRT\\[\\d{5}]: Issue ", 
        "postContext": " created",
        "pyRegex": r"PSIRT PSIRT\[\d{5}]: Issue (?P<val>\S+) created"
    },
    "JiraConf_HTTP_Response_Code": { 
        "regexPreset": "INTEGER", "preContext": " ", "postContext": "( - | \\d+ )",
        "pyRegex": r" (?P<val>-?\d+)(?: - | \d+ )"
    },
    "JiraConf_Access_URI": {
        "regexPreset": "ANYTHING_BUT_SPACE",
        "preContext": "( -0800] \"\\w+ | -0700] \"\\w+ )", "postContext": " HTTP",
        "pyRegex": r"(?: -0800] \"\w+ | -0700] \"\w+ )(?P<val>\S+) HTTP"
    },
    "Jira_Access_URI_MinusQP": {
        "regexPreset": "CUSTOM",
        "preContext": r"",
        "postContext": r"",
        "customRegex": r'"\w+\s([^?\s]+)',
        "pyRegex": r'(?P<val>"\w+\s([^?\s]+))'
    }
}
