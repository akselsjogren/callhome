import tempfile
import textwrap

from unittest.mock import MagicMock

import pytest

from callhome import client


@pytest.fixture
def mock_mktemp(monkeypatch, tmp_path):
    temp = tempfile.mkstemp(dir=str(tmp_path))
    monkeypatch.setattr(client, "_mktemp", MagicMock(return_value=temp))
    return temp[1]


def test_write_hosts_file_empty_file(tmp_path, mock_mktemp):
    host_list = [
        {"host": "foxtrot", "ip": "198.51.100.101"},
        {"host": "golf", "ip": "192.0.2.42"},
    ]
    hosts = tmp_path / "hosts"
    hosts.write_text("127.0.0.1 localhost")
    temp_host = client.write_hosts_file(host_list, hosts, "bar")
    assert temp_host == mock_mktemp
    with open(mock_mktemp) as f:
        assert f.read() == textwrap.dedent(
            """\
            127.0.0.1 localhost
            # --- callhome managed start ---
            198.51.100.101 foxtrot foxtrot.bar
            192.0.2.42 golf golf.bar
            # --- callhome managed end ---
            """
        )


def test_write_hosts_file_update_existing(tmp_path, mock_mktemp):
    host_list = [
        {"host": "foxtrot", "ip": "198.51.100.101"},
        {"host": "golf", "ip": "192.0.2.42"},
    ]
    hosts = tmp_path / "hosts"
    hosts.write_text(
        textwrap.dedent(
            """\
        127.0.0.1 localhost
        ::1       localhost
        # keep this
        # --- callhome managed start ---
        192.0.2.42 golf
        # --- callhome managed end ---
        198.51.100.200 hotel
        """
        )
    )
    temp_host = client.write_hosts_file(host_list, hosts, "foo.bar")
    assert temp_host == mock_mktemp
    with open(mock_mktemp) as f:
        assert f.read() == textwrap.dedent(
            """\
            127.0.0.1 localhost
            ::1       localhost
            # keep this
            # --- callhome managed start ---
            198.51.100.101 foxtrot foxtrot.foo.bar
            192.0.2.42 golf golf.foo.bar
            # --- callhome managed end ---
            198.51.100.200 hotel
            """
        )
