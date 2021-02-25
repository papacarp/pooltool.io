***
### DEPRECATION NOTICE

These scripts will cease to be maintained immediately and may not be updated to
support changes to future **Cardano** node and cli instances. The scripts may be removed
from this repository all together on or after **2021-03-01**. No support will be
provided for these scripts by Andrew Westberg, PapaCarp, or Adam Dean. As an alternative,
we strongly recommend that you consider installing the fantastic 
[CNCLI](https://github.com/AndrewWestberg/cncli) utility library by 
[Andrew Westberg](https://github.com/AndrewWestberg). 

***

# Cardano Leader Logs (Python Implementation)

These utility scripts allow a Stake Pool Operator to check the slot leadership schedule
for their stake pool. The logic contained herein is thanks to the hard work of [Andrew
Westberg](https://github.com/AndrewWestberg) (developer of JorManager and operator of 
the BCSH family of stake pools).

## getSigma.py Details

This simple utility script uses a local copy of the Cardano ledger-state to calculate
the precise *sigma* (active controlled stake / total active stake) value for the given
pool-id.

### Arguments

#### --pool-id ID

***Required***. Pass the hex-format Pool ID for the stake pool you wish to find the
sigma value for.

#### --ledger PATH [Default: ./ledger.json]

***Optional***. By default the script will look for a local file named *ledger.json*
and attempt to parse the data there. Use this optional argument to specify the path
to the ledger-state JSON file you would like to use.

#### --next

***Optional***. Get the specified pool's sigma value for the following epoch (relative
to the specified ledger file).

### Usage

```shell
user@foo:~$ python3 getSigma.py --pool-id 123456789abcdefxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx --ledger /path/to/ledger.json --next
building active stake
Sigma: 0.001234567890123456
```

## leaderLogs.py Details

This script utilizes libsodium, the pool's VRF.skey, and the pool's active controlled
stake (*sigma*, see above) along with an epoch nonce to perform the same logic check
used by *cardano-node* to test for slot leadership.

This should (and has proven in practice) to provide an accurate slot leadership schedule
for the pool in question provided that all the passed parameters are accurate.

### Requirements

#### pytz - Python Timezone Extension

This script requires the *pytz* extension for Python. You can make sure this is installed
on your system by running the following command:

```shell
user@foo:~$ python3 -m pip install pytz
```
### Arguments

#### --vrf-skey PATH [/path/to/my/pool.vrf.skey]

***Required***. Provide the path to the complete *pool.vrf.skey* file. This will be
parsed automatically by the script extract the necessary portion of the CBORHex key.

#### --sigma FLOAT [0.001234567890123456]

***Required***. Provide the 18-decimal precise sigma value from the pool. You can
use the value returned by *getSigma.py* above to acquire this value.

#### --tz STRING [America/Los_Angeles]

***Optional***. Default: America/Los_Angeles. Provide the string timezone name of
your timezone to this argument to cast the slot leadership schedule times into your
local timezone. [List of Valid Timezones](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)

> **Note:** By the default the script will attempt to fetch epoch details from
> [https://epoch-api.crypto2099.io](https://epoch-api.crypto2099.io:2096/epoch). If
> the api is unavailable or you would like to test against another epoch or test 
> network you can use the arguments below to override these settings.
> 
> **DEPRECATION NOTICE:** The original epoch api from [Crypto2099](https://github.com/crypto2099)
> has been deprecated in favor of the new API service that works seamlessly with the CNCLI library.
> You can query the new API for the necessary arguments by visiting calling:
> https://api.crypto2099.io/v1/sigma/<pool_id>/<epoch_no>.
> Replace **<pool_id>** with your Pool ID and **<epoch_no>** with the epoch you would like
> parameter details for.

#### --epoch INTEGER [222]

***Optional***. Default: Latest current epoch from API. Provide the epoch number you would
like to check for the leadership schedule of.

#### --epoch-nonce STRING [171625aef5357dfccfeaeedecd5de49f71fb6e05953f2799d3ff84419dbef0ac]

***Optional***. Default: Current epoch nonce (eta0) from API. Provide the epoch nonce
for the epoch you are checking the leadership schedule of.

#### --d-param FLOAT [0.6]

***Optional***. Default: Current *d* parameter from API. Provide the current *d*
(decentralization) parameter of the network for the epoch you are checking the
leadership of.

#### -bft

***Optional***. Use this flag to instruct leaderLogs.py to show collisions with
the BFT Node overlay slots. The use of this flag can be viewed as either helpful
information or masochistic behavior depending on how you look at it. :)

#### --pool-id STRING [123456789abcdefxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx]

***Optional***. If you provide your Pool ID (Bech32 or Hex) as an argument; the script
will attempt to query the new Crypto2099 Epoch API for all necessary arguments to calculate
leadership logs.

### Usage

The following snippets show example script usage and expected output. Make sure
when using in your case that you change the command arguments to values that are
accurate for your pool.

#### Simple Usage
```shell
foo@bar:~$ python3 leaderLogs.py --vrf-skey /path/to/my/pool.vrf.skey --pool-id d9812f8d30b5db4b03e5b76cfd242db9cd2763da4671ed062be808a0
Checking leadership log for d9812f8d30b5db4b03e5b76cfd242db9cd2763da4671ed062be808a0
Epoch #222 [d Param: 0.6]
Pool Active Stake: 188554157002146 
Total Active Stake: 16371244779824020
Pool Sigma: 0.011517398923417283
Epoch Nonce: 171625aef5357dfccfeaeedecd5de49f71fb6e05953f2799d3ff84419dbef0ac
2020-10-07 17:50:35 ==> Leader for 10551944, Cumulative epoch blocks: 1
...
2020-10-12 08:05:33 ==> Leader for 10948842, Cumulative epoch blocks: 10
```

#### Basic Usage
```shell
foo@bar:~$ python3 leaderLogs.py --vrf-skey /path/to/my/pool.vrf.skey --sigma 0.001234567890123456
Checking leadership log for Epoch 222 [ d Param: 0.6 ]
2020-10-07 17:50:35 ==> Leader for 10551944, Cumulative epoch blocks: 1
...
2020-10-12 08:05:33 ==> Leader for 10948842, Cumulative epoch blocks: 10
```

#### Advanced Usage with All Arguments
```shell
foo@bar:~$ python3 leaderLogs.py \
> --vrf-skey /path/to/my/pool.vrf.skey \
> --sigma 0.001234567890123456 \
> --tz America/New_York \
> --epoch 222 \
> --epoch-nonce 171625aef5357dfccfeaeedecd5de49f71fb6e05953f2799d3ff84419dbef0ac \
> --d-param 0.6 \
Checking leadership log for Epoch 222 [ d Param: 0.6 ]
2020-10-07 20:50:35 ==> Leader for 10551944, Cumulative epoch blocks: 1
...
2020-10-12 11:05:33 ==> Leader for 10948842, Cumulative epoch blocks: 10
```
