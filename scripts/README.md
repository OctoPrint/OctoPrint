# init/systemd files for OctoPrint.

Assumes OctoPrint is installed under user pi at /home/pi/OctoPrint/venv/bin/octoprint. If you have a different
setup you'll need to adjust octoprint.default (init) or octoprint.service (systemd) accordingly.

## init
Download the init.d files to the locations shown:

```
octoprint.default   => /etc/default/octoprint
octoprint.init      => /etc/init.d/octoprint
```

Next, enable and start the `octoprint` service:

```sh
# Enable octoprint service
sudo update-rc.d octoprint defaults

# and start it
sudo service octoprint start
```

## systemd
Download the systemd files to the locations shown:

```
octoprint.service   => /etc/systemd/system/octoprint.service
```

Next, make necessary modifications (if any) then notify systemd:
```sh
sudo systemctl daemon-reload
```

Finally, enable and start the `octoprint` service:

```sh
# Enable octoprint service
sudo systemctl enable octoprint

# and start it
sudo systemctl start octoprint
```
