import asyncio
import json
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from typing import Optional

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
        self.uri = base
        self._session = requests.Session()
        self._session.headers["Authorization"] = f'Bearer {self.apikey}'

    def reload(self, *services: str) -> None:
        # NOTE: If you need to reload other things, see
        # https://developers.home-assistant.io/docs/api/rest/ for more details.
        if services:
            logger.info("reloading HA configuration")

        for service in services:
            if not service:
                continue

            self._session.post(f"http://{self.uri}/api/services/{service}/reload")
            logger.debug(f"reloading service: {service}")

    def validate_global_configuration(self) -> str:
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
            return response["warnings"]

        if response.get("result") != "valid":
            raise ConfigurationError(response["errors"])

        return ""

    def validate_automations(self, *files: str) -> str:
        return asyncio.get_event_loop().run_until_complete(
            self._validate_automations(*files),
        )

    async def _validate_automations(self, *files: str) -> str:
        # NOTE: We need to do this synchronously, because websockets library does not
        # permit multiple recv to occur at once.
        results = []
        async with self._establish_websocket_connection() as ws:
            for file in files:
                with open(file) as f:
                    contents = yaml.load(f)

                response = await self._validate_script(
                    ws,
                    triggers=contents.get("trigger") or contents.get("triggers"),
                    conditions=contents.get("condition") or contents.get("conditions"),
                    actions=contents.get("action") or contents.get("actions"),
                )
                if response:
                    results.append(f"'{file}' is invalid: {response}")

        return "\n".join(results)

    def validate_scripts(self, *files: str) -> str:
        return asyncio.get_event_loop().run_until_complete(
            self._validate_scripts(*files),
        )

    async def _validate_scripts(self, *files: str) -> str:
        results = []
        async with self._establish_websocket_connection() as ws:
            for file in files:
                with open(file) as f:
                    contents = yaml.load(f)

                response = await self._validate_script(
                    ws,
                    actions=contents.get("sequence"),
                )
                if response:
                    results.append(f"'{file}' is invalid: {response}")

        return "\n".join(results)

    async def _validate_script(
        self,
        ws: ClientConnection,
        triggers: Optional[list] = None,
        conditions: Optional[list] = None,
        actions: Optional[list] = None,
    ) -> str:
        # Default values.
        if not triggers:
            triggers = []

        if not conditions:
            conditions = []

        if not actions:
            actions = []

        payload = {
            "id": self._id,
            "type": "validate_config",
            "triggers": triggers,
            "conditions": conditions,
            "actions": actions,
        }
        self._id += 1

        await ws.send(json.dumps(payload))

        message = json.loads(await ws.recv())
        if not message["success"]:
            raise ConfigurationError(f"{message['error']['code']}: {message['error']['message']}")

        return ";\n".join([
            f"{key} failed with error: {message['result'][key]['error']}"
            for key in ["triggers", "conditions", "actions"]
            if not message["result"][key]["valid"]
        ])

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
