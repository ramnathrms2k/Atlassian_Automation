"""
Parse Jira dbconfig.xml (or similar) to extract DB host and port.
Supports JDBC URLs in XML or plain text.
"""
import re
from typing import Optional


def parse_db_host_port(content: str) -> Optional[tuple[str, int]]:
    """
    Parse dbconfig.xml content and return (host, port) for the datasource.
    Returns None if not found or parse error.
    """
    if not content or not content.strip():
        return None

    # MySQL connector "address" format: jdbc:mysql://address=(protocol=tcp)(host=hostname)(port=3306)/db
    # Match (host=...) and (port=...) from the same address block
    addr_block = re.search(
        r"\(host=([^)]+)\).*?\(port=(\d+)\)",
        content,
        re.IGNORECASE | re.DOTALL,
    )
    if addr_block:
        try:
            return (addr_block.group(1).strip(), int(addr_block.group(2)))
        except ValueError:
            pass

    # Simple JDBC URL: jdbc:postgresql://host:port/db, jdbc:mysql://host:port/db, etc.
    pattern = re.compile(
        r"jdbc:(?:postgresql|mysql|oracle):(?://)?([^:/]+):(\d+)(?:/|$)",
        re.IGNORECASE,
    )
    match = pattern.search(content)
    if match:
        host, port_str = match.group(1), match.group(2)
        try:
            return (host.strip(), int(port_str))
        except ValueError:
            pass

    # Fallback: look for host and port in XML elements
    host_el = re.search(r"<host[^>]*>([^<]+)</host>", content, re.I)
    port_el = re.search(r"<port[^>]*>(\d+)</port>", content, re.I)
    if host_el and port_el:
        try:
            return (host_el.group(1).strip(), int(port_el.group(1)))
        except ValueError:
            pass
    return None


def parse_db_from_server_xml(content: str) -> Optional[tuple[str, int]]:
    """
    Parse Confluence server.xml (or similar) for Resource jdbc/confluence url=.
    Returns (host, port) from jdbc:mysql://host:port/... or jdbc:postgresql://host:port/...
    """
    if not content or not content.strip():
        return None
    # url="jdbc:mysql://host:port/db?..." or url='...' (may contain &amp;)
    pattern = re.compile(
        r'url=["\']jdbc:(?:mysql|postgresql)://([^:/]+):(\d+)(?:/|\?|")',
        re.IGNORECASE,
    )
    match = pattern.search(content)
    if match:
        try:
            return (match.group(1).strip(), int(match.group(2)))
        except ValueError:
            pass
    return None
