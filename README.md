# homeassistant

This repository contains the customized functionality of my homeassistant setup.

## Deploying

First, copy all the files over to the homeassistant instance. I have pre-configured
the homeassistant alias to the designated host in `~/.ssh/config`.

```
Host homeassistant
    HostName control.home
    User root
```

Run this command to upload the files.

```bash
bin/upload homeassistant
```

Finally, visit homeassistant to reload the YAML files: http://control.home:8123/developer-tools/yaml.
It is recommended to check the configuration, before actually restarting it.
