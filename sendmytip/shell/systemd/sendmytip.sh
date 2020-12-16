#!/usr/bin/env bash

# CHANGE THESE TO SUITE YOUR POOL => GET THEM FROM https://pooltool.io/profile
# YOUR POOL ID AS ON THE EXPLORER
PT_MY_POOL_ID="xxxxxxxxxxxxxxxxxxxxxxx"
# GET THIS FROM YOUR ACCOUNT PROFILE PAGE ON POOLTOOL WEBSITE
PT_MY_API_KEY="xxxx-xx-xx-xx-xxxx"
# YOUR NODE ID (OPTIONAL, THIS IS RESERVED FOR FUTURE USE AND IS NOT CAPTURED YET)
PT_MY_NODE_ID="xxxx-xxx-xxx-xxx-xxxx"

# MODIFY THIS LINE TO POINT TO YOUR LOG FILE AS SPECIFIED IN RSYSLOG
LOG_FILE="/var/log/cardano-node.log"

# MODIFY THIS LINE TO POINT TO YOUR ACTUAL SOCKET PATH
export CARDANO_NODE_SOCKET_PATH="/home/cardano-node/socket/node.socket"

#########################################################################################################################
## ### ##### DO NOT EDIT PAST THIS POINT ##### DO NOT EDIT PAST THIS POINT ##### DO NOT EDIT PAST THIS POINT ##### ### ##
#########################################################################################################################

# THE NAME OF THE SCRIPT YOU USE TO MANAGE YOUR POOL
PLATFORM="sendmytip.sh"

# CARDANO BINARIES
CNODE=$(command -v cardano-node)
CCLI=$(command -v cardano-cli)

while IFS= read -r line; do
    if echo "$line" | grep "Chain extended, new tip" 2>/dev/null; then
        # NODE VERSION
        nodeVNumber=$("${CNODE}" --version | awk '/cardano-node/ {print $2}')
        nodeGitRev=$("${CNODE}" --version | awk '/rev/ {print $3}' | cut -c1-5)
        nodeVersion="$nodeVNumber":"$nodeGitRev"

        # TIMESTAMP CONVERSION TO ## 2020-10-26T14:34:20.75Z"
        # THE TIME ZONE MUST BE UTC AND THE TIME FORMAT YYYY-MM-DD HH-MM-SS UTC
        at=$(echo "$line" | grep -o "[0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}.*UTC" | sed 's/\ /T/' | sed 's/\ UTC/Z/')

        # NODE TIP
        nodeTip=$("${CCLI}" query tip --mainnet)
        lastSlot=$(echo "$nodeTip" | jq -r .slotNo)
        lastBlockHash=$(echo "$nodeTip" | jq -r .headerHash)
        lastBlockHeight=$(echo "$nodeTip" | jq -r .blockNo)

        # THE DATA TO SEND TO POOLTOOL
        JSON="$(jq -n --compact-output --arg NODE_ID "$PT_MY_NODE_ID" --arg MY_API_KEY "$PT_MY_API_KEY" --arg MY_POOL_ID "$PT_MY_POOL_ID" --arg VERSION "$nodeVersion" --arg AT "$at" --arg BLOCKNO "$lastBlockHeight" --arg SLOTNO "$lastSlot" --arg PLATFORM "$PLATFORM" --arg BLOCKHASH "$lastBlockHash" '{apiKey: $MY_API_KEY, poolId: $MY_POOL_ID, data: {nodeId: $NODE_ID, version: $VERSION, at: $AT, blockNo: $BLOCKNO, slotNo: $SLOTNO, blockHash: $BLOCKHASH, platform: $PLATFORM}}')"
        echo "Packet Sent: $JSON"

        # ONLY IF THE BLOCK HEIGHT IS NOT EMPTY
        if [ "$lastBlockHeight" != "" ]; then
            RESPONSE="$(curl -s -H "Accept: application/json" -H "Content-Type:application/json" -X POST --data "$JSON" "https://api.pooltool.io/v0/sendstats")"
            echo "$RESPONSE"
        fi
    fi
done < <(tail -Fn0 "$LOG_FILE")

echo "something went wrong... this is out of the while looop..."

exit 127
