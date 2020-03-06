#!/bin/bash

shopt -s expand_aliases
#Change below variables to determine what you upload to pooltool
VERIFY_SLOTS_GPG=true
VERIFY_SLOTS_HASH=false

#Uncomment if you want to use a remote REST API
#JORMUNGANDR_RESTAPI_URL="<HOST>"
RESTAPI_PORT=5001
#MY_POOL_ID="<POOLID>"
#MY_USER_ID="<USERID>" # on pooltool website get this from your account profile page

THIS_GENESIS="8e4d2a343f3dcf93"
KEY_LOCATION="/tmp/keystorage"

#Testing if variables are set
if  [ -z "$MY_POOL_ID"] || [ -z "$MY_USER_ID" ] || [ -z "$THIS_GENESIS" ] || [ -z "$KEY_LOCATION" ]
then
	echo "One or more variables not set."
	echo "MY_POOL_ID = $MY_POOL_ID"
	echo "MY_USER_ID = $MY_USER_ID"
	echo "THIS_GENESIS = $THIS_GENESIS"
	echo "KEY_LOCATION = $KEY_LOCATION"
	exit 1
elif [ ! -d "$KEY_LOCATION" ]
then
	echo "Key directory doesn't exist. Making the directory ..."
	mkdir -p $KEY_LOCATION
	if [ $? -ne 0 ]
	then
		echo "Unable to create Key directory. Please create manually or use a different path."
		exit 1
	fi
else
	echo "Everything ok. Starting ..."
fi

if [ ! $JORMUNGANDR_RESTAPI_URL ]; then export JORMUNGANDR_RESTAPI_URL=http://127.0.0.1:${RESTAPI_PORT}/api/v0; fi

#Using CURL instead of JCLI for better portability

#Getting EPOCH 
NODESTATS=`curl -s  ${JORMUNGANDR_RESTAPI_URL}/node/stats`
CURRENT_EPOCH=`echo $NODESTATS | jq -r .lastBlockDate | cut -d. -f1`
PREVIOUS_EPOCH=$((${CURRENT_EPOCH} - 1))

#We need to exit with an error if nodestats is empty (IE, node, down or misconfiguration)

if [ -z "$CURRENT_EPOCH" ]
then
	echo "Nodestats not avaliable.  Node is down or rest API misconfigured? Check REST Port and Path."
	exit 1
fi

#Retrieving Leader slots assigned in current epoch
RESPONSE=`curl -s ${JORMUNGANDR_RESTAPI_URL}/leaders/logs`
CURRENT_SLOTS=`echo $RESPONSE | jq -c '[ .[] | select(.scheduled_at_date | startswith('\"$CURRENT_EPOCH\"')) ]'`
ASSIGNED_SLOTS=`echo $CURRENT_SLOTS | jq '. | length'`

if [ "$VERIFY_SLOTS_GPG" = true ] ; then
	#Generating symmetric key for current epoch and retrieving previous epoch key
	if [ -f "${KEY_LOCATION}/passphrase_${PREVIOUS_EPOCH}" ]
	then
		PREVIOUS_EPOCH_KEY=`cat ${KEY_LOCATION}/passphrase_${PREVIOUS_EPOCH}`
	else
		PREVIOUS_EPOCH_KEY=''
	fi

	if [ -f "${KEY_LOCATION}/passphrase_${CURRENT_EPOCH}" ]
	then
		CURRENT_EPOCH_KEY=`cat ${KEY_LOCATION}/passphrase_${CURRENT_EPOCH}`
	else
		CURRENT_EPOCH_KEY=`openssl rand -base64 32 | tee ${KEY_LOCATION}/passphrase_${CURRENT_EPOCH}`
	fi

	#Encrypting current slots for sending to pooltool
	CURRENT_SLOTS_ENCRYPTED=`echo $CURRENT_SLOTS | gpg --symmetric --armor --batch --passphrase ${CURRENT_EPOCH_KEY}`

	#Creating JSON for sending to pooltool

	JSON="$( jq -n --compact-output --arg CURRENTEPOCH "$CURRENT_EPOCH" --arg POOLID "$MY_POOL_ID" --arg USERID "$MY_USER_ID" --arg GENESISPREF "$THIS_GENESIS" --arg ASSIGNED "$ASSIGNED_SLOTS" --arg KEY "$PREVIOUS_EPOCH_KEY" --arg SLOTS "$CURRENT_SLOTS_ENCRYPTED" '{currentepoch: $CURRENTEPOCH, poolid: $POOLID, genesispref: $GENESISPREF, userid: $USERID, assigned_slots: $ASSIGNED, previous_epoch_key: $KEY, encrypted_slots: $SLOTS}')"

	echo "Packet Sent:"
	echo $JSON

	RESPONSE=`curl -s -H "Accept: application/json" -H "Content-Type:application/json" -X POST --data "$JSON" "https://api.pooltool.io/v0/sendlogs"`

	echo "Response Received:"
	echo "$RESPONSE"
	exit 1
