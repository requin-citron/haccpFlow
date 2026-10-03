from __future__ import annotations

import logging
from typing import Any

from paho.mqtt.client import Client, ConnectFlags, DisconnectFlags
from paho.mqtt.enums import CallbackAPIVersion
from paho.mqtt.properties import Properties
from paho.mqtt.reasoncodes import ReasonCode

from app.config import Settings

logger = logging.getLogger(__name__)


class MqttClient:
    """Keeps one connection to the broker alive.

    No topic is consumed yet: the ingestion layer will be added on top of this.
    The client is intentionally non-blocking so a broker outage never prevents
    the API from starting; readiness reports the degraded state instead.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: Client | None = None

    @property
    def connected(self) -> bool:
        if self._client is None:
            return False
        return bool(self._client.is_connected())

    def start(self) -> None:
        if self._client is not None:
            return

        client = Client(
            callback_api_version=CallbackAPIVersion.VERSION2,
            client_id=self._settings.mqtt_client_id,
            clean_session=True,
        )
        if self._settings.mqtt_username:
            client.username_pw_set(
                self._settings.mqtt_username,
                self._settings.mqtt_password.get_secret_value(),
            )
        client.reconnect_delay_set(min_delay=1, max_delay=30)
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect

        self._client = client
        client.connect_async(
            self._settings.mqtt_host,
            self._settings.mqtt_port,
            keepalive=60,
        )
        client.loop_start()

    def stop(self) -> None:
        client = self._client
        if client is None:
            return
        client.loop_stop()
        client.disconnect()
        self._client = None

    def _on_connect(
        self,
        client: Client,
        userdata: Any,
        flags: ConnectFlags,
        reason_code: ReasonCode,
        properties: Properties | None = None,
    ) -> None:
        if reason_code.is_failure:
            logger.error("MQTT connection refused: %s", reason_code)
            return
        logger.info(
            "Connected to MQTT broker %s:%s",
            self._settings.mqtt_host,
            self._settings.mqtt_port,
        )

    def _on_disconnect(
        self,
        client: Client,
        userdata: Any,
        flags: DisconnectFlags,
        reason_code: ReasonCode,
        properties: Properties | None = None,
    ) -> None:
        logger.warning("Disconnected from MQTT broker: %s", reason_code)
