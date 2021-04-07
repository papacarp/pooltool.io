#!/usr/bin/env bash

## CHANGE THESE TO SUITE YOUR POOL

# your pool id as on the explorer
PT_MY_POOL_ID="xxxx"
# get this from your account profile page on pooltool website
PT_MY_API_KEY="xxxx-xx-xx-xx-xxxx"
# Your node ID (optional, this is reserved for future use and is not captured yet)
PT_MY_NODE_ID="xxxx-xxx-xxx-xxx-xxxx"
# THE NAME OF THE SCRIPT YOU USE TO MANAGE YOUR POOL
PLATFORM="sendmytip.sh"
# The location of your log file.
# EXAMPLE CONFIGURATION ENTRIES IN YOUR config.json FILE FOR YOUR NODE:
# "defaultScribes": [
#    [
#      "FileSK",
#      "/opt/cardano/cnode/logs/node0.json"
#    ]
# ],
#
# "setupScribes": [
#    {
#     "scKind": "FileSK",
#     "scName": "/opt/cardano/cnode/logs/node0.json",
#     "scFormat": "ScJson",
#     "scRotation": null
#    }
# ]

# MODIFY THIS LINE TO POINT TO YOUR LOG FILE AS SPECIFIED IN YOUR CONFIG FILE
LOG_FILE="/opt/cardano/cnode/logs/node0.json"

[[ -z "${CARDANO_NODE_SOCKET_PATH}" ]] && export CARDANO_NODE_SOCKET_SOCKET="/opt/cardano/cnode/sockets/node0.socket"

shopt -s expand_aliases

alias cli="$(which cardano-cli)"

tail -Fn0 $LOG_FILE | \
while read line ; do
    echo "$line" | grep "TraceAddBlockEvent.AddedToCurrentChain" 2>/dev/null
    if [ $? = 0 ]
    then
        # current cardano-node json output has a bug in it with an extra quote it seems so jq doesn't work by default.  ("newtip":"\"8afc7f@6131589")
        # Fix the line so that it's proper JSON
        LINE=$(echo "$line" | sed "s/\"newtip\":\"\"/\"newtip\":\"/g")
        nodeVersion=$(echo ${LINE} | jq -r .env)
        AT=$(echo ${LINE} | jq -r .at)

        nodeTip=$(cli query tip --mainnet)
        lastSlot=$(echo ${nodeTip} | jq -r .slot)
        lastBlockHash=$(echo ${nodeTip} | jq -r .hash)
        lastBlockHeight=$(echo ${nodeTip} | jq -r .block)

        JSON="$(jq -n --compact-output --arg NODE_ID "$PT_MY_NODE_ID" --arg MY_API_KEY "$PT_MY_API_KEY" --arg MY_POOL_ID "$PT_MY_POOL_ID" --arg VERSION "$nodeVersion" --arg AT "$AT" --arg BLOCKNO "$lastBlockHeight" --arg SLOTNO "$lastSlot" --arg PLATFORM "$PLATFORM" --arg BLOCKHASH "$lastBlockHash" '{apiKey: $MY_API_KEY, poolId: $MY_POOL_ID, data: {nodeId: $NODE_ID, version: $VERSION, at: $AT, blockNo: $BLOCKNO, slotNo: $SLOTNO, blockHash: $BLOCKHASH, platform: $PLATFORM}}')"
        echo "Packet Sent: $JSON"

        if [ "${lastBlockHeight}" != "" ]; then
        RESPONSE="$(curl -s -H "Accept: application/json" -H "Content-Type:application/json" -X POST --data "$JSON" "https://api.pooltool.io/v0/sendstats")"
        echo $RESPONSE
        fi
    fi
done
