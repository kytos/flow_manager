"""Switch match."""

import ipaddress

from pyof.v0x01.common.flow_match import FlowWildCards

IPV4_ETH_TYPE = 2048


def format_request(request):
    """Format user request to match function format."""
    args = {}
    for key, value in request.items():
        args[key] = value
    return args


def do_match(flow_to_install, version, stored_flow_dict):
    """Match a packet against this flow."""
    if version == 0x01:
        return match10(stored_flow_dict, flow_to_install)
    elif version == 0x04:
        return match13_no_strict(flow_to_install, stored_flow_dict)
    raise NotImplementedError(f'Unsupported OpenFlow version {version}')


def _get_match_fields(flow_dict):
    """Generate match fields."""
    match_fields = {}
    if 'match' in flow_dict:
        for key, value in flow_dict['match'].items():
            match_fields[key] = value
    return match_fields


# pylint: disable=too-many-return-statements, too-many-statements, R0912
def _match_ipv4_10(match_fields, args, wildcards):
    """Match IPV4 fields against packet with Flow (OF1.0)."""
    if not match_fields['eth_type'] == IPV4_ETH_TYPE:
        return False
    flow_ip_int = int(ipaddress.IPv4Address(match_fields.get('ipv4_src')))
    if flow_ip_int != 0:
        mask = (wildcards
                & FlowWildCards.OFPFW_NW_SRC_MASK) >> \
                FlowWildCards.OFPFW_NW_SRC_SHIFT
        if mask > 32:
            mask = 32
        if mask != 32 and 'ipv4_src' not in args:
            return False
        mask = (0xffffffff << mask) & 0xffffffff
        ip_int = int(ipaddress.IPv4Address(args.get('ipv4_src')))
        if ip_int & mask != flow_ip_int & mask:
            return False
    flow_ip_int = int(ipaddress.IPv4Address(match_fields['ipv4_dst']))
    if flow_ip_int != 0:
        mask = (wildcards
                & FlowWildCards.OFPFW_NW_DST_MASK) >> \
                FlowWildCards.OFPFW_NW_DST_SHIFT
        if mask > 32:
            mask = 32
        if mask != 32 and 'ipv4_dst' not in args:
            return False
        mask = (0xffffffff << mask) & 0xffffffff
        ip_int = int(ipaddress.IPv4Address(args.get('ipv4_dst')))
        if ip_int & mask != flow_ip_int & mask:
            return False
    if not wildcards & FlowWildCards.OFPFW_NW_TOS:
        if 'ip_tos' not in args:
            return False
        if match_fields.get('ip_tos') != int(args.get('ip_tos')):
            return False
    if not wildcards & FlowWildCards.OFPFW_NW_PROTO:
        if 'ip_proto' not in args:
            return False
        if match_fields.get('ip_proto') != int(args.get('ip_proto')):
            return False
    if not wildcards & FlowWildCards.OFPFW_TP_SRC:
        if 'tp_src' not in args:
            return False
        if match_fields.get('tcp_src') != int(args.get('tp_src')):
            return False
    if not wildcards & FlowWildCards.OFPFW_TP_DST:
        if 'tp_dst' not in args:
            return False
        if match_fields.get('tcp_dst') != int(args.get('tp_dst')):
            return False
    return True


# pylint: disable=too-many-return-statements, too-many-statements, R0912
def match10(flow_dict, args):
    """Match a packet against this flow (OF1.0)."""
    match_fields = _get_match_fields(flow_dict)
    wildcards = match_fields.get('wildcards')
    if not wildcards & FlowWildCards.OFPFW_IN_PORT:
        if 'in_port' not in args:
            return False
        if match_fields.get('in_port') != int(args.get('in_port')):
            return False
    if not wildcards & FlowWildCards.OFPFW_DL_VLAN_PCP:
        if 'vlan_pcp' not in args:
            return False
        if match_fields.get('vlan_pcp') != int(args.get('vlan_pcp')):
            return False
    if not wildcards & FlowWildCards.OFPFW_DL_VLAN:
        if 'vlan_vid' not in args:
            return False
        if match_fields.get('vlan_vid') != args.get('vlan_vid')[-1]:
            return False
    if not wildcards & FlowWildCards.OFPFW_DL_SRC:
        if 'eth_src' not in args:
            return False
        if match_fields.get('eth_src') != args.get('eth_src'):
            return False
    if not wildcards & FlowWildCards.OFPFW_DL_DST:
        if 'eth_dst' not in args:
            return False
        if match_fields.get('eth_dst') != args.get('eth_dst'):
            return False
    if not wildcards & FlowWildCards.OFPFW_DL_TYPE:
        if 'eth_type' not in args:
            return False
        if match_fields.get('eth_type') != int(args.get('eth_type')):
            return False
    if not _match_ipv4_10(match_fields, args, wildcards):
        return False
    return flow_dict


def match13_no_strict(flow_to_install, stored_flow_dict):
    """Match a packet againts the stored flow (OF 1.3).

    Return the flow if any fields match, otherwise, return False.
    """
    if flow_to_install.get('cookie_mask') and 'cookie' in stored_flow_dict:
        cookie = flow_to_install['cookie_mask'] & flow_to_install['cookie']
        if cookie == stored_flow_dict['cookie']:
            return stored_flow_dict
        return False

    if 'match' not in flow_to_install:
        return False

    for key, value in flow_to_install.get('match').items():
        if 'match' not in stored_flow_dict:
            return False
        if key not in ('ipv4_src', 'ipv4_dst', 'ipv6_src', 'ipv6_dst'):
            if value == stored_flow_dict['match'].get(key):
                return stored_flow_dict
        else:
            field = flow_to_install.get(key)
            packet_ip = int(ipaddress.ip_address(field))
            ip_addr = value
            if packet_ip & ip_addr.netmask == ip_addr.address:
                return stored_flow_dict

    return False


def match_flows(flow_to_install, version, stored_flow_dict):
    # pylint: disable=bad-staticmethod-argument
    """
    Match the packet in request against the flows installed in the switch.

    Try the match with each flow, in other. If many is True, tries the
    match with all flows, if False, tries until the first match.
    :param args: packet data
    :param many: Boolean, indicating whether to continue after matching the
            first flow or not
    :return: If many, the list of matched flows, or the matched flow
    """
    match = do_match(flow_to_install, version, stored_flow_dict)
    return match
