#!/bin/bash

if [ -z "$KYTOS_HOST" ]; then
    echo '- "export KYTOS_HOST=127.0.0.1" and run again; or'
    echo '- "KYTOS_HOST=127.0.0.1 ./this_test.sh".'
    exit
fi

API_URL="http://$KYTOS_HOST:8181/api/kytos/flow_manager/v2"

echo -n 'Press any key to install 2 flows in 00:00:00:00:00:00:00:01...'
read

CMD="curl -sH \"Content-Type: application/json\" -X POST -d @add_flow_mod.json $API_URL/flows/00:00:00:00:00:00:00:01"
echo $CMD
eval "$CMD"
echo
echo

function list_vlans {
    echo -n 'Flows are updated every 5 seconds by default. Wait the interval and press any key.'
    read
    CMD="curl -s $API_URL/flows/00:00:00:00:00:00:00:01 | python -m json.tool | grep dl_vlan\\\""
    echo $CMD
    user_input='n'
    while [[ $user_input == 'n' || $user_input == 'N' ]]; do
        eval "$CMD"
        echo -n "$1 Repeat (n) or proceed (Y)? "
        read user_input
    done
    echo
}

list_vlans 'You should see VLANs 20 and 21.'

echo 'Press any key to delete flows with VLAN = 20'
read
CMD="curl -H \"Content-Type: application/json\" -X POST -d @delete_flow_mod.json $API_URL/delete/00:00:00:00:00:00:00:01"
echo $CMD
eval "$CMD"
echo
echo

list_vlans 'You should see VLAN 21 and _not_ 20.'
