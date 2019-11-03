# init/systemd files for OctoPrint.

Assumes OctoPrint is installed under user pi at /home/pi/OctoPrint/venv/bin/octoprint. If you have a different
setup you'll need to adjust octoprint.default (init) or octoprint.service (systemd) accordingly.

## init

```
octoprint.default   => /etc/default/octoprint
octoprint.init      => /etc/init.d/octoprint
```

## systemd

```
octoprint.service   => /etc/systemd/system/octoprint.service
```
