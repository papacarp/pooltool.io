#!/usr/bin/env bash

# YOU CAN PASS THESE STRINGS AS ENVIRONMENTAL VARIABLES, OR EDIT THEM IN THE SCRIPT HERE
if [ -z "$PT_MY_POOL_ID" ]; then
## CHANGE THESE TO SUIT YOUR POOL TO YOUR POOL ID AS ON THE EXPLORER
PT_MY_POOL_ID="XXXXXXXX"
fi

if [ -z "$PT_MY_API_KEY" ]; then
## GET THIS FROM YOUR ACCOUNT PROFILE PAGE ON POOLTOOL WEBSITE
PT_MY_API_KEY="XXXXXXXX"
fi

if [ -z "$PT_MY_NODE_ID" ]; then
## GET THIS FROM YOUR POOL MANAGE TAB ON POOLTOOL WEBSITE
PT_MY_NODE_ID="XXXXXXXX"
fi

if [ -z "$PT_TOPOLOGY_FILE" ]; then
## SET THIS TO THE LOCATION OF YOUR TOPOLOGY FILE THAT YOUR NODE USES
PT_TOPOLOGY_FILE="$CNODE_HOME/files/ff-topology-buddies.json"
fi

JSON="$(jq -n --compact-output --arg MY_API_KEY "$PT_MY_API_KEY" --arg MY_POOL_ID "$PT_MY_POOL_ID" --arg MY_NODE_ID "$PT_MY_NODE_ID" '{apiKey: $MY_API_KEY, nodeId: $MY_NODE_ID, poolId: $MY_POOL_ID}')"
echo "Packet Sent: $JSON"
RESPONSE="$(curl -s -H "Accept: application/json" -H "Content-Type:application/json" -X POST --data "$JSON" "https://api.pooltool.io/v0/getbuddies")"
SUCCESS="$(echo $RESPONSE | jq '.success')"
if [ $SUCCESS ]; then
  echo "Success"
  echo $RESPONSE | jq '. | {Producers: .message}' > $PT_TOPOLOGY_FILE
  echo "Topology saved to $PT_TOPOLOGY_FILE.  Note topology will only take effect next time you restart your node"
else
  echo "Failure "
  echo $RESPONSE | jq '.message'
fi
