"""
Quick tests: parse_db_from_server_xml (Confluence server.xml) and VMW-Confluence config load.
"""
import pytest

from app.dbconfig_parser import parse_db_from_server_xml
from app.config_loader import get_config, list_environments


# Realistic snippet from Confluence server.xml (Resource jdbc/confluence)
SAMPLE_SERVER_XML = '''<Context path="" docBase="../confluence" reloadable="false">
		<Resource name="jdbc/confluence" auth="Container" type="javax.sql.DataSource"
                          username="wikiuser"
                          password="Confprd@123"
                          driverClassName="com.mysql.cj.jdbc.Driver"
                          url="jdbc:mysql://db-lvnv-it-105.lvn.broadcom.net:3306/confluence?autoreconnect=true&amp;useUnicode=true&amp;useSSL=false&amp;characterEncoding=utf8&amp;useLocalSessionState=true"
			  maxTotal="250"
                          maxIdle="7"
                          defaultTransactionIsolation="READ_COMMITTED"
                          testOnBorrow="true"
			  defaultAutoCommit="false"/>
</Context>'''


def test_parse_db_from_server_xml_mysql():
    """Parse JDBC MySQL URL from Confluence server.xml returns (host, port)."""
    got = parse_db_from_server_xml(SAMPLE_SERVER_XML)
    assert got == ("db-lvnv-it-105.lvn.broadcom.net", 3306)


def test_parse_db_from_server_xml_postgresql():
    """Parse JDBC PostgreSQL URL works as well."""
    xml = '<Resource url="jdbc:postgresql://pg-host.example.com:5432/confluence"/>'
    assert parse_db_from_server_xml(xml) == ("pg-host.example.com", 5432)


def test_parse_db_from_server_xml_empty():
    """Empty or whitespace content returns None."""
    assert parse_db_from_server_xml("") is None
    assert parse_db_from_server_xml("   \n  ") is None


def test_parse_db_from_server_xml_no_jdbc():
    """Content without a JDBC URL returns None."""
    assert parse_db_from_server_xml("<Server port=\"8000\"/>") is None


def test_vmw_confluence_config():
    """VMW-Confluence env loads with correct app_type, app_port, paths, and servers."""
    envs = list_environments()
    assert "VMW-Confluence" in envs

    config = get_config("VMW-Confluence")
    assert config.get("app_type") == "confluence"
    assert config.get("app_port") == 8090
    assert config.get("environment") == "VMW-Confluence"
    assert config.get("domain") == ".lvn.broadcom.net"

    paths = config.get("paths", {})
    assert paths.get("setenv") == "/export/confluence/bin/setenv.sh"
    assert paths.get("server_xml") == "/export/confluence/conf/server.xml"

    servers = config.get("servers", [])
    assert servers == ["conf-lvnv-it-101", "conf-lvnv-it-102", "conf-lvnv-it-103"]


def test_vmw_jira_config_unchanged():
    """VMW-Jira still has jira-friendly settings and app_type jira."""
    config = get_config("VMW-Jira")
    assert config.get("app_type") == "jira"
    assert config.get("app_port") == 8080
    paths = config.get("paths", {})
    assert paths.get("dbconfig") == "/export/jirahome/dbconfig.xml"
    assert paths.get("setenv") == "/export/jira/bin/setenv.sh"
    servers = config.get("servers", [])
    assert "jira-lvnv-it-101" in servers
