#!/bin/env python3

# leader logs proof of concept - all credit goes to @andrewwestberg of BCSH, @AC8998 (Antonio) of CSP and @iiLap (Pal Dorogi) of UNDR for the algo extraction from cardano-node

import math
import binascii
from datetime import datetime, timezone
import pytz
import hashlib
from ctypes import *
import re

from urllib.request import urlopen
import json
import argparse

parser = argparse.ArgumentParser(description="Calculate the leadership log.")
parser.add_argument('--vrf-skey', dest='skey', help='provide the path to the pool.vrf.skey file or the raw skey (128 hex characters)', required=True)
parser.add_argument('--sigma', dest='sigma', type=float, help='the controlled stake sigma value of the pool [e.g. 0.0034052348379780869]')
parser.add_argument('--pool-id', dest='poolId', help='the Pool ID to fetch from the Epoch API')
parser.add_argument('--epoch', dest='epoch', type=int, help='the epoch number [e.g. 221]')
parser.add_argument('--epoch-nonce', dest='eta0', help='the epoch nonce to check')
parser.add_argument('--d-param', dest='d', type=float, help='the current decentralization parameter [e.g. 0.0 - 1.0]')
parser.add_argument('-bft', action='store_true', help='if specified will also calculate slots stolen by BFT due to d not being 0')
parser.add_argument('--tz', dest='tz', default='America/Los_Angeles', help='the local timezone name [Default: America/Los_Angeles]')

args = parser.parse_args()

epoch = args.epoch
poolId = args.poolId
local_tz = pytz.timezone(args.tz)

if poolId is not None:
    # Get parameters from API
    print("Checking leadership log for", poolId)
    if epoch is not None:
        print("\033[94m[INFO]:\033[0m Checking leadership for Epoch", epoch)
        url=("https://api.crypto2099.io/v1/sigma/"+str(poolId)+"/"+str(epoch))
    else:
        print("\033[94m[INFO]:\033[0m No epoch provided, using latest known epoch.")
        url=("https://api.crypto2099.io/v1/sigma/"+str(poolId))
    try:
        page = urlopen(url)
        pool_data = json.loads(page.read().decode("utf-8"))
    except:
        print("\033[1;31m[WARN]:\033[0m Unable to fetch data from the sigma API.")
        exit()
    try:
        epoch = pool_data['epoch']
        sigma = pool_data['sigma']
        eta0 = pool_data['nonce']
        decentralizationParam = pool_data['d']
    except:
        print("\033[1;31m[ERROR]:\033[0m One or more data points from the API are missing or invalid. Please try again.")
        parse.format_help()
        parser.print_help()
        exit()

    print("d Param:",decentralizationParam)
    print("Pool Active Stake:", pool_data['active_stake'])
    print("Total Active Stake:", pool_data['total_staked'])
    print("Pool Sigma:", sigma)
    print("Epoch Nonce:", eta0)
else:
    if epoch == None:
       print("\033[94m[INFO]:\033[0m No epoch provided, using latest known epoch.")
       url=("https://api.crypto2099.io/v1/epoch/")
    else:
       url=("https://api.crypto2099.io/v1/epoch/"+str(epoch))

    try:
        page = urlopen(url)
        epoch_data = json.loads(page.read().decode("utf-8"))
    except:
        print("\033[1;31m[WARN]:\033[0m Unable to fetch data from the epoch API.")

    try:
        epoch = args.epoch or epoch_data['number']
        sigma = args.sigma
        eta0 = args.eta0 or epoch_data['nonce']
        decentralizationParam = args.d or epoch_data['d']
    except:
        print("\033[1;31m[ERROR]:\033[0m One or more arguments are missing or invalid. Please try again.")
        parser.format_help()
        parser.print_help()
        exit()
    print("Checking leadership log for Epoch",epoch,"[ d Param:",decentralizationParam,"]")

if eta0 == 'TBD':
        print("\033[1;31m[ERROR]:\033[0m You're a bit early. The epoch nonce for Epoch",epoch,"isn't ready yet! Try again later.")
        exit()

if re.search(r"[a-f0-9]{128}", args.skey):
    poolVrfSkey = args.skey
else:
    with open(args.skey) as f:
        skey = json.load(f)
        poolVrfSkey = skey['cborHex'][4:]

# Bindings are not avaliable so using ctypes to just force it in for now.
libsodium = cdll.LoadLibrary("/usr/local/lib/libsodium.so")
#MACOS users can use this and comment line above
#libsodium = cdll.LoadLibrary("/usr/local/lib/libsodium.23.dylib")
libsodium.sodium_init()

# Hard code these for now.
epochLength = 432000
activeSlotCoeff = 0.05
slotLength = 1
epoch211firstslot = 5788800

# calculate first slot of target epoch
firstSlotOfEpoch = 5788800 + (epoch - 211)*epochLength

from decimal import *
getcontext().prec = 9
getcontext().rounding = ROUND_HALF_UP

def isOverlaySlot(firstSlotOfEpoch, currentSlot, decentralizationParam):
    diff_slot = float(currentSlot - firstSlotOfEpoch)
    left = Decimal(diff_slot) * Decimal(decentralizationParam)
    right = Decimal(diff_slot + 1) * Decimal(decentralizationParam)
    if math.ceil( left ) < math.ceil( right ):
        return True
    return False

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
stolencount=0
for slot in range(firstSlotOfEpoch,epochLength+firstSlotOfEpoch):
    overlaySlot = isOverlaySlot(firstSlotOfEpoch, slot, decentralizationParam)
    if overlaySlot and not args.bft:
      continue

    slotLeader = isSlotLeader(slot, activeSlotCoeff, sigma, eta0, poolVrfSkey)

    if slotLeader:
        timestamp = datetime.fromtimestamp(slot + 1591566291, tz=local_tz)

        if overlaySlot:
            stolencount+=1
            print(timestamp.strftime('%Y-%m-%d %H:%M:%S') + " ==> Stolen by BFT for " + str(slot-firstSlotOfEpoch) + ", Cumulative stolen blocks due to d param: " + str(stolencount))
        else:
            slotcount+=1
            print(timestamp.strftime('%Y-%m-%d %H:%M:%S') + " ==> Leader for " + str(slot-firstSlotOfEpoch) + ", Cumulative epoch blocks: " + str(slotcount))

if slotcount == 0:
    print("No slots found for current epoch... :(")
if overlaySlot:
    print("Slots stolen by BFT nodes: " + str(stolencount))
