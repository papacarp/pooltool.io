#!/bin/bash
shopt -s expand_aliases
RESTAPI_PORT=5001
MY_POOL_ID="52b33axxxxxxxxxxxx"
MY_USER_ID="xxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxx" # on pooltool website get this from your account profile page
THIS_GENESIS="8e4d2a343f3dcf93"   # We only actually look at the first 7 characters

if [ ! $JORMUNGANDR_RESTAPI_URL ]; then export JORMUNGANDR_RESTAPI_URL=http://127.0.0.1:${RESTAPI_PORT}/api; fi
alias cli="$(which jcli) rest v0"

lastBlockHeight=$(cli node stats get --output-format json | jq -r .lastBlockHeight)
echo ${lastBlockHeight}
if [ "$lastBlockHeight" != "" ]; then
curl -G "https://api.pooltool.io/v0/sharemytip?poolid=${MY_POOL_ID}&userid=${MY_USER_ID}&genesispref=${THIS_GENESIS}&mytip=${lastBlockHeight}"
fi
