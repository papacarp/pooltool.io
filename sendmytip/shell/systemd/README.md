# send my tip for systemd #

This is a modified version of the ```sendmytip.sh``` script so that it can work for those who do not use ```cntools``` and manage their ```cardano-node``` with ```systemd```.

This script is provided by Andrea of the [Insalada Stake Pool](https://insalada.io) (ticker: SALAD). Reach out to him on [PoolTool Telegram Channel](https://t.me/pooltool) for any issue with this script.

## paths and assumptions ##

For this script to work, you should:

- use the default scribes for your ```cardano-node``` logs:

``` json
"defaultScribes": [
  [
    "StdoutSK",
    "stdout"
  ]
],
```

``` json
"setupScribes": [
  {
    "scFormat": "ScText",
    "scKind": "StdoutSK",
    "scName": "stdout",
    "scRotation": null
  }
]
```

- use ```systemd``` to manage cardano-node ```/etc/systemd/system/cardano-node.service```:

``` text
[Unit]
Description=Block Producing Node
After=multi-user.target

[Service]
Type=simple
EnvironmentFile=/home/cardano-node/cardano-node.env
ExecStart=/usr/local/bin/cardano-node run --config $CONFIG --topology $TOPOLOGY --database-path $DBPATH --socket-path $SOCKETPATH --host-addr $HOSTADDR --port $PORT --shelley-kes-key $KES_SK --shelley-vrf-key $VRF_SK --shelley-operational-certificate $OPCERT
KillSignal=SIGINT
RestartKillSignal=SIGINT
StandardOutput=journal
StandardError=journal
SyslogIdentifier=cardano-node

LimitNOFILE=65536

Restart=on-failure
RestartSec=15s
WorkingDirectory=~
User=cnode
Group=cnode

[Install]
WantedBy=multi-user.target
```

this would be the environment file (```/home/cardano-node/cardano-node.env```):

``` text
CONFIG="./config/config.json"
TOPOLOGY="./config/topology.json"
DBPATH="./db/"
SOCKETPATH="./socket/node.socket"
HOSTADDR="0.0.0.0"
PORT="3000"
KES_SK="./keys/kes.skey"
VRF_SK="./keys/vrf.skey"
OPCERT="./keys/opcert"
```

- use ```rsyslog``` (```/etc/rsyslog.d/90-cardano-node.conf```) to write the logs to a standard location:

``` text
if $programname == 'cardano-node' then /var/log/cardano-node.log
& stop
```

- use ```logrotate``` (```/etc/logrotate.d/cardano-node```) to rotate your logs:

``` text
/var/log/cardano-node.log {
    daily
    rotate 30
    copytruncate
    compress
    delaycompress
    notifempty
    missingok
}
```

The script also assumes the followings:

- your cardano node user is ```cnode```
- your ```cnode``` user home directory is ```/home/cardano-node```
- your socket path is ```/home/cardano-node/socket/node.socket```
- the script is placed in ```/root/scripts/sendmytip.sh```
- the script is run with the provided ```sendmytip.service``` unit file
- your server timezone is UTC
- the time format in the logs is ```YYYY-MM-DD HH-MM-SS UTC```

## setup and usage ##

Of course the above assumptions would only work with on such setup. You may need to adjust paths and variables to suit your system. Once you've made sure of properly running ```cardano-node``` with ```systemd``` and logging, you **may** need to:

- adjust the variables (**required** for pool related variables) in the script.
- adjust paths in the script (only if they differ).
- copy the script in a location of your choice. (```/root/scripts/``` would work out of the box)
- make the script executable (```chmod +x /root/scripts/sendmytip.sh```)
- change the ```ExecStart``` path script in the ```sendmytip.service``` unit file to match where you have placed it (only if they differ).
- copy ```sendmytip.service``` unit file in ```/etc/systemd/system/sendmytip.service```
- run ```systemctl daemon-reload```
- run ```systemctl start sendmytip```

Now your cardano node is sending the tip to Pooltool, and your pool will have the Height filed populated on Pooltool.
