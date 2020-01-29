#!/bin/bash
shopt -s expand_aliases
RESTAPI_PORT=5001
# MY_POOL_ID="52b33axxxxxxxxxxxx"
# MY_USER_ID="xxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxx" # on pooltool website get this from your account profile page
THIS_GENESIS="8e4d2a343f3dcf93"   # We only actually look at the first 7 characters

if [ ! $JORMUNGANDR_RESTAPI_URL ]; then export JORMUNGANDR_RESTAPI_URL=http://127.0.0.1:${RESTAPI_PORT}/api; fi
alias cli="$(which jcli) rest v0"
nodestats=$(cli node stats get --output-format json > stats.json);
platformName="sendmytip.sh"
lastBlockHeight=$(cat stats.json | jq -r .lastBlockHeight)
jormVersion=$(cat stats.json | jq -r .version)

lastBlockHash=$(cat stats.json | jq -r .lastBlockHash)
lastBlock=$(cli block ${lastBlockHash} get)
lastPoolID=${lastBlock:168:64}
lastParent=${lastBlock:104:64}
lastSlot=$((0x${lastBlock:24:8}))
lastEpoch=$((0x${lastBlock:16:8}))

if [ "$lastBlockHeight" != "" ]; then
curl -G --data-urlencode "platform=${platformName}" --data-urlencode "jormver=${jormVersion}" "https://api.pooltool.io/v0/sharemytip?poolid=${MY_POOL_ID}&userid=${MY_USER_ID}&genesispref=${THIS_GENESIS}&mytip=${lastBlockHeight}&lasthash=${lastBlockHash}&lastpool=${lastPoolID}&lastparent=${lastParent}&lastslot=${lastSlot}&lastepoch=${lastEpoch}"
fi

