#!/usr/bin/env bash

## CHANGE THESE TO SUITE YOUR POOL
# your pool id as on the explorer
MY_POOL_ID="52b33axxxxxxxxxxxx"
# get this from your account profile page on pooltool website
MY_USER_ID="xxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxx"
# we only actually look at the first 7 characters
THIS_GENESIS="8e4d2a343f3dcf93"
# THE NAME OF THE SCRIPT YOU USE TO MANAGE YOUR POOL
PLATFORM="itn-sendmytip.sh"
## node count should start from 1 (e.g: if you have a single node use 1, if you have 3 nodes; use 3)
## EXAMPLE 1 nodes: ITN1_NODES_COUNT="1"
## EXAMPLE 2 nodes: ITN1_NODES_COUNT="2"
## EXAMPLE 3 nodes: ITN1_NODES_COUNT="3"
ITN1_NODES_COUNT="1"
## YOUR REST PRIVATE PORTS ARRAY (STATE ALL OF THE PORTS IN INCREMENTAL/SEQUENTIAL ORDER)
## EXAMPLE 1 ports: declare -a ITN1_REST_API_PORT=("3001")
## EXAMPLE 2 ports: declare -a ITN1_REST_API_PORT=("3001" "3002")
## EXAMPLE 3 ports: declare -a ITN1_REST_API_PORT=("3001" "3002" "3003")
declare -a ITN1_REST_API_PORT=("3001")

#######################################################################################################################################

### DO NOT EDIT PAST THIS POINT ### ## DO NOT CHANGE ### DO NOT EDIT PAST THIS POINT ### ## DO NOT CHANGE #### ## #

#######################################################################################################################################

# THIS SHOULD TAKE CARE OF JCLI PATH (ASSUMES $PATH ; /usr/local/bin ; or same directory)
JCLI="$(command -v jcli)"
[ -z "$JCLI" ] && JCLI="/usr/local/bin/jcli"
[ -z "$JCLI" ] && [ -f ./jcli ] && JCLI="./jcli"

## temporary file
tmpFile=$(mktemp)

## needed arrays declarations
declare -a lastBlockHeightArray
declare -a nodeAvailableRestArray

## choose the node to query for variables depending on height
for ((i = 0; i < "$ITN1_NODES_COUNT"; i++)); do
    ## temporary node variable to cycle through
    NODE_REST_API_PORT="${ITN1_REST_API_PORT[i]}"
    NODE_REST_API_URL="http://127.0.0.1:$NODE_REST_API_PORT/api"

    ## query each node for status
    nodeStatus=$($JCLI rest v0 node stats get -h "$NODE_REST_API_URL" | awk '/state/ {print $2}')

    ## if the node is running...
    if [ "$nodeStatus" == "Running" ]; then
        ## query each node
        $JCLI rest v0 node stats get -h "$NODE_REST_API_URL" --output-format json >"$tmpFile"
        ## get the height only, highest to be node for the curl variables later
        lastBlockHeightArray[++a]=$(jq -r .lastBlockHeight "$tmpFile")
        ## only get the ports for the available nodes (state running)
        nodeAvailableRestArray[++v]=$NODE_REST_API_PORT
    elif [ "$nodeStatus" == "Bootstrapping" ]; then
        echo "The node is Bootstrapping, exiting the routine"
        continue
    else
        echo "ERROR: THE NODE IS NOT RUNNING, EXITING THE ROUTINE"
        continue
    fi
done

## set some default values to later select node...
NODE_PORT=${nodeAvailableRestArray[1]} ## 1 for element value at length position 1
NODE_HEIGHT=${lastBlockHeightArray[1]} ## 1 for element value at length position 1

## ...by iterating over the LENGTH of the array we set above (+1 needed to match length index)
lastBlockHeightLength=${#lastBlockHeightArray[@]}
for ((n = 1; n < lastBlockHeightLength + 1; n++)); do
    ## let's make sure we have an integer value
    if [[ "$NODE_HEIGHT" =~ ^[0-9] ]]; then
        ## index with the highest lastBlockHeight wins...
        ## ...and it's set as index value to use in the actual REST query later
        if [[ "${lastBlockHeightArray[$n]}" -gt "$NODE_HEIGHT" ]]; then
            NODE_HEIGHT="${lastBlockHeightArray[$n]}"
            NODE_PORT="${nodeAvailableRestArray[$n]}"
        fi
    fi
done

SELECTED_REST_API_PORT="$NODE_PORT"
SELECTED_REST_API_URL="http://127.0.0.1:$SELECTED_REST_API_PORT/api"

## query node and dump to file
$JCLI rest v0 node stats get -h "$SELECTED_REST_API_URL" --output-format json >"$tmpFile"

## run the commands from the chosen node only, and use these for curl
jormVersion="$(jq -r .version "$tmpFile")"
lastBlockHeight=$(jq -r .lastBlockHeight "$tmpFile")
lastBlockHash=$(jq -r .lastBlockHash "$tmpFile")
lastBlock=$($JCLI rest v0 block "${lastBlockHash}" get -h "$SELECTED_REST_API_URL")
lastPoolID=${lastBlock:168:64}
lastParent=${lastBlock:104:64}
lastSlot=$((0x${lastBlock:24:8}))
lastEpoch=$((0x${lastBlock:16:8}))

## send to pooltool :)
if [ "$lastBlockHeight" != "" ]; then
    curl -s -G --data-urlencode "platform=${PLATFORM}" --data-urlencode "jormver=${jormVersion}" "https://api.pooltool.io/v0/sharemytip?poolid=${MY_POOL_ID}&userid=${MY_USER_ID}&genesispref=${THIS_GENESIS}&mytip=${lastBlockHeight}&lasthash=${lastBlockHash}&lastpool=${lastPoolID}&lastparent=${lastParent}&lastslot=${lastSlot}&lastepoch=${lastEpoch}"
fi

## we protecc, we clean up
rm "$tmpFile"

unset ITN1_REST_API_PORT
unset lastBlockHeightArray
unset nodeAvailableRestArray
