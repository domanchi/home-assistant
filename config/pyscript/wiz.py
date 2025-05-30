@service
def wiz_cycle_effect(entity_id: str) -> None:
    """
    Example:
        service: pyscript.wiz_cycle_effect
        data:
            entity_id: 'light.wiz'
    """
    if not entity_id:
        return

    current_effect = state.get(f"{entity_id}.effect")
    if current_effect not in _allowed_presets:
        index = 0
    else:
        index = (_allowed_presets.index(current_effect) + 1) % len(_allowed_presets)

    light.turn_on(
        entity_id=entity_id,
        effect=_allowed_presets[index],
    )


# NOTE: The entity's attributes has a set of supported effects.
# Then, it's a matter of selecting a subset that might be fun to play with.
#
# These need to be case sensitive, otherwise, the lightbulb will throw an error.
_allowed_presets = [
    "Fireplace",
    "Romance",
    "Party",
    "Jungle",
    "Ocean",
]