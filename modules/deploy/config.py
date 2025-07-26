from dataclasses import dataclass
from typing import Callable
from typing import Optional

from .homeassistant import homeassistant


@dataclass
class SynchronizedConfig:
    path: str
    """
    Path is the relative path to the synchronized configuration files, from the root of the
    git repo. It may refer to one specific file, or an entire directory of configuration files.

    Required.
    """

    service: Optional[str]
    """
    Service returns the HomeAssistant service to reload, in order for changes to be applied.

    Recall that HomeAssistant entities are defined as `$service.$functionName`, and each service
    can be independently restarted (with caveats). As such, this parameter increases system
    stability by permitting targeted restarts.
    """

    validate: Optional[Callable[[homeassistant, *tuple[str, ...]], str]]
    """
    Validate is an optional function to check the validity of the configuration files that are
    referenced by [path]. It is expected to raise a ConfigurationError if the provided configuration
    file is invalid.
    """


def _ignore_validation(_, *args) -> str:
    return ""


# NOTE: We currently rely on the config/ prefix to make our lives easier when copying
# files over to the remote host.
synchronized_files = [
    SynchronizedConfig(
        path="config/automations",
        service="automation",
        validate=lambda ha, *files: ha.validate_automations(*files),
    ),

    SynchronizedConfig(
        path="config/scripts",
        service="script",
        validate=lambda ha, *files: ha.validate_scripts(*files),
    ),

    SynchronizedConfig(
        path="config/api-actions",
        service="rest_command",
        validate=_ignore_validation,
    ),
    SynchronizedConfig(
        path="config/www",
        service=None,
        validate=_ignore_validation,
    ),

    # Helpers
    SynchronizedConfig(
        path="config/helpers/input_number",
        service="input_number",
        validate=_ignore_validation,
    ),
    SynchronizedConfig(
        path="config/helpers/input_datetime",
        service="input_datetime",
        validate=_ignore_validation,
    ),
    SynchronizedConfig(
        path="config/helpers/input_boolean",
        service="input_boolean",
        validate=_ignore_validation,
    ),

    # NOTE: This is configured with auto refresh upon deploy.
    SynchronizedConfig(
        path="config/pyscript",
        service=None,
        validate=_ignore_validation,
    ),

    SynchronizedConfig(
        path="config/configuration.yaml",
        service=None,
        validate=lambda ha, _: ha.validate_global_configuration(),
    ),
]
