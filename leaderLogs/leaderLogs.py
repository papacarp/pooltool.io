# leader logs proof of concept - all credit goes to @andrewwestberg of BCSH for the algo extraction from cardano-node

import math
import binascii
from datetime import datetime, timezone
from time import mktime
import pytz
import hashlib
from ctypes import *
import re

from urllib.request import urlopen
import json
import argparse

parser = argparse.ArgumentParser(description="Calculate the leadership log.")
parser.add_argument('--vrf-skey', dest='skey', help='provide the path to the pool.vrf.skey file or the raw skey (128 hex characters)', required=True)
parser.add_argument('--sigma', dest='sigma', type=float, help='the controlled stake sigma value of the pool [e.g. 0.0034052348379780869]', required=True)
parser.add_argument('--pool-id', dest='poolId', help='the pool ID')
parser.add_argument('--epoch', dest='epoch', type=int, help='the epoch number [e.g. 221]')
parser.add_argument('--epoch-nonce', dest='eta0', help='the epoch nonce to check')
parser.add_argument('--d-param', dest='d', type=float, help='the current decentralization parameter [e.g. 0.0 - 1.0]')
parser.add_argument('-bft', action='store_true', help='if specified will also calculate slots stolen by BFT due to d not being 0')
parser.add_argument('--tz', dest='tz', default='America/Los_Angeles', help='the local timezone name [Default: America/Los_Angeles]')
parser.add_argument('--porcelain', action='store_true', help='if specified will print JSON')

args = parser.parse_args()

blocks=[]
def print_block(timestamp, stolen, epoch_slot):
    if not args.porcelain:
        if stolen:
            print(timestamp.strftime('%Y-%m-%d %H:%M:%S') + " ==> Stolen by BFT for " + str(slot-firstSlotOfEpoch) + ", Cumulative stolen blocks due to d param: " + str(stolencount))
        else:
            print(timestamp.strftime('%Y-%m-%d %H:%M:%S') + " ==> Leader for " + str(slot-firstSlotOfEpoch) + ", Cumulative epoch blocks: " + str(slotcount))

    else:
        block = dict()
        block["timestamp"] = timestamp.strftime('%Y-%m-%d %H:%M:%S')
        block["timestamp_unix"] = mktime(timestamp.timetuple())
        block["stolen"] = stolen
        block["epochSlot"] = epoch_slot
        blocks.append(block)

def print_safe(*text):
    if not args.porcelain:
        print(text)

epoch = args.epoch
if epoch == None:
   print_safe("\033[94m[INFO]:\033[0m No epoch provided, using latest known epoch.")
   url=("https://epoch-api.crypto2099.io:2096/epoch/")
else:
   url=("https://epoch-api.crypto2099.io:2096/epoch/"+str(epoch))

try:
    page = urlopen(url)
    epoch_data = json.loads(page.read().decode("utf-8"))
except:
    print_safe("\033[1;31m[WARN]:\033[0m Unable to fetch data from the epoch API.")
    exit(1)

try:
    epoch = args.epoch or epoch_data['number']
    poolId = args.poolId
    sigma = args.sigma
    eta0 = args.eta0 or epoch_data['eta0']
    decentralizationParam = args.d or epoch_data['d']
    local_tz = pytz.timezone(args.tz)
except:
    print_safe("\033[1;31m[ERROR]:\033[0m One or more arguments are missing or invalid. Please try again.")
    parser.format_help()
    parser.print_help()
    exit(1)

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

print_safe("Checking leadership log for Epoch", epoch, " [ d Param:", decentralizationParam, "]")
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
        print_safe("error.  Feed me bytes")
        exit(2)

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
            print_block(timestamp, True, slot - firstSlotOfEpoch)
        else:
            slotcount+=1
            print_block(timestamp, False, slot - firstSlotOfEpoch)

if slotcount == 0:
    print_safe("No slots found for current epoch... :(")
if overlaySlot:
    print_safe("Slots stolen by BFT nodes: " + str(stolencount))

if args.porcelain:
    print(json.dumps(blocks))