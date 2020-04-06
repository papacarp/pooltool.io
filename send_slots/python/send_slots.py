"""
Copyright (c) 2020 Tilia I/O, A Cardano staking pool, https://tiliaio.com

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import json
import requests
import subprocess
import sys
import os
import getopt
import requests
import hashlib
from subprocess import Popen, PIPE

class Slots():
    def __init__(self, parsed_params):
        self._p = parsed_params
        self._node_stats = None
        self._leaders_logs = None
        self._current_epoch = None
        self._previous_epoch = None
        self._url_pool_tool = 'https://api.pooltool.io/v0/sendlogs'
        self._headers = {
             "Accept": "application/json",
             "Content-Type": "application/json",
        }

    def _get_node_stats(self):
        try:
            r = requests.get("{}/node/stats".format(self._p['jormungandr_restapi']))
            if r.status_code == 200:
                return r.json()
            else:
                print("An error occoured, error code: {}".format(r.status_code))
                return None
        except Exception as e:
            print("Error: Nodestats not avaliable. Node is down or rest API misconfigured? Check REST Port and Path.")
            print(e)
            sys.exit(1)

        return None

    def _send_data(self, data):
        try:
            print("Packet Sent:")
            print(json.dumps(data))

            r = requests.post(self._url_pool_tool, data=json.dumps(data), headers=self._headers)

            print('Response received:')
            print(r.content.decode())
            sys.exit(0)
        except Exception as e:
            print('Error: Sending data failed.')
            print(e)

    def _get_leaders_logs(self):
        try:
            r = requests.get("{}/leaders/logs".format(self._p['jormungandr_restapi']))
            if r.status_code == 200:
                return r.json()
            else:
                print("An error occoured, error code: {}".format(r.status_code))
                return None
        except Exception as e:
            print('Error: Failed to get leaders logs.')
            print(e)

        return None

    def _write_data(self, filename, data):
        try:
            with open(filename, 'w') as f:
                    f.write(data)
            return True
        except Exception as e:
            print('Error: Failed to write data to file {}.'.format(filename))
            print(e)

        return False

    def _read_data(self, filename):
        data = None
        try:
            with open(filename, 'r') as f:
                data = f.read()
        except Exception as e:
            print('Error: Failed to read data from file {}.'.format(filename))
            print(e)
            sys.exit(1)
        
        return data

    def _get_current_slots(self):
        current_slots = []
        for slot in self._leaders_logs:
            dot_pos = slot['scheduled_at_date'].find('.')
            if dot_pos > -1 and slot['scheduled_at_date'][0:dot_pos] == str(self._current_epoch):
                current_slots.append(slot)
        return current_slots

    def _generate_new_key(self):
        try:
            cmd = ["openssl", "rand", "-base64", "32"]
            proc = Popen(cmd, stdout=PIPE, stdin=PIPE, stderr=PIPE)
            stdout, stderr = proc.communicate()
            if proc.returncode != 0:
                print('Error: Failed to generate new key.')
                print('stdout: {}\nstderr:{}'.format(stdout.decode(), stderr.decode()))
                sys.exit(1)

            return stdout.decode().rstrip()
        except Exception as e:
            print('Error: Failed to generate new key')
            print(e)
            sys.exit(1)

        return None

    def _encrypt_current_slots(self):
        stdout = None
        stderr = None
        try:
            slots_to_encrpyt = json.dumps(self._current_slots) if (len(self._current_slots) > 0) else '[]'
            cmd1 = ["echo", slots_to_encrpyt]
            proc1 = Popen(cmd1, stdout=PIPE, stdin=PIPE, stderr=PIPE)
            cmd2 = ["gpg", "--symmetric", "--armor", "--batch", "--passphrase", self._current_epoch_key]
            proc2 = Popen(cmd2, stdout=PIPE, stdin=proc1.stdout, stderr=PIPE)

            stdout, stderr = proc2.communicate()
            if proc2.returncode != 0:
                print('Error: Failed to encrypt current slots.')
                print('stdout: {}\nstderr:{}'.format(stdout.decode(), stderr.decode()))
                sys.exit(1)
        except Exception as e:
            print('Error: Failed to encrypt current slots.')
            print(e)

            sys.exit(1)

        return stdout.decode().rstrip()

    def _verify_slots_gpg(self):
        previous_epoch_passphrase_filename = '{key_path}{s}passphrase_{epoch}'.format(key_path=self._p['key_path'], s=os.sep, epoch=self._previous_epoch)
        previous_epoch_key = None
        if os.path.exists(previous_epoch_passphrase_filename):
            previous_epoch_key = self._read_data(previous_epoch_passphrase_filename)
        else:
            previous_epoch_key = ''

        current_epoch_passphrase_filename = '{key_path}{s}passphrase_{epoch}'.format(key_path=self._p['key_path'], s=os.sep, epoch=self._current_epoch)
        if os.path.exists(current_epoch_passphrase_filename):
            self._current_epoch_key = self._read_data(current_epoch_passphrase_filename)
        else:
            self._current_epoch_key = self._generate_new_key()
            self._write_data(current_epoch_passphrase_filename, self._current_epoch_key)

        # Encrypting current slots for sending to pooltool
        current_slots_encrypted = self._encrypt_current_slots()

        data = {
            'currentepoch': str(self._current_epoch),
            'poolid': self._p['pool_id'],
            'genesispref': self._p['genesis'],
            'userid': self._p['user_id'],
            'assigned_slots': str(len(self._current_slots)),
            'previous_epoch_key': previous_epoch_key,
            'encrypted_slots': current_slots_encrypted
        }

        self._send_data(data)

    def _verify_slots_hash(self):
        # pushing the current slots to file and getting the slots from the last epoch
        leader_slots_prev_epoch_filename = '{key_path}{s}leader_slots_{epoch}'.format(key_path=self._p['key_path'], s=os.sep, epoch=self._previous_epoch)
        last_epoch_slots = None
        if os.path.exists(leader_slots_prev_epoch_filename):
            last_epoch_slots = json.loads(self._read_data(leader_slots_prev_epoch_filename))
        else:
            last_epoch_slots = ''

        leader_slots_current_epoch_filename = '{key_path}{s}leader_slots_{epoch}'.format(key_path=self._p['key_path'], s=os.sep, epoch=self._current_epoch)
        if not os.path.exists(leader_slots_current_epoch_filename):
            self._write_data(leader_slots_current_epoch_filename, json.dumps(self._current_slots))

        # hash verification version
        hash_current_epoch_filename = '{key_path}{s}hash_{epoch}'.format(key_path=self._p['key_path'], s=os.sep, epoch=self._current_epoch)
        current_epoch_hash = hashlib.sha256(json.dumps(self._current_slots).encode('utf-8')).hexdigest()
        self._write_data(hash_current_epoch_filename, current_epoch_hash)

        data = {
            'currentepoch': str(self._current_epoch),
            'poolid': self._p['pool_id'],
            'genesispref': self._p['genesis'],
            'userid': self._p['user_id'],
            'assigned_slots': str(len(self._current_slots)),
            'this_epoch_hash': current_epoch_hash,
            'last_epoch_slots': '[]' if type(last_epoch_slots) is list and len(last_epoch_slots) == 0 else last_epoch_slots
        }

        self._send_data(data)

    def _no_verification_method(self):
        data = {
            'currentepoch': str(self._current_epoch),
            'poolid': self._p['pool_id'],
            'genesispref': self._p['genesis'],
            'userid': self._p['user_id'],
            'assigned_slots': str(len(self._current_slots)),
        }

        self._send_data(data)

    def process(self):
        self._node_stats = self._get_node_stats()
        if self._node_stats is None:
            return
        try:
            self._current_epoch = int(self._node_stats['lastBlockDate'][0 : self._node_stats['lastBlockDate'].find('.')])
            self._previous_epoch = self._current_epoch - 1
        except Exception as e:
            print('Error: Failed to parse lastBlockDate.')
            print(e)
            sys.exit(1)

        self._leaders_logs = self._get_leaders_logs()
        if self._leaders_logs is None:
            return

        self._current_slots = self._get_current_slots()

        if parsed_params['verify_slots_gpg']:
            self._verify_slots_gpg()
        elif parsed_params['verify_slots_hash']:
            self._verify_slots_hash()
        else:
            self._no_verification_method()

def show_invalid_params(invalid_params, params):
    print("Error: Invalid parameters:")
    for param in invalid_params:
        print("{invalid_param} = {param_value}".format(invalid_param=param, param_value=params[param]))

    print()

def show_help(program_name, params):
    print("{} [ -g [0|1] | -s [0|1] ] [OPTION]....".format(program_name))
    print()
    print("Mandatory parameters (without any defaults):")
    print("-i, {:<30} {}".format("--pool-id=POOL_ID", "Stake pool id"))
    print("-u, {:<30} {}".format("--user-id=USER_ID", "PoolTool user id"))
    print()
    print("Optional parameters with default fallback values:")
    print("-g, {:<30} {}".format("--verify-gpg=BOOL", "Determines what you upload to pooltool, default: 0, BOOL:[0,1]"))
    print("-s, {:<30} {}".format("--verify-hash=BOOL", "Determines what you upload to pooltool, default: 0, BOOL:[0,1]"))
    url = params['jormungandr_restapi'].format(rest_api_port=params['restapi_port'])
    print("-r, {:<30} {}".format("--jormungandr_restapi=URL", "Jormungandr rest api url, default: {url}".format(url=url)))
    print("-p, {:<30} {}".format("--restapi-port=PORT", "Port number for jormungandr rest api, default: 5001"))
    print("-i, {:<30} {}".format("--pool-id=POOL_ID", "Stake pool id"))
    print("-u, {:<30} {}".format("--user-id=USER_ID", "PoolTool user id"))
    print("-t, {:<30} {}".format("--genesis=THIS_GENESIS", "Genesis hash, default: 8e4d2a343f3dcf93"))
    print("-k, {:<30} {}".format("--key-path=KEY_PATH", "Location where the temporary files generated by this tool will be stored, default: /tmp/keystorage"))

    print("If neither -g nor -s are specified the number of slots will be sent to pooltool but pooltool won't be able to verify the number of blocks processed by the pool.")

def create_path(key_path):
    if not os.path.exists(key_path):
        print("Key directory doesn't exist. Making the directory ...")
        try:
            os.mkdir(key_path)
        except Exception as e:
            print('Error: Failed to create dir {}'.format(key_path))
            print(e)
            sys.exit(1)

def parse_cmd_parameters(argv):
    # default parameters values
    parsed_params = {
        'verify_slots_gpg': False,
        'verify_slots_hash': False,
        'jormungandr_restapi': 'http://127.0.0.1:{rest_api_port}/api/v0',
        'restapi_port': 5001,
        'pool_id': '',
        'user_id': '',
        'genesis': '8e4d2a343f3dcf93',
        'key_path': '/tmp/keystorage'
    }

    # get program name
    program_name = argv[0]

    # if program is called without parameters show help and quit
    if len(argv) <= 1:
        show_help(program_name, parsed_params)
        sys.exit(0)

    argvs = argv[1:]

    try:
        opts, args = getopt.getopt(argvs, "h:g:s:r:p:i:u:t:k:", ["verify-gpg=", "verify-hash=", "jormungandr_restapi=", 
            "restapi-port=", "pool-id=", "user-id=", "genesis=", "key-path="])
    except getopt.GetoptError:
        show_help(program_name, parsed_params)
        sys.exit(1)

    invalid_params = []
    for opt, arg in opts:
        if opt == '-h':
            show_help(program_name, parsed_params)
        elif opt in ("-g", "--verify-gpg"):
            if not arg is None and len(arg) > 0:
                parsed_params['verify_slots_gpg'] = False if int(arg) == 0 else True
            else:
                parsed_params['verify_slots_gpg'] = True
        elif opt in ("-s", "--verify-hash"):
            if not arg is None and len(arg) > 0:
                parsed_params['verify_slots_hash'] = False if int(arg) == 0 else True
            else:
                parsed_params['verify_slots_hash'] = False
        elif opt in ("-r", "--jormungandr-restapi"):
            if not arg is None and len(arg) > 0:
                parsed_params['jormungandr_restapi'] = arg
        elif opt in ("-p", "--restapi-port"):
            if not arg is None and len(arg) > 0:
                parsed_params['restapi_port'] = arg
        elif opt in ("-i", "--pool-id"):
            if not arg is None and len(arg) > 0:
                parsed_params['pool_id'] = arg
            else:
                invalid_params.append('pool_id')
        elif opt in ("-u", "--user-id"):
            if not arg is None and len(arg) > 0:
                parsed_params['user_id'] = arg
            else:
                invalid_params.append('user_id')
        elif opt in ("-t", "--genesis"):
            if not arg is None and len(arg) > 0:
                parsed_params['this_genesis'] = arg
        elif opt in ("-k", "--key-path"):
            if not arg is None and len(arg) > 0:
                parsed_params['key_path'] = arg

    if len(invalid_params) > 0:
        show_invalid_params(invalid_params, parsed_params)
        show_help(program_name, parsed_params)

    if parsed_params['verify_slots_gpg'] and parsed_params['verify_slots_hash']:
        print("Error: You can choose upload method to verify slots with gpg or hash but not both.")
        sys.exit(1)

    if parsed_params['jormungandr_restapi'].find('rest_api_port') > -1:
        parsed_params['jormungandr_restapi'] = parsed_params['jormungandr_restapi'].format(rest_api_port=parsed_params['restapi_port'])

    return parsed_params

if __name__ == "__main__":

    parsed_params = parse_cmd_parameters(sys.argv)

    # make sure the path exists. If it doesn't it will be created
    create_path(parsed_params['key_path'])

    print("Everything ok. Starting ...")
    slots = Slots(parsed_params)
    slots.process()