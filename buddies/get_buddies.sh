#!/usr/bin/env bash

## CHANGE THESE TO SUIT YOUR POOL TO YOUR POOL ID AS ON THE EXPLORER
MY_POOL_ID="XXXXXXXX"
## GET THIS FROM YOUR ACCOUNT PROFILE PAGE ON POOLTOOL WEBSITE
MY_API_KEY="XXXXXXXX"
## GET THIS FROM YOUR POOL MANAGE TAB ON POOLTOOL WEBSITE
MY_NODE_ID="XXXXXXXX"
## SET THIS TO THE LOCATION OF YOUR TOPOLOGY FILE THAT YOUR NODE USES
TOPOLOGY_FILE="$CNODE_HOME/files/ff-topology-buddies.json"

JSON="$(jq -n --compact-output --arg MY_API_KEY "$MY_API_KEY" --arg MY_POOL_ID "$MY_POOL_ID" --arg MY_NODE_ID "$MY_NODE_ID" '{apiKey: $MY_API_KEY, nodeId: $MY_NODE_ID, poolId: $MY_POOL_ID}')"
echo "Packet Sent: $JSON"
RESPONSE="$(curl -s -H "Accept: application/json" -H "Content-Type:application/json" -X POST --data "$JSON" "https://api.pooltool.io/v0/getbuddies")"
SUCCESS="$(echo $RESPONSE | jq '.success')"
if [ $SUCCESS ]; then
  echo "Success"
  echo $RESPONSE | jq '. | {Producers: .message}' > $TOPOLOGY_FILE
  echo "Topology saved to $TOPOLOGY_FILE.  Note topology will only take effect next time you restart your node"
else
  echo "Failure "
  echo $RESPONSE | jq '.message'
fi
