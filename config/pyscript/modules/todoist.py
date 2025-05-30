from typing import Any


def parse(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Parse extracts all project metadata into a list of dictionaries, each item
    representing a different project.

    :raises: KeyError
    """
    # This is a mapping of project ids to standardized output.
    projects = {}

    # First, process the list of projects.
    for p in payload["projects"]:
        if p.get("is_archived", False):
            continue

        projects[p["id"]] = {
            "id": p["id"],
            "name": p["name"],
            "items": [],
        }

    # Now, assign the list of items.
    for item in payload["items"]:
        pid = item["project_id"]
        if pid not in projects:
            continue

        subset = {}
        for key in [
            "id",
            "content",
            "description",
            "labels",
            "priority",
            "due",
            "section_id",
        ]:
            subset[key] = item[key]

        projects[pid]["items"].append(subset)

    return list(projects.values())


def main() -> None:
    """
    This function permits easier iteration and (manual) testing for the aforementioned
    `parse` function. It is separated from the other service files to avoid depending
    on HomeAssistant-injected globals for testing.
    """
    import argparse
    import json

    parser = argparse.ArgumentParser(description='Parse Todoist project data from JSON file')
    parser.add_argument('filepath', help='Path to the JSON file containing Todoist data')

    args = parser.parse_args()

    try:
        with open(args.filepath, 'r') as file:
            data = json.load(file)

        result = parse(data)
        print(json.dumps(result, indent=2))

    except FileNotFoundError:
        print(f"Error: File '{args.filepath}' not found")
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in file '{args.filepath}': {e}")


if __name__ == '__main__':
    main()
