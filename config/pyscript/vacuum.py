import json


@service
def vacuum_start(rooms: str) -> None:
    """
    Example:
        service: pyscript.vacuum_enqueue_room
        data:
            rooms: '["kitchen"]'
    
    It is expected that rooms is a json-encoded list.
    """
    # Short-circuit if no rooms.
    if not rooms:
        return

    raw_room_list = json.loads(str(rooms))
    
    room_list = []
    for room in raw_room_list:
        if room not in room_list:
            room_list.append(room)

    # Actually start the vacuum.
    for entity_id, room_ids in _process_rooms(room_list).items():
        vacuum.send_command(
            entity_id=entity_id,
            command="app_segment_clean",
            params=[
                {
                    "repeat": 1,
                    "segments": room_ids,
                },
            ],
        )

    # Move the enqueued items to the actively handled queue.
    saver.set_variable(
        name="vacuum.queue",
        value="",
    )
    saver.set_variable(
        name="vacuum.clean",
        value=json.dumps(room_list),
    )


def _process_rooms(rooms: list[str]) -> dict[str, list[int]]:
    output = {
        # NOTE: Only one vacuum currently available.
        "vacuum.roborock_s7": [],
    }

    room_labels = {
        "bedroom": 16,
        "kitchen": 18,
        "living room": 20,
        "dining area": 24,
    }
    for name in rooms:
        room_id = room_labels.get(name)
        if not room_id:
            continue

        output["vacuum.roborock_s7"].append(room_id)

    return output
