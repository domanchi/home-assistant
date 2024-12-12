import asyncio
import json
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import requests
import websockets
from ruamel.yaml import YAML
from websockets.client import ClientConnection

from .logger import logger
from .secrets import API_TOKEN


yaml = YAML(typ="safe")


class ConfigurationError(ValueError):
    pass


class NetworkInvariantError(ValueError):
    """This is raised when protocols do not match expectations."""
    pass


class homeassistant:
    """
    Defines an interface to interact with the HomeAssistant server.

    For more information, check out:
        - https://developers.home-assistant.io/docs/api/rest
    """

    def __init__(self, base: str) -> None:
        self.uri = f"{base}:8123"
        self._session = requests.Session()
        self._session.headers["Authorization"] = f'Bearer {self.apikey}'

    def reload(self, type: str = "") -> None:
        # NOTE: If you need to reload other things, see
        # https://developers.home-assistant.io/docs/api/rest/ for more details.
        logger.info("reloading HA configuration")

        for service in [
            "automation",
            "script",
        ]:
            self._session.post(f"http://{self.uri}/api/services/{service}/reload")

    def check_configs(self, *files: str, force: bool = False) -> None:
        """Checks configuration files for validity."""
        warnings = asyncio.get_event_loop().run_until_complete(self._check_configs(*files))
        if warnings:
            if not force:
                raise ConfigurationError(warnings)

            for message in warnings:
                logger.warning(message)
        else:
            logger.info("no issues found with HA configuration")

    async def _check_configs(self, *files: str) -> list[str]:
        return [
            result
            for results in await asyncio.gather(
                self._validate_global_config(),
                self._validate_automations(*files),
            )
            for result in results
            if result
        ]

    async def _validate_global_config(self) -> list[str]:
        """
        Check to make sure that configuration.yaml is valid.
        Returns warnings if an error is detected, but not loud enough to cause issues when
        rebooting.

        :returns: configuration warnings, if applicable.
        :raises: ConfigurationError on invalid config
        """
        result = self._session.post(f"http://{self.uri}/api/config/core/check_config")

        response = result.json()
        if response.get("warnings"):
            return [response["warnings"]]

        if response.get("result") != "valid":
            raise ConfigurationError(response["errors"])

        return []

    async def _validate_automations(self, *files: str) -> list[str]:
        """
        Check to make sure that configured automations are valid.
        Returns warnings if an error is detected.

        :raises: NetworkInvariantError if websocket connection cannot be established.
        """
        async with self._establish_websocket_connection() as ws:
            # NOTE: We need to do this synchronously, because websockets library does not
            # permit multiple recv to occur at once.
            return [
                item
                for f in files
                for item in await self._validate_automation(ws, f)
            ]

    async def _validate_automation(self, ws: ClientConnection, file: str) -> list[str]:
        with open(file) as f:
            contents = yaml.load(f)

        trigger = contents.get("trigger") or contents.get("triggers") or []
        condition = contents.get("condition") or contents.get("conditions") or []
        action = contents.get("action") or contents.get("actions") or []

        payload = {
            "id": self._id,
            "type": "validate_config",
            "trigger": trigger,
            "condition": condition,
            "action": action,
        }

        self._id += 1
        await ws.send(json.dumps(payload, separators=(",", ":")))

        message = json.loads(await ws.recv())
        return [
            f"{file}::{key} failed with error: {message['result'][key]['error']}"
            for key in ["trigger", "condition", "action"]
            if not message["result"][key]["valid"]
        ]

    @asynccontextmanager
    async def _establish_websocket_connection(self) -> AsyncGenerator[ClientConnection, None]:
        """
        For more details on this handshake, see
        https://developers.home-assistant.io/docs/api/websocket

        :raises: NetworkInvariantError
        """
        async with websockets.connect(f"ws://{self.uri}/api/websocket") as ws:
            message = json.loads(await ws.recv())
            if message["type"] != "auth_required":
                raise NetworkInvariantError(f"expect: type='auth_required', got '{message}'")

            await ws.send(json.dumps({
                "type": "auth",
                "access_token": self.apikey,
            }))

            message = json.loads(await ws.recv())
            if message["type"] != "auth_ok":
                raise NetworkInvariantError(f"expect: type='auth_ok', got '{message}'")

            # NOTE: An auto-incrementing id field is required by HomeAssistant websocket manager.
            self._id = 1
            yield ws

    @property
    def apikey(self) -> str:
        return API_TOKEN
