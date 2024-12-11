# deploy

This directory contains logic to deploy code to the homeassistant server.

## Quick Start

```bash
# First, stage all the files you want to add.
home-assistant $ git add automations/file.yaml

# Then, run the deploy command to upload, test and merge your changes
# if successful.
home-assistant $ bin/deploy -m "<commit message>"
```

## Design

The fundamental reason why this tool needs to be built is because we do not trust a public CI host enough to build a secure tunnel from the CI host to a homeassistant server. Given its sensitive nature, we disable incoming access from the public internet to the homeassistant server, which leaves us two methods of updating configuration:

1.  Upload to the server via a network adjacent device
2.  Have the server periodically query for updates, installing when available

The issue with the second option is that:

-   It requires HAOS (custom) integrations
-   It requires a robust alerting mechanism (i.e. if configuration is invalid)
-   It allows invalid configuration to land on `master`

With better alerting and testing infrastructure, it would be a more ideal solution, but the scope of setting that up is undefined (more difficult than you might think, after initial research).

As such, we rely on this methodology:

1.  Determine change request
2.  Upload modified configuration
3.  Run test
4.  If test passes, commit change. If test fails, rollback change.

## Secret Management

We use [git-secret](https://sobolevn.me/git-secret/) to manage encrypted secrets at rest. Here's a quick guide:

### Adding Secrets

Just add entries to `deploy/secrets.py`. The entire file is GPG-encrypted, and stored in source code. If the key needs to be rotated, it can be done quite easily as well.

Once the new secret has been added, run:

```bash
$ git secret hide
$ git add deploy/secrets.py.secret
```

### Adding Member

First, the user wishing to be added must create a GPG key:

```bash
$ gpg --gen-key

# --armor makes it ASCII
$ gpg --armor --export $email > public-key.gpg

# Share the public key over some communications channel.
# Then, import it into your keyring
$ gpg --import public-key.gpg

# Share the secret with the email.
$ git secret tell $email

# We no longer need their public key, so we can remove it from our
# keyring.
$ gpg --delete-keys $email

# Decrypt, then re-encrypt for newly added user.
$ git secret reveal; git secret hide
```
