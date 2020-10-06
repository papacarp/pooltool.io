# leader logs proof of concept - all credit goes to @andrewwestberg of BCSH for the algo extraction from cardano-node

import math
import binascii
from datetime import datetime, timezone
import pytz
import hashlib
from ctypes import *

import json
import argparse

parser = argparse.ArgumentParser(description="Calculate the leadership log.")
parser.add_argument('--pool-id', dest='poolId', help='the pool ID', required=True)
parser.add_argument('--epoch', dest='epoch', help='the epoch number [e.g. 221]', type=int, required=True)
parser.add_argument('--epoch-nonce', dest='eta0', help='the epoch nonce to check', required=True)
parser.add_argument('--vrf-skey', dest='skey', help='provide the path to the pool.vrf.skey file', required=True)
parser.add_argument('--sigma', dest='sigma', type=float, help='the controlled stake sigma value of the pool', required=True)

args = parser.parse_args()

epoch = args.epoch
poolId = args.poolId
sigma = args.sigma
#poolVrfSkey = args.skey
eta0 = args.eta0

with open(args.skey) as f:
    skey = json.load(f)

poolVrfSkey = skey['cborHex'][4:]
#print(poolVrfSkey)

# Bindings are not avaliable so using ctypes to just force it in for now.
libsodium = cdll.LoadLibrary("/usr/local/lib/libsodium.so")
libsodium.sodium_init()

# Hard code these for now.
epochLength = 432000
activeSlotCoeff = 0.05
slotLength = 1
epoch211firstslot = 5788800
decentralizationParam = 0.62

# more hard coded values
local_tz = pytz.timezone('America/Los_angeles') # use your local timezone name here
#epoch=221
#poolId="95c4956f7a137f7fe9c72f2e831e6038744b6307d00143b2447e6443"
#sigma = 0.010052348379780869 # note function to pull data from ledger state is below.  its just faster to hard code it for testing
# grab this from  your pool key set.  Make sure you strip off the first 4 characters (the CBOR header) so your Skey is the exact same length as the example shown here
#poolVrfSkey = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxa51b5e76dfd68dd77ae"
#eta0 = "5ee77854fe91cc243b8d5589de3192e795f162097dba7501f8d1b0d5d7546bd5" # value is for epoch 221

firstSlotOfEpoch = 5788800 + (epoch - 211)*epochLength

def isOverlaySlot(firstSlotOfEpoch, currentSlot, decentralizationParam):
   diff_slot = float(currentSlot - firstSlotOfEpoch)
   if math.ceil( diff_slot * decentralizationParam ) < math.ceil( (diff_slot + 1) * decentralizationParam ):
      return True
   return False


def getSigma(poolId):
    blockstakedelegators={}
    blockstake={}
    bs={}
    print("building active stake")
    for item2 in ledger['esSnapshots']["_pstakeSet"]['_delegations']:
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

    for item2 in ledger['esSnapshots']["_pstakeSet"]['_stake']:
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


    return float(bs[poolId]/total_bs)

def mkSeed(slot,eta0):

    h = hashlib.blake2b(digest_size=32)
    h.update(bytearray([0,0,0,0,0,0,0,1])) #neutral nonce
    seedLbytes=h.digest()

    h = hashlib.blake2b(digest_size=32)
    h.update(slot.to_bytes(8,byteorder='big') + binascii.unhexlify(eta0))
    slotToSeedBytes = h.digest()

    seed = [x ^ slotToSeedBytes[i] for i,x in enumerate(seedLbytes)]

    return bytes(seed)



def vrfEvalCertified(seed, tpraosCanBeLeaderSignKeyVRF):
    if isinstance(seed, bytes) and isinstance(tpraosCanBeLeaderSignKeyVRF, bytes):
        proof = create_string_buffer(libsodium.crypto_vrf_ietfdraft03_proofbytes())

        libsodium.crypto_vrf_prove(proof, tpraosCanBeLeaderSignKeyVRF,seed, len(seed))

        proofHash = create_string_buffer(libsodium.crypto_vrf_outputbytes())

        libsodium.crypto_vrf_proof_to_hash(proofHash,proof)

        return proofHash.raw

    else:
        print("error.  Feed me bytes")
        exit()


# Determine if our pool is a slot leader for this given slot
# @param slot The slot to check
# @param activeSlotCoeff The activeSlotsCoeff value from protocol params
# @param sigma The controlled stake proportion for the pool
# @param eta0 The epoch nonce value
# @param poolVrfSkey The vrf signing key for the pool

def isSlotLeader(slot,activeSlotCoeff,sigma,eta0,poolVrfSkey):
    seed = mkSeed(slot, eta0)
    tpraosCanBeLeaderSignKeyVRFb = binascii.unhexlify(poolVrfSkey)
    cert=vrfEvalCertified(seed,tpraosCanBeLeaderSignKeyVRFb)
    certNat  = int.from_bytes(cert, byteorder="big", signed=False)
    certNatMax = math.pow(2,512)
    denominator = certNatMax - certNat
    q = certNatMax / denominator
    c = math.log(1.0 - activeSlotCoeff)
    sigmaOfF = math.exp(-sigma * c)
    return q <= sigmaOfF


slotcount=0
for slot in range(firstSlotOfEpoch,epochLength+firstSlotOfEpoch):
    if isOverlaySlot(firstSlotOfEpoch,slot,decentralizationParam):
        continue

    slotLeader = isSlotLeader(slot,activeSlotCoeff,sigma,eta0,poolVrfSkey)

    if slotLeader:
        slotcount+=1
        timestamp = datetime.fromtimestamp(slot + 1591566291, tz=local_tz)
        print(timestamp.strftime('%Y-%m-%d %H:%M:%S') + " ==> Leader for " +str(slot) + ", Cumulative epoch blocks: " + str(slotcount))

