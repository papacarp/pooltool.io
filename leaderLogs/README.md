# Cardano Leader Logs (Python Implementation)

These utility scripts allow a Stake Pool Operator to check the slot leadership schedule
for their stake pool. The logic contained herein is thanks to the hard work of [Andrew
Westberg](https://github.com/amw7) (developer of JorManager and operator of BCSH family
of stake pools).

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

### Usage

```shell
user@foo:~$ python3 getSigma.py --pool-id 123456789abcdefxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx --ledger /path/to/ledger.json
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
user@foo:~$ python3 pip -m install pytz
```
### Arguments

#### --vrf-skey PATH

***Required***. Provide the path to the complete *pool.vrf.skey* file. This will be
parsed automatically by the script extract the necessary portion of the CBORHex key.

#### --sigma FLOAT

***Required***. Provide the 18-decimal precise sigma value from the pool. You can
use the value returned by *getSigma.py* above to acquire this value.

**Note:** By the default the script will attempt to fetch epoch details from
[https://epoch-api.crypto2099.io](https://epoch-api.crypto2099.io:2096/epoch). If
the api is unavailable or you would like to test against another epoch or test 
network you can use the arguments below to override these settings.
