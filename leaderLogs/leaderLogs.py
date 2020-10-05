# leader logs proof of concept - all credit goes to @andrewwestberg of BCSH for the algo extraction from cardano-node
# Current issue:  I suspect a precision and/or big integer math issue resulting in far more slots than expected in the isSlotLeader function.
# For example
# certNat = 91829741963481555176272775124811557118579219617852200004823836275117288794553889298345298218949459449673836160366
# certNatMax = 1.3407807929942597e+154
# denominator (certNatMax - certNat) = 1.3407807929942597e+154
# q (certNatMax / denominator) = 1.0

import json
import math
import binascii
import sys
import hashlib
import psycopg2
import psycopg2.extras
from psycopg2.extras import Json
from nacl._sodium import ffi, lib
from ctypes import *


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
epoch=221
poolId="95c4956f7a137f7fe9c72f2e831e6038744b6307d00143b2447e6443"
sigma = 0.010052348379780869 # note function to pull data from ledger state is below.  its just faster to hard code it for testing
# grab this from  your pool key set
poolVrfSkey = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxa51b5e76dfd68dd77ae"
eta0 = "5ee77854fe91cc243b8d5589de3192e795f162097dba7501f8d1b0d5d7546bd5" # value is for epoch 211

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

    byt_combined = slot.to_bytes(8,byteorder='big') + binascii.unhexlify(eta0)

    h = hashlib.blake2b(digest_size=32)
    h.update(slot.to_bytes(8,byteorder='big') + binascii.unhexlify(eta0))
    slotToSeedBytes = h.digest()

    seed = [x ^ slotToSeedBytes[i] for i,x in enumerate(seedLbytes)]

    return bytearray(seed)



def vrfEvalCertified(seed, tpraosCanBeLeaderSignKeyVRF):
    if isinstance(seed, bytes) and isinstance(tpraosCanBeLeaderSignKeyVRF, bytes):
        proof = create_string_buffer(libsodium.crypto_vrf_ietfdraft03_proofbytes())

        libsodium.crypto_vrf_prove(proof, tpraosCanBeLeaderSignKeyVRF,seed, len(seed))

        proofHash = create_string_buffer(libsodium.crypto_vrf_outputbytes())

        libsodium.crypto_vrf_proof_to_hash(proofHash,proof)

        return proofHash.value.hex()

    else:
        print("error.  Feed me bytes")


# Determine if our pool is a slot leader for this given slot
# @param slot The slot to check
# @param f The activeSlotsCoeff value from protocol params
# @param sigma The controlled stake proportion for the pool
# @param eta0 The epoch nonce value
# @param poolVrfSkey The vrf signing key for the pool

def isSlotLeader(slot,activeSlotCoeff,sigma,eta0,poolVrfSkey):
    seed = mkSeed(slot, eta0) # returns binary already

    seedb = binascii.unhexlify(seed.hex())
    tpraosCanBeLeaderSignKeyVRFb = binascii.unhexlify(poolVrfSkey)

    cert=vrfEvalCertified(seedb,tpraosCanBeLeaderSignKeyVRFb)

    #add 00 to make sure we don't get a negative number by accident

    certNat  = int("0x00" + cert, 0)
    #print("certNat = " + str(certNat))

    certNatMax = math.pow(2,512)
    #print("certNatMax = " + str(certNatMax))

    denominator = certNatMax - certNat
    #print("denominator (certNatMax - certNat) = " + str(denominator))

    q = certNatMax / denominator
    #print("q (certNatMax / denominator) = "  + str(q))

    c = math.log(1.0 - activeSlotCoeff)

    sigmaOfF = math.exp(-sigma * c)
    #print("vals",q,sigmaOfF)
    return q <= sigmaOfF


slotcount=0
for slot in range(firstSlotOfEpoch,epochLength+firstSlotOfEpoch):
    if isOverlaySlot(firstSlotOfEpoch,slot,decentralizationParam):
        continue

    slotLeader = isSlotLeader(slot,activeSlotCoeff,sigma,eta0,poolVrfSkey)

    if slotLeader:
        slotcount+=1
        print("Leader for " +str(slot) + ", Cumulative epoch blocks: " + str(slotcount))




