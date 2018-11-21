#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This fixture module provides abstractions that facilitate testing

import requests
import socket
import os
import time
import re
import collections
from fabric import Connection

# Check out https://github.com/viniarck/containernet-docker/blob/master/app/custom_topo.py#L55-L65

dpids = [
    "00:00:00:00:00:00:00:01",
    "00:00:00:00:00:00:00:02",
    "00:00:00:00:00:00:00:03",
    "00:00:00:00:00:00:00:04",
    "00:00:00:00:00:00:00:05",
]

PingResult = collections.namedtuple(
    "PingResult", "packets_sent packets_received packet_loss"
)


class HostsManager(object):

    """Class to facilitate data plane checks on hosts"""

    def __init__(self, host1_fqdn, host1_port, host2_fqdn, host2_port):
        """Constructor of HostsManager."""

        self.host1 = host1_fqdn
        self.host1_port = host1_port
        self.host2 = host2_fqdn
        self.host_port = host2_port

    def ping_from_host1_to_host2(self, dst_ip="10.0.0.2"):
        """ping from host1 to host2."""
        con = Connection(
            host=f"root@{self.host1}",
            port=self.host1_port,
            connect_kwargs={"password": "toor"},
        )
        cmd = f"ping {dst_ip} -c 3 -W 1"
        return con.run(cmd, hide=True)

    def parse_ping_output(self, lines):
        """
        Parse ping output, which is expected to have this pattern:


        PING 10.0.0.2 (10.0.0.2) 56(84) bytes of data.
        64 bytes from 10.0.0.2: icmp_seq=1 ttl=64 time=206 ms
        64 bytes from 10.0.0.2: icmp_seq=2 ttl=64 time=204 ms
        64 bytes from 10.0.0.2: icmp_seq=3 ttl=64 time=204 ms

        --- 10.0.0.2 ping statistics ---
        3 packets transmitted, 3 received, 0% packet loss, time 2002ms
        rtt min/avg/max/mdev = 204.563/205.132/206.223/0.931 ms

        """
        re_values = r".*?(\d+) packets transmitted.*?(\d+) received.*?(\d+)% packet loss"
        sent = 0
        received = 0
        loss = 0

        for line in lines.split("\n"):
            g = re.match(re_values, line)
            if g:
                sent = int(g.group(1))
                received = int(g.group(2))
                loss = int(g.group(3))

        return PingResult(
            packets_sent=sent, packets_received=received, packet_loss=loss
        )


class FlowManager(object):

    """Class to facilitate testing"""

    def __init__(self, host="localhost", tcp_port=8181, version="v2", api_retries=3):
        """Constructor of FlowManager."""
        self.host = host
        self.tcp_port = tcp_port
        self.version = version
        self.base_url = (
            f"http://{self.host}:{self.tcp_port}/api/kytos/flow_manager/{self.version}/"
        )
        self.api_retries = api_retries
        # wait up for a few seconds to make sure the REST API is reachable via TCP.
        self.try_to_connect_on_api()

    def try_to_connect_on_api(self):
        """Check if it's possible to open a TCP connection to the REST API."""
        for api_retry in range(0, self.api_retries):
            if self.is_api_up():
                break
            if api_retry == self.api_retries - 1:
                raise RuntimeError(
                    f"Couldn't connect to {self.host} on {self.tcp_port}"
                )
            time.sleep(1)

    def is_api_up(self, timeout=3):
        """Check if Kytos REST api is up and running."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((self.host, self.tcp_port))
        if result == 0:
            return True
        return False

    def build_urlendpoint(self, endpoint):
        """Build an url endpoint based on base_url.
        Make sure to add the trailing / in the endpoint whenever needed.
        """
        return f"{self.base_url}{endpoint}"

    def get_request_flows(self, dpid=""):
        """Get all flows, if given a dpid adds this dpid in the url request endpoint."""
        url = self.build_urlendpoint("flows")
        if dpid:
            url += "/" + dpid
        r = requests.get(url)
        return r

    def post_request_flow(self, flow_entries, dpid=""):
        """Push all flow_entries. If given a dpid add this dpid in the url request endpoint.

        flow_entries is a dictionary."""
        url = self.build_urlendpoint("flows")
        if dpid:
            url += "/" + dpid
        r = requests.post(url, json=flow_entries)
        return r


class FlowManagerFromEnv(FlowManager):

    """Construct FlowMananger with environment variables"""

    def __init__(self):
        """Constructor of FlowManagerFromEnv."""
        super().__init__(
            host=os.environ.get("KYTOS_HOST"),
            tcp_port=os.environ.get("KYTOS_TCP_PORT"),
            version=os.environ.get("KYTOS_FLOW_MANAGER_VERSION"),
        )
