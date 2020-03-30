#!/bin/bash

#MY_POOL_ID="<POOLID>"
#MY_USER_ID="<USERID>" # on pooltool website get this from your account profile page
THIS_GENESIS="8e4d2a343f3dcf93"
CURRENT_EPOCH="84"
ASSIGNED_SLOTS="0"

JSON="$( jq -n --compact-output --arg CURRENTEPOCH "$CURRENT_EPOCH" --arg POOLID "$MY_POOL_ID" --arg USERID "$MY_USER_ID" --arg GENESISPREF "$THIS_GENESIS" --arg ASSIGNED "$ASSIGNED_SLOTS"  '{currentepoch: $CURRENTEPOCH, poolid: $POOLID,  genesispref: $GENESISPREF, userid: $USERID, assigned_slots: $ASSIGNED}')"

echo "Packet Sent:"
echo "$JSON"

RESPONSE=$(curl -s -H "Accept: application/json" -H "Content-Type:application/json" -X POST --data "$JSON" "https://api.pooltool.io/v0/sendlogs")

echo "Response Received:"
echo "$RESPONSE"