fi

if [ "$VERIFY_SLOTS_HASH" = true ] ; then
	#Pushing the current slots to file and getting the slots from the last epoch.
	if [ -f "${KEY_LOCATION}/leader_slots_${PREVIOUS_EPOCH}" ]
	then
                LAST_EPOCH_SLOTS=`cat ${KEY_LOCATION}/leader_slots_${PREVIOUS_EPOCH}`
        else
                LAST_EPOCH_SLOTS=''
        fi

	if [ ! -f "${KEY_LOCATION}/leader_slots_${CURRENT_EPOCH}" ]
	then
		echo -n $CURRENT_SLOTS | tee ${KEY_LOCATION}/leader_slots_${CURRENT_EPOCH}
	fi

	#Hash verification version goes here.  I know its verbose, but its so much easier for people to decode and customize if we keep them all separate
	CURRENT_EPOCH_HASH=`echo -n $CURRENT_SLOTS | sha256sum | cut -d" " -f1 | tee ${KEY_LOCATION}/hash_${CURRENT_EPOCH}`

        JSON="$( jq -n --compact-output --arg CURRENTEPOCH "$CURRENT_EPOCH" --arg POOLID "$MY_POOL_ID" --arg USERID "$MY_USER_ID" --arg GENESISPREF "$THIS_GENESIS" --arg ASSIGNED "$ASSIGNED_SLOTS" --arg HASH "$CURRENT_EPOCH_HASH" --arg SLOTS "$LAST_EPOCH_SLOTS" '{currentepoch: $CURRENTEPOCH, poolid: $POOLID, genesispref: $GENESISPREF, userid: $USERID, assigned_slots: $ASSIGNED, this_epoch_hash: $HASH, last_epoch_slots: $SLOTS}')"

        echo "Packet Sent:"
        echo $JSON

        RESPONSE=`curl -s -H "Accept: application/json" -H "Content-Type:application/json" -X POST --data "$JSON" "https://api.pooltool.io/v0/sendlogs"`

        echo "Response Received:"
        echo "$RESPONSE"
        exit 1

fi

# if we get to here then neither verification method is being used.  Just send current slots
JSON="$( jq -n --compact-output --arg CURRENTEPOCH "$CURRENT_EPOCH" --arg POOLID "$MY_POOL_ID" --arg USERID "$MY_USER_ID" --arg GENESISPREF "$THIS_GENESIS" --arg ASSIGNED "$ASSIGNED_SLOTS"  '{currentepoch: $CURRENTEPOCH, poolid: $POOLID,  genesispref: $GENESISPREF, userid: $USERID, assigned_slots: $ASSIGNED}')"

echo "Packet Sent:"
echo $JSON

RESPONSE=`curl -s -H "Accept: application/json" -H "Content-Type:application/json" -X POST --data "$JSON" "https://api.pooltool.io/v0/sendlogs"`

echo "Response Received:"
echo "$RESPONSE"
