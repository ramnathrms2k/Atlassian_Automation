"""
Quick tests: parse_db_from_server_xml (Confluence server.xml) and example environment config load.
"""
import pytest

from app.dbconfig_parser import parse_db_from_server_xml
from app.config_loader import get_config, list_environments


# Realistic snippet from Confluence server.xml (Resource jdbc/confluence); host/port generic
SAMPLE_SERVER_XML = '''<Context path="" docBase="../confluence" reloadable="false">
		<Resource name="jdbc/confluence" auth="Container" type="javax.sql.DataSource"
                          username="wikiuser"
                          password="TOKEN"
                          driverClassName="com.mysql.cj.jdbc.Driver"
                          url="jdbc:mysql://db-host.example.com:3306/confluence?autoreconnect=true&amp;useUnicode=true&amp;useSSL=false"
			  maxTotal="250" maxIdle="7" defaultTransactionIsolation="READ_COMMITTED"
                          testOnBorrow="true" defaultAutoCommit="false"/>
</Context>'''


def test_parse_db_from_server_xml_mysql():
    """Parse JDBC MySQL URL from Confluence server.xml returns (host, port)."""
    got = parse_db_from_server_xml(SAMPLE_SERVER_XML)
    assert got == ("db-host.example.com", 3306)


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


def test_example_confluence_config():
    """Example-Confluence env loads with correct app_type, app_port, paths, and servers."""
    envs = list_environments()
    assert "Example-Confluence" in envs

    config = get_config("Example-Confluence")
    assert config.get("app_type") == "confluence"
    assert config.get("app_port") == 8090
    assert config.get("environment") == "Example-Confluence"
    assert config.get("domain") == ".example.com"

    paths = config.get("paths", {})
    assert paths.get("setenv") == "/export/confluence/bin/setenv.sh"
    assert paths.get("server_xml") == "/export/confluence/conf/server.xml"

    servers = config.get("servers", [])
    assert servers == ["conf-app-01", "conf-app-02", "conf-app-03"]


def test_example_jira_config():
    """Example-Jira has jira-friendly settings and app_type jira."""
    config = get_config("Example-Jira")
    assert config.get("app_type") == "jira"
    assert config.get("app_port") == 8080
    paths = config.get("paths", {})
    assert paths.get("dbconfig") == "/export/jirahome/dbconfig.xml"
    assert paths.get("setenv") == "/export/jira/bin/setenv.sh"
    servers = config.get("servers", [])
    assert "jira-app-01" in servers
