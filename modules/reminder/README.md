# reminder

This directory contains logic to configure recurring reminders.

## Quick Start

To update recurring task list, first add your changes to `task.py`. Then, run the following command:

```bash
$ python -m modules.reminder > config/scripts/recurring-chores.yaml
$ git add config/scripts/recurring-chores.yaml
$ bin/deploy -v -m "$commitMessage"
```

## Design

HomeAssistant does not support scheduling things any longer than a daily basis. However, we want a method to register recurring reminders so that the HomeAssistant can send out notifications about infrequent (albeit predictable) chores.

The first iteration of this system kept it to a basic YAML: by leveraging the automations specifications language, we can trigger a poor man's cron job on a daily basis, and check to see what tasks have been queued up for that specific day. Unfortunately, due to HomeAssistant's strict parsing, the YAML file has a lot of duplicated code, and is difficult to iterate upon / test.

To address this issue, we construct an abstraction layer over this poor man's cron job. This module ingests a basic list of recurring reminders, and outputs a YAML file in the format that HomeAssistant will accept. Furthermore, by adding this abstraction layer, we seek to achieve the following objectives:

1.  Make it easy to add new recurring tasks to be tracked
2.  Make it easy to test resulting YAML
3.  De-couple intent from implementation details

## Testing

### Manual

This is written as a script to be invoked by an automation, so that we can explicitly pass in variables into the script to simulate a specific date. To do this:

1.  Visit the [Recurring Chores](http://control.home:8123/config/script/show/script.recurring_chores) script in the UI
2.  Click on the hamburger icon, and click "Information"
3.  Configure the inputs accordingly.
4.  Hit "Run".

