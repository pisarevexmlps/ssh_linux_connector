from ssh_linux.parsers import parse_df_p, parse_meminfo, parse_os_release


def test_parse_os_release() -> None:
    raw = """
NAME="Ubuntu"
VERSION="22.04.4 LTS (Jammy Jellyfish)"
ID=ubuntu
VERSION_ID="22.04"
PRETTY_NAME="Ubuntu 22.04.4 LTS"
""".strip()

    parsed = parse_os_release(raw)

    assert parsed["os_pretty"] == "Ubuntu 22.04.4 LTS"
    assert parsed["os_id"] == "ubuntu"
    assert parsed["os_version_id"] == "22.04"


def test_parse_meminfo_memtotal() -> None:
    raw = """
MemTotal:       16384256 kB
MemFree:         1234567 kB
""".strip()

    assert parse_meminfo(raw) == 16384256


def test_parse_df_p_output() -> None:
    raw = """
Filesystem     1024-blocks     Used Available Capacity Mounted on
udev              1990848        0   1990848       0% /dev
tmpfs              404080     1460    402620       1% /run
/dev/sda1        30493204 12124260  16924612      42% /
""".strip()

    parsed = parse_df_p(raw)

    assert parsed == [
        {
            "filesystem": "udev",
            "size_kb": 1990848,
            "used_kb": 0,
            "avail_kb": 1990848,
            "mountpoint": "/dev",
        },
        {
            "filesystem": "tmpfs",
            "size_kb": 404080,
            "used_kb": 1460,
            "avail_kb": 402620,
            "mountpoint": "/run",
        },
        {
            "filesystem": "/dev/sda1",
            "size_kb": 30493204,
            "used_kb": 12124260,
            "avail_kb": 16924612,
            "mountpoint": "/",
        },
    ]
