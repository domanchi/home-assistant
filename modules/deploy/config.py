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

    validate: Optional[Callable[[homeassistant, str], str]]
    """
    Validate is an optional function to check the validity of the configuration files that are
    referenced by [path]. It is expected to raise a ConfigurationError if the provided configuration
    file is invalid.
    """


# NOTE: We currently rely on the config/ prefix to make our lives easier when copying
# files over to the remote host.
synchronized_files = [
    SynchronizedConfig(
        path="config/automations",
        validate=lambda ha, *files: ha.validate_automations(*files),
    ),

    SynchronizedConfig(
        path="config/scripts",
        validate=lambda ha, *files: ha.validate_scripts(*files),
    ),

    SynchronizedConfig(
        path="config/configuration.yaml",
        validate=lambda ha, _: ha.validate_global_configuration(),
    ),
]
