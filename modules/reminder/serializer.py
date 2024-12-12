import sys
from typing import Any

from ruamel.yaml import YAML

from .task import Task


# NOTE: typ="safe" cannot be used with DoubleQuotedScalarString.
yaml = YAML()

# Make it look more like a YAML file, as compared to a JSON object.
yaml.default_flow_style = False


def serialize_to_yaml(*tasks: Task, filename: str = "") -> bytes:
    """
    This serializes the provided tasks list into a script YAML.

    This was chosen over an automation so that we can modify the variables for improved testability.
    """
    stream = sys.stdout
    if filename:
        stream = open(filename, "w")

    stream.write(
        "# This is an automatically generated file.\n"
        "# Any manual modifications to this will not be persisted.\n"
    )

    yaml.dump({
        "recurring_chores": {
            "mode": "single",
            "alias": "Recurring Chores",
            "description": "Adds TODO items for recurring chores.",

            "fields": {
                # Allow for testability, since we can override variables.
                "today": {
                    "name": "Current Date",
                    "required": True,
                    "selector": {
                        "date": {},
                    },
                },
                "channel": {
                    "name": "Slack Channel",
                    # NOTE: This only configures the UI.
                    # It does not configure the actual default value (which is blank string).
                    # However, this works out in our favor, because now we can choose to send
                    # a slack messsage only when we give this a value.
                    "default": "#claudia-test",
                    "example": "#chores",
                    "selector": {
                        "text": {},
                    },
                },
                "add_task": {
                    "name": "Add Task",
                    "description": "If true, this will add a task on todoist",
                    "default": False,
                    "selector": {
                        "boolean": {},
                    },
                },
            },

            "sequence": [{
                # Run these in parallel, because each reminder doesn't have dependencies
                # on each other.
                "parallel": [
                    _serialize_task(task)
                    for task in tasks
                ],
            }],
        },
    }, stream)

    if filename:
        stream.close()


def _serialize_task(task: Task) -> dict[str, Any]:
    slack_notification = {
        "action": "notify.pockets_inc",
        "data": {
            "target": "{{ channel }}",
            "message": "I've added a chore to your to-do list.",
            "data": {
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": (
                                f"I've added \"*{task.description}*\" to your "
                                "<https://app.todoist.com/app/project/chores-2337975766|to-do list>."
                            ),
                        },
                    },
                ],
            },
        },
    }

    return {
        "if": [
            {
                "condition": "template",
                "value_template": task.cadence.render("as_datetime(today)"),
            },
        ],
        "then": [
            {
                "action": "logbook.log",
                "data": {
                    "name": "Recurring Chores",
                    "entity_id": "script.recurring_chores",
                    "message": f"Added task: {task.description}",
                },
            },
            slack_notification,
            {
                "condition": "template",
                "value_template": "{{ add_task }}",
            },
            {
                "action": "todoist.new_task",
                "data": {
                    "project": "Chores",
                    "labels": "recurring",
                    "content": task.description,
                },
            },
        ],
    }
