import unittest

from cloudwanderer import URN

from ..helpers import CloudWandererCalls, ExpectedCall, MultipleResourceScenario, NoMotoMock, SingleResourceScenario


class TestCustomerGateways(NoMotoMock, unittest.TestCase):

    vpn_connection_payload = {
        "CustomerGatewayConfiguration": '<?xml version="1.0" encoding="UTF-8"?>\n<vpn_connection id="vpn-11111111">\n  <customer_gateway_id>cgw-11111111111111111</customer_gateway_id>\n  <vpn_gateway_id>vgw-11111111111111111</vpn_gateway_id>\n  <vpn_connection_type>ipsec.1</vpn_connection_type>\n  <ipsec_tunnel>\n    <customer_gateway>\n      <tunnel_outside_address>\n        <ip_address>1.1.1.1</ip_address>\n      </tunnel_outside_address>\n      <tunnel_inside_address>\n        <ip_address>169.254.80.146</ip_address>\n        <network_mask>255.255.255.252</network_mask>\n        <network_cidr>30</network_cidr>\n      </tunnel_inside_address>\n      <bgp>\n        <asn>65000</asn>\n        <hold_time>30</hold_time>\n      </bgp>\n    </customer_gateway>\n    <vpn_gateway>\n      <tunnel_outside_address>\n        <ip_address>1.1.1.1</ip_address>\n      </tunnel_outside_address>\n      <tunnel_inside_address>\n        <ip_address>169.254.80.145</ip_address>\n        <network_mask>255.255.255.252</network_mask>\n        <network_cidr>30</network_cidr>\n      </tunnel_inside_address>\n      <bgp>\n        <asn>64512</asn>\n        <hold_time>30</hold_time>\n      </bgp>\n    </vpn_gateway>\n    <ike>\n      <authentication_protocol>sha1</authentication_protocol>\n      <encryption_protocol>aes-128-cbc</encryption_protocol>\n      <lifetime>28800</lifetime>\n      <perfect_forward_secrecy>group2</perfect_forward_secrecy>\n      <mode>main</mode>\n      <pre_shared_key>11111111111111111</pre_shared_key>\n    </ike>\n    <ipsec>\n      <protocol>esp</protocol>\n      <authentication_protocol>hmac-sha1-96</authentication_protocol>\n      <encryption_protocol>aes-128-cbc</encryption_protocol>\n      <lifetime>3600</lifetime>\n      <perfect_forward_secrecy>group2</perfect_forward_secrecy>\n      <mode>tunnel</mode>\n      <clear_df_bit>true</clear_df_bit>\n      <fragmentation_before_encryption>true</fragmentation_before_encryption>\n      <tcp_mss_adjustment>1379</tcp_mss_adjustment>\n      <dead_peer_detection>\n        <interval>10</interval>\n        <retries>3</retries>\n      </dead_peer_detection>\n    </ipsec>\n  </ipsec_tunnel>\n  <ipsec_tunnel>\n    <customer_gateway>\n      <tunnel_outside_address>\n        <ip_address>1.1.1.1</ip_address>\n      </tunnel_outside_address>\n      <tunnel_inside_address>\n        <ip_address>169.254.172.86</ip_address>\n        <network_mask>255.255.255.252</network_mask>\n        <network_cidr>30</network_cidr>\n      </tunnel_inside_address>\n      <bgp>\n        <asn>65000</asn>\n        <hold_time>30</hold_time>\n      </bgp>\n    </customer_gateway>\n    <vpn_gateway>\n      <tunnel_outside_address>\n        <ip_address>1.1.1.1</ip_address>\n      </tunnel_outside_address>\n      <tunnel_inside_address>\n        <ip_address>169.254.172.85</ip_address>\n        <network_mask>255.255.255.252</network_mask>\n        <network_cidr>30</network_cidr>\n      </tunnel_inside_address>\n      <bgp>\n        <asn>64512</asn>\n        <hold_time>30</hold_time>\n      </bgp>\n    </vpn_gateway>\n    <ike>\n      <authentication_protocol>sha1</authentication_protocol>\n      <encryption_protocol>aes-128-cbc</encryption_protocol>\n      <lifetime>28800</lifetime>\n      <perfect_forward_secrecy>group2</perfect_forward_secrecy>\n      <mode>main</mode>\n      <pre_shared_key>11111111111111111</pre_shared_key>\n    </ike>\n    <ipsec>\n      <protocol>esp</protocol>\n      <authentication_protocol>hmac-sha1-96</authentication_protocol>\n      <encryption_protocol>aes-128-cbc</encryption_protocol>\n      <lifetime>3600</lifetime>\n      <perfect_forward_secrecy>group2</perfect_forward_secrecy>\n      <mode>tunnel</mode>\n      <clear_df_bit>true</clear_df_bit>\n      <fragmentation_before_encryption>true</fragmentation_before_encryption>\n      <tcp_mss_adjustment>1379</tcp_mss_adjustment>\n      <dead_peer_detection>\n        <interval>10</interval>\n        <retries>3</retries>\n      </dead_peer_detection>\n    </ipsec>\n  </ipsec_tunnel>\n</vpn_connection>',  # noqa
        "CustomerGatewayId": "cgw-11111111111111111",
        "Category": "VPN",
        "State": "pending",
        "Type": "ipsec.1",
        "VpnConnectionId": "vpn-11111111",
        "VpnGatewayId": "vgw-11111111111111111",
        "Options": {
            "EnableAcceleration": False,
            "StaticRoutesOnly": False,
            "LocalIpv4NetworkCidr": "0.0.0.0/0",
            "RemoteIpv4NetworkCidr": "0.0.0.0/0",
            "TunnelInsideIpVersion": "ipv4",
            "TunnelOptions": [],
        },
        "Routes": [],
        "Tags": [{"Key": "Name", "Value": "test-vpn-connection"}],
        "VgwTelemetry": [
            {
                "AcceptedRouteCount": 0,
                "LastStatusChange": "2021-04-13T10:21:30.000Z",
                "OutsideIpAddress": "1.1.1.1",
                "Status": "DOWN",
                "StatusMessage": "IPSEC IS DOWN",
            },
            {
                "AcceptedRouteCount": 0,
                "LastStatusChange": "2021-04-13T10:21:30.000Z",
                "OutsideIpAddress": "1.1.1.1",
                "Status": "DOWN",
                "StatusMessage": "IPSEC IS DOWN",
            },
        ],
    }

    mock = {
        "ec2": {
            "describe_vpn_connections.return_value": {"VpnConnections": [vpn_connection_payload]},
        }
    }

    single_resource_scenarios = [
        SingleResourceScenario(
            urn=URN.from_string("urn:aws:123456789012:eu-west-2:ec2:vpn_connection:vpn-11111111111111111"),
            expected_results=[vpn_connection_payload],
            expected_call=ExpectedCall(
                "ec2", "describe_vpn_connections", [], {"VpnConnectionIds": ["vpn-11111111111111111"]}
            ),
        )
    ]
    multiple_resource_scenarios = [
        MultipleResourceScenario(
            arguments=CloudWandererCalls(
                regions=["eu-west-2"], service_names=["ec2"], resource_types=["vpn_connection"]
            ),
            expected_results=[vpn_connection_payload],
        )
    ]
