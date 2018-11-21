#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pytest
from . import fixtures

# TODO after each test case tear down all installed flows.


@pytest.fixture(scope="module")
def topo_dpids():
    """Get all dpids from the custom topology."""
    return fixtures.dpids


@pytest.fixture(scope="module")
def flow_mngr():
    """Instantiate flow manager fixture for testing."""
    return fixtures.FlowManager()


@pytest.fixture(scope="module")
def hosts_mngr():
    """Instantiate HostsManager for data plane tests."""
    return fixtures.HostsManager(
        host1_fqdn="localhost", host1_port=2222, host2_fqdn="localhost", host2_port=2223
    )


def test_get_flows_from_single_dpid(topo_dpids, flow_mngr):
    mngr = flow_mngr
    dpid = topo_dpids[0]

    r = mngr.get_request_flows(dpid)
    assert r.status_code == 200
    d_resp = r.json()
    print(d_resp)
    # assert the key exists in the request payload
    assert d_resp[dpid]


def test_get_flows_from_all_dpids(topo_dpids, flow_mngr):
    mngr = flow_mngr

    r = mngr.get_request_flows()
    assert r.status_code == 200

    d_resp = r.json()
    # all dpids must be in the response
    for dpid in topo_dpids:
        assert d_resp[dpid]


def test_install_untagged_flow_single_dpid(topo_dpids, flow_mngr):
    flow_entries = {
        "flows": [
            {
                "priority": 4000,
                "match": {"in_port": 1},
                "actions": [{"action_type": "output", "port": 2}],
            }
        ]
    }
    mngr = flow_mngr
    dpids = topo_dpids
    r = mngr.post_request_flow(flow_entries=flow_entries, dpid=dpids[0])
    assert r.status_code == 200

    d_resp = r.json()
    assert d_resp["response"] == "FlowMod Messages Sent"

    # Check control plane
    r = mngr.get_request_flows(dpid=dpids[0])
    assert r.status_code == 200
    d_resp = r.json()

    flow_entry = None
    for _flow_entry in d_resp[dpids[0]]["flows"]:
        if _flow_entry["priority"] == 4000:
            flow_entry = _flow_entry
    assert flow_entry

    # Check a few main fields of the flow entry
    assert flow_entry["match"] == {"in_port": 1}
    assert flow_entry["actions"] == [{"action_type": "output", "port": 2}]


def test_install_untagged_flow_whole_topo_hosts(topo_dpids, flow_mngr, hosts_mngr):
    flow_entries = {
        "flows": [
            {
                "priority": 3000,
                "match": {"in_port": 1},
                "actions": [{"action_type": "output", "port": 2}],
            },
            {
                "priority": 3000,
                "match": {"in_port": 2},
                "actions": [{"action_type": "output", "port": 1}],
            },
        ]
    }
    mngr = flow_mngr
    # push bidir flow mods on each dpid
    for dpid in topo_dpids:
        r = mngr.post_request_flow(flow_entries=flow_entries, dpid=dpid)
        assert r.status_code == 200
        d_resp = r.json()
        assert d_resp["response"] == "FlowMod Messages Sent"

    # check data plane
    res = hosts_mngr.ping_from_host1_to_host2()
    ping_res = hosts_mngr.parse_ping_output(res.stdout)
    assert ping_res.packets_sent > 0
    assert ping_res.packets_received > 0
    print(ping_res)
