import os
import pwd

import pytest
from clan_cli.ssh.host import Host
from clan_cli.ssh.host_group import HostGroup
from clan_cli.ssh.host_key import HostKeyCheck
from sshd import Sshd


@pytest.fixture
def host_group(sshd: Sshd) -> HostGroup:
    login = pwd.getpwuid(os.getuid()).pw_name
    group = HostGroup(
        [
            Host(
                "127.0.0.1",
                port=sshd.port,
                user=login,
                key=sshd.key,
                host_key_check=HostKeyCheck.NONE,
            )
        ]
    )
    return group
