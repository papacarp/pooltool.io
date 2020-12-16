"""
Copyright (c) 2020 Viper Science

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

class SendMyTip():
    """Provide an interface to the pooltool.io API.
    """

    def __init__(self, userid, poolid, genhash, jclipath, restport):
        self.userid = userid
        self.poolid = poolid
        self.genhash = genhash
        self.jclipath = jclipath
        self.restport = restport

    def _get(self, url, params=None):
        """ Query specified URL and return JSON contents
        """
        r = requests.get(url, params=params)
        if r.status_code != 200:
            return None
        else:
            return r.json()

    def get_block(self, block_hash):
        try:
            cmd = (f"{self.jclipath} rest v0 block {block_hash} get "
                   f"--host http://127.0.0.1:{self.restport}/api")
            res = subprocess.run(cmd.split(), 
                stdout=subprocess.PIPE, universal_newlines=True)
            return res.stdout.strip()
        except Exception:
            return None

    def get_status(self):
        try:
            cmd = (f"{self.jclipath} rest v0 node stats get --output-format "
                   f"json --host http://127.0.0.1:{self.restport}/api")
            res = subprocess.run(cmd.split(), 
                stdout=subprocess.PIPE, universal_newlines=True)
            j = json.loads(res.stdout.strip())
        except Exception:
            j = {"state":"error"}
        return j

    def send(self):

        platform_name = "sendmytip.py"

        # Query status information from the pool (Jormungandr)
        raw_status = self.get_status()
        if raw_status["state"].lower() != "running":
            return None
        
        last_block_height = raw_status["lastBlockHeight"]
        last_block_hash = raw_status["lastBlockHash"]
        last_block = self.get_block(last_block_hash)
        last_pool_id = last_block[168:232]
        last_parent = last_block[104:168]
        last_slot = "0x" + last_block[24:32]
        last_epoch = "0x" + last_block[16:24]
        jorm_version = raw_status["version"]
        params = {
            "platform": platform_name,
            "jormver": jorm_version
        }

        # Build the url
        url = (f"https://api.pooltool.io/v0/sharemytip?poolid={self.poolid}"
               f"&userid={self.userid}&genesispref={self.genhash}"
               f"&mytip={last_block_height}&lasthash={last_block_hash}"
               f"&lastpool={last_pool_id}&lastparent={last_parent}"
               f"&lastslot={last_slot}&lastepoch={last_epoch}")

        return self._get(url, params=params)


if __name__ == "__main__":
    
    # Your pool id as on the explorer
    poolid = "52b33axxxxxxxxxxxx"
    
    # get this from your account profile page on pooltool website
    userid = "xxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxx"
    
    # Pooltool only actually looks at the first 7 characters
    genhash = "8e4d2a343f3dcf93"

    # Path to the JCLI instance on your server.
    jcli = "./jcli"

    # REST API port number.
    port = "3100"

    send_my_tip = SendMyTip(userid, poolid, genhash, jcli, port)
    print(send_my_tip.send())
