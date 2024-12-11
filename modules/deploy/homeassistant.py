import json
import shlex

from .connection import Connection
from .logger import logger
from .secrets import API_TOKEN


class ConfigurationError(ValueError):
    pass


class homeassistant:
    def __init__(self, conn: Connection) -> None:
        # Public for easier testing.
        self.conn = conn

    def check_configs(self, force: bool = False) -> None:
        """
        Currently, this only checks to see if the homeassistant will fail to reload.
        In the future, we should build in automations validation too.

        :raises: CalledProcessError on invalid configuration
        :raises: json.JSONDecodeError on invalid server response
        """
        result = self.curl(
            "-X", "POST",
            "http://homeassistant.local:8123/api/config/core/check_config",
        )

        response = json.loads(result)
        if response.get("warnings"):
            if not force:
                raise ConfigurationError(response["warnings"])

            logger.warning(response["warnings"])

        if response.get("result") == "valid":
            logger.info("no issues found with HA configuration")
            return

        raise ConfigurationError(response["errors"])

    def reload(self, type: str = "") -> None:
        # TODO: How to reload other things besides "automation"?
        logger.info("reloading HA configuration")
        self.curl(
            "-X", "POST",
            "http://homeassistant.local:8123/api/services/automation/reload",
        )

    def curl(self, *args: str) -> bytes:
        logger.debug(shlex.join(["curl", *args]))
        return self.conn.do(
            "curl",
            "-H", f"Authorization: Bearer {self.apikey}",
            *args,
        )

    @property
    def apikey(self) -> str:
        return API_TOKEN
