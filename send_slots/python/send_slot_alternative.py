# -*- coding: utf-8 -*-


#  This script validates the slots using the Hash method protecting the actual slot allocation untill the epoch has passed. 
#  To use simply fill in the , Nodes , Pools, pool_ids and user_id variables with your own values 

import requests
import json
import hashlib
import time


##############-- EDIT HERE --##################
Nodes = { "Node1":"http://localhost:3100" } # Node Rest API port
Pools = ["BSP" , "BSP0" ] # Pool tickers
pool_ids = { "BSP":"97ff3c658c7e06dfb3f0cf0353a538e7f3c9c11bc5f89504c2ad6ede652913cf", "BSP0":"df6e1e2717bded5a4fba27533a80fbc82f2445e116d2f93366147d4b49415a43" } # Pool IDs
user_id = "xxxxxxx-xxxxx-xxxx-xxxx-xxxxxxxx" # Pooltool user id
#################################################


master_node = "Node1"

def send_slots(node=master_node):
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
    poolLogs = {}
    poolLogs["genesispref"] = "8e4d2a343f3dcf9330ad9035b3e8d168e6728904262f2c434a4f8f934ec7b676"
    poolLogs["userid"] = user_id
    try:
        r = requests.get( Nodes[node] + '/api/v0/settings')
        settings = json.loads(r.text)

    except Exception as e:
        print (str(e))
        return

    slot_duration = int(settings['slotDuration'])
    slots_per_epoch = int(settings['slotsPerEpoch'])

    curr_epoch = int(((int(time.time()) - 1576264417)) / (slots_per_epoch * slot_duration))
    poolLogs["currentepoch"] = str(curr_epoch)
    try:
        r =requests.get( Nodes[node] + '/api/v0/leaders/logs')
        leaders_logs = json.loads(r.text)
        Pools_log = {}
        for pool in Pools:
            Pools_log[pool] = []
        for d in leaders_logs:
            print(d)
            for i in range(len(Pools)):
                if ((d['enclave_leader_id'] == i+1) and (int(float(d['scheduled_at_date'])) == curr_epoch)) :
                    Pools_log[Pools[i]].append(d)
        for pool in Pools:    
            with open( 'slot_logs/' + pool + '_slots_' + str(curr_epoch) + '.json', 'w') as outfile:
                json.dump(Pools_log[pool], outfile)  
            slots = str(len(Pools_log[pool]))
            
           # send( pool+ " Got : " + slots  + " Blocks \n" + sort_file )
            poolLogs["assigned_slots"] = slots
            poolLogs["poolid"] = pool_ids[pool]
            
            file = open('slot_logs/' + pool + '_slots_' + str(curr_epoch - 1) + '.json', "r") 
            poolLogs["last_epoch_slots"] = file.read() 
            file.close()

            file = open('slot_logs/' + pool + '_slots_' + str(curr_epoch ) + '.json', "rb") 
            poolLogs["this_epoch_hash"] =  hashlib.sha256(file.read()).hexdigest();
            file.close()
            print(poolLogs)
              
            
            r =requests.post( 'https://api.pooltool.io/v0/sendlogs' , data=json.dumps(poolLogs) , headers=headers )
            print(r.text)
    except Exception as e:
        print (str(e))
        return
        
        
send_slots()
