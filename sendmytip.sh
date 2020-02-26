#!/bin/bash

## CHANGE THESE TO SUITE YOUR POOL
# your pool id as on the explorer
MY_POOL_ID="52b33axxxxxxxxxxxx"
# get this from your account profile page on pooltool website
MY_USER_ID="xxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxx"
# we only actually look at the first 7 characters
THIS_GENESIS="8e4d2a343f3dcf93"
# THE NAME OF THE SCRIPT YOU USE TO MANAGE YOUR POOL
PLATFORM="sendmytip.sh"
## node count should start from 1 (e.g: if you have a single node use 1, if you have 3 nodes; use 3...)
ITN1_NODES_COUNT="1"
## your rest private port (start from xxx1 to match node count)
## if you have a single node, this would be the REST api port for it
ITN1_REST_API_PORT="3101"

# THIS SHOULD TAKE CARE OF JCLI PATH (ASSUMES /usr/local/bin or same directory)
JCLI="$(command -v jcli)"
[ -z "${JCLI}" ] && JCLI="/usr/local/bin/jcli"
[ -z "${JCLI}" ] && [ -f ./jcli ] && JCLI="./jcli"

##### DON'T CHANGE ANYTHING BEYOND THIS LINE #####
tmpFile=$(mktemp)

## ITERATIONS AND ARRAY START FROM 1 TO MATCH NODE COUNT....
## choose the node to query for variables depending on height
for ((i = 1; i <= "$ITN1_NODES_COUNT"; i++)); do
    ## temporary node variable to cycle through
    NODE_RESTAPI_PORT="${ITN1_REST_API_PORT%?}$i"
    NODE_RESTAPI_URL="http://127.0.0.1:$NODE_RESTAPI_PORT/api"
    ## query each node
    $JCLI rest v0 node stats get -h "$NODE_RESTAPI_URL" --output-format json >"$tmpFile"
    ## get the height only, highest to be the selected node for the curl variables later
    lastBlockHeightArray[++a]=$(jq -r .lastBlockHeight "$tmpFile")
done

## ITERATIONS AND ARRAY START FROM 1 TO MATCH NODE COUNT....
## set some default values to later select node...
NODE_HEIGHT=${lastBlockHeightArray[1]}
NODE_INDEX=1

## ...by iterating over the array we set above
for ((n = 1; n <= ${#lastBlockHeightArray[@]}; ++n)); do
    ## let's avoid 'null' values from botstrapping/not available nodes
    if [[ "${lastBlockHeightArray[n]}" =~ ^[0-9] ]]; then
        ## index with the highest lastBlockHeight wins...
        ## ...and it's set as index value to use in the actual REST query later
        (("${lastBlockHeightArray[n]}" > "$NODE_HEIGHT")) && NODE_HEIGHT="${lastBlockHeightArray[n]}" && NODE_INDEX="$n"
    fi
done

SELECTED_RESTAPI_PORT="${ITN1_REST_API_PORT%?}$NODE_INDEX"
SELECTED_RESTAPI_URL="http://127.0.0.1:$SELECTED_RESTAPI_PORT/api"

## query node and dump to file
$JCLI rest v0 node stats get -h "$SELECTED_RESTAPI_URL" --output-format json >"$tmpFile"

## run the commands from the chosen node only, and use these for curl
jormVersion="$(jq -r .version "$tmpFile")"
lastBlockHeight=$(jq -r .lastBlockHeight "$tmpFile")
lastBlockHash=$(jq -r .lastBlockHash "$tmpFile")
lastBlock=$($JCLI rest v0 block "${lastBlockHash}" get -h "$SELECTED_RESTAPI_URL")
lastPoolID=${lastBlock:168:64}
lastParent=${lastBlock:104:64}
lastSlot=$((0x${lastBlock:24:8}))
lastEpoch=$((0x${lastBlock:16:8}))

##... and finally send to pooltool :)
if [ "$lastBlockHeight" != "" ]; then
    curl -s -G --data-urlencode "platform=${PLATFORM}" --data-urlencode "jormver=${jormVersion}" "https://api.pooltool.io/v0/sharemytip?poolid=${MY_POOL_ID}&userid=${MY_USER_ID}&genesispref=${THIS_GENESIS}&mytip=${lastBlockHeight}&lasthash=${lastBlockHash}&lastpool=${lastPoolID}&lastparent=${lastParent}&lastslot=${lastSlot}&lastepoch=${lastEpoch}"
fi

## we protecc, we clean up
rm "$tmpFile"
