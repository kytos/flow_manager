"""Switch match."""

import ipaddress

from pyof.v0x01.common.flow_match import FlowWildCards

IPV4_ETH_TYPE = 2048


def match_flow(flow_to_install, version, stored_flow_dict):
    """Check that the flow fields match.

    It has support for (OF 1.0) and (OF 1.3) flows.
    If fields match, return the flow, otherwise return False.
    Does not require that all fields match.
    """
    if version == 0x01:
        return match10_no_strict(flow_to_install, stored_flow_dict)
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
    if match_fields.get('dl_type') == IPV4_ETH_TYPE:
        return False
    flow_ip_int = int(ipaddress.IPv4Address(match_fields.get('nw_src', 0)))
    if flow_ip_int != 0:
        mask = (wildcards
                & FlowWildCards.OFPFW_NW_SRC_MASK) >> \
                FlowWildCards.OFPFW_NW_SRC_SHIFT
        if mask > 32:
            mask = 32
        if mask != 32 and 'nw_src' not in args:
            return False
        mask = (0xffffffff << mask) & 0xffffffff
        ip_int = int(ipaddress.IPv4Address(args.get('nw_src')))
        if ip_int & mask != flow_ip_int & mask:
            return False
    flow_ip_int = int(ipaddress.IPv4Address(match_fields.get('nw_dst', 0)))
    if flow_ip_int != 0:
        mask = (wildcards
                & FlowWildCards.OFPFW_NW_DST_MASK) >> \
                FlowWildCards.OFPFW_NW_DST_SHIFT
        if mask > 32:
            mask = 32
        if mask != 32 and 'nw_dst' not in args:
            return False
        mask = (0xffffffff << mask) & 0xffffffff
        ip_int = int(ipaddress.IPv4Address(args.get('nw_dst')))
        if ip_int & mask != flow_ip_int & mask:
            return False
    if not wildcards & FlowWildCards.OFPFW_NW_TOS:
        if ('nw_tos', 'nw_proto', 'tp_src', 'tp_dst') not in args:
            return True
        if match_fields.get('nw_tos') != int(args.get('nw_tos')):
            return False
    if not wildcards & FlowWildCards.OFPFW_NW_PROTO:
        if match_fields.get('nw_proto') != int(args.get('nw_proto')):
            return False
    if not wildcards & FlowWildCards.OFPFW_TP_SRC:
        if match_fields.get('tp_src') != int(args.get('tp_src')):
            return False
    if not wildcards & FlowWildCards.OFPFW_TP_DST:
        if match_fields.get('tp_dst') != int(args.get('tp_dst')):
            return False
    return True


# pylint: disable=too-many-return-statements, too-many-statements, R0912
def match10_no_strict(flow_dict, args):
    """Match a packet against this flow (OF1.0)."""
    args = _get_match_fields(args)
    match_fields = _get_match_fields(flow_dict)
    wildcards = match_fields.get('wildcards', 0)
    if not wildcards & FlowWildCards.OFPFW_IN_PORT:
        if match_fields.get('in_port') != args.get('in_port'):
            return False
    if not wildcards & FlowWildCards.OFPFW_DL_VLAN_PCP:
        if match_fields.get('dl_vlan_pcp') != args.get('dl_vlan_pcp'):
            return False
    if not wildcards & FlowWildCards.OFPFW_DL_VLAN:
        if match_fields.get('dl_vlan') != args.get('dl_vlan'):
            return False
    if not wildcards & FlowWildCards.OFPFW_DL_SRC:
        if match_fields.get('dl_src') != args.get('dl_src'):
            return False
    if not wildcards & FlowWildCards.OFPFW_DL_DST:
        if match_fields.get('dl_dst') != args.get('dl_dst'):
            return False
    if not wildcards & FlowWildCards.OFPFW_DL_TYPE:
        if match_fields.get('dl_type') != args.get('dl_type'):
            return False
    if not _match_ipv4_10(match_fields, args, wildcards):
        return False
    return flow_dict


def match13_no_strict(flow_to_install, stored_flow_dict):
    """Match a packet againts the stored flow (OF 1.3).

    Return the flow if any fields match, otherwise, return False.
    """
    if flow_to_install.get('cookie_mask') and 'cookie' in stored_flow_dict:
        cookie = flow_to_install['cookie'] & flow_to_install['cookie_mask']
        stored_cookie = (stored_flow_dict['cookie'] &
                         flow_to_install['cookie_mask'])
        if cookie == stored_cookie:
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
            field = stored_flow_dict['match'].get(key)
            if not field:
                return False
            masked_ip_addr = ipaddress.ip_network(value, False)
            field_mask = field + "/" + str(masked_ip_addr.netmask)
            masked_stored_ip = ipaddress.ip_network(field_mask, False)
            if masked_ip_addr == masked_stored_ip:
                return stored_flow_dict
    return False
