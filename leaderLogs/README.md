# Cardano Leader Logs (Python Implementation)

These utility scripts allow a Stake Pool Operator to check the slot leadership schedule
for their stake pool. The logic contained herein is thanks to the hard work of Andrew
Westberg [@amw7] (developer of JorManager and operator of BCSH family of stake pools).

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

```
