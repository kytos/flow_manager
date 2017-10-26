#!/bin/bash

if [ -z "$KYTOS_HOST" ]; then
    echo '- "export KYTOS_HOST=127.0.0.1" and run again; or'
    echo '- "KYTOS_HOST=127.0.0.1 ./this_test.sh".'
    exit
fi

API_URL="http://$KYTOS_HOST:8181/api/kytos/flow_manager/v1"

echo 'Press any key to install 2 flows in 00:00:00:00:00:00:00:01...'
read

CMD="curl -H \"Content-Type: application/json\" -X POST -d @add_flow_mod.json $API_URL/flows/00:00:00:00:00:00:00:01"
echo $CMD
eval "$CMD"
echo

cat <<VERIFY
--------------------------------------------------------------------------------
Flows are updated every 5 seconds by default. Assert they were installed:

1. Kytos controller:
kytos $> flows = controller.switches['00:00:00:00:00:00:00:01'].flows
kytos $> [flow.match.dl_vlan for flow in flows]
Out[ ]: [20, 21]

2. REST:
curl http://$KYTOS_HOST:8181/api/kytos/flow_manager/v1/flows/00:00:00:00:00:00:00:01 | python -m json.tool | grep dl_vlan
                    "dl_vlan": 21,
                    "dl_vlan_pcp": 0,
                    "dl_vlan": 20,
                    "dl_vlan_pcp": 0,
--------------------------------------------------------------------------------
VERIFY

echo 'Press any key to delete flows with VLAN = 20'
read
CMD="curl -H \"Content-Type: application/json\" -X POST -d @delete_flow_mod.json $API_URL/delete/00:00:00:00:00:00:00:01"
echo $CMD
eval "$CMD"
echo

echo 'Check the flows again and VLAN = 20 should not be found.'
