import json
import argparse
import os.path
from os import path

parser = argparse.ArgumentParser(description="Calculate the sigma value of the specified pool. If you do not provide the path to a ledger file via the --ledger option then the script will look for a ledger.json file in the current directory")
parser.add_argument('--pool-id', dest='id', help='the pool ID', required=True)
parser.add_argument('--ledger', dest='ledger', default='ledger.json', help='the path to a current ledger-state JSON file')
parser.add_argument('--next', action='store_true', help='if specified will provide sigma for the next epoch instead of the current epoch')
parser.add_argument('--porcelain', action='store_true', help='if specified will print JSON')

args = parser.parse_args()

poolId = args.id
ledger = args.ledger

if not path.exists(ledger):
    txt1 = "We tried but could not locate your ledger-state JSON file!"
    txt1 += "Use: \033[1;34mcardano-cli shelley query ledger-state --mainnet --out-file ledger.json\033[0m to export one!"
    if not args.porcelain:
        print(txt1)
    else:
        print('{ "error": "' + txt1 + '"}')        
    exit(1)

with open(ledger) as f:
    ledger = json.load(f)
    
stakequery="_pstakeSet"
stakeinfo="active"
if args.next:
  stakequery="_pstakeMark"
  stakeinfo="next"

blockstakedelegators={}
blockstake={}
bs={}

if not args.porcelain:
    print("building "+stakeinfo+" stake")

if 'nesEs' in ledger:
  ledger_set=ledger['nesEs']['esSnapshots'][stakequery]
else:
  ledger_set=ledger['esSnapshots'][stakequery]

for item2 in ledger_set['_delegations']:
    keyhashobj = []
    for itemsmall in item2:
        if 'key hash' in itemsmall:
            keyhashobj.append(itemsmall['key hash'])
        else:
            poolid = itemsmall
    if poolid not in blockstakedelegators:
        blockstakedelegators[poolid]=keyhashobj
    else:
        blockstakedelegators[poolid]=blockstakedelegators[poolid]+keyhashobj

for item2 in ledger_set['_stake']:
    delegatorid = None
    for itemsmall in item2:
        if isinstance(itemsmall,int):
            snapstake = itemsmall
        else:
            delegatorid=itemsmall['key hash']
    if delegatorid != None:
        if delegatorid not in blockstake:
            blockstake[delegatorid]=snapstake
        else:
            blockstake[delegatorid]=blockstake[delegatorid]+snapstake

total_bs=0
for poolid in blockstakedelegators:
    bs[poolid]=0
    for d in blockstakedelegators[poolid]:
        if d in blockstake:
            bs[poolid]=bs[poolid]+blockstake[d]
            total_bs=total_bs + blockstake[d]

sigma = float(bs[poolId]/total_bs)

if not args.porcelain:
    print("Sigma:",sigma)
else:
    result = dict()
    result["sigma"] = "%.10f" % float(sigma)
    result["stakeinfo"] = stakeinfo
    result["stakequery"] = stakequery
    print(json.dumps(result))
