from datetime import datetime as dt
from typing import Any
from zoneinfo import ZoneInfo

import todoist


@service
def parse_todoist_api() -> None:
    """
    This service transforms the Todoist Sync API into individually tracked
    projects (mapped to sensors).

    Example:
        action: pyscript.parse_todoist_api
        data: {}
    """
    data = fetch()

    try:
        projects = todoist.parse(data)
    except KeyError as e:
        log.error(f"invalid payload: {str(e)}")
        return

    # Update sensors for each project
    for project in projects:
        project_name = project["name"]

        # Create sensor entity ID
        sensor_id = f"sensor.todoist_project_{project_name.lower()}"

        # Set sensor state and attributes
        state.set(
            sensor_id,
            value=project["id"],
            new_attributes={
                'friendly_name': f"Todoist: {project_name}",
                'last_updated': dt.now(tz=ZoneInfo("America/Los_Angeles")).isoformat(),
                **project,
            }
        )

        log.info(f"updated {sensor_id}")


def fetch() -> dict[str, Any]:
    """Fetch retrieves the data from the API."""

    # NOTE: We outsource this to `rest_command` integration, so that we don't need to
    # store secrets in this script.
    #
    # NOTE: We perform this within pyscript because there are payload limitations
    # when shuttling it between services (32768 bytes).
    data = service.call(
        "rest_command",
        "todoist_fetch_data",
        blocking=True,
        return_response=True,
    )

    return data.get("content", {})
