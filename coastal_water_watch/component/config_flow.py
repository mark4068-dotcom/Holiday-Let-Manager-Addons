"""Config flow for Coastal Water Watch."""

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    CONF_LOCATION,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    UPDATE_INTERVAL_OPTIONS,
)
from .locations import LOCATIONS


class CoastalWaterWatchConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure a monitored bathing-water location."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return the polling options flow."""
        return CoastalWaterWatchOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Select a location from the verified catalogue."""
        if user_input is not None:
            location = LOCATIONS[user_input[CONF_LOCATION]]
            await self.async_set_unique_id(location.key)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=location.name,
                data={CONF_LOCATION: location.key},
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_LOCATION): vol.In(
                    {key: location.name for key, location in LOCATIONS.items()}
                )
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)


class CoastalWaterWatchOptionsFlow(config_entries.OptionsFlow):
    """Configure bounded polling behavior."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Change the coordinator polling interval."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self.config_entry.options.get(
            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
        )
        schema = vol.Schema(
            {
                vol.Required(CONF_UPDATE_INTERVAL, default=current): vol.In(
                    UPDATE_INTERVAL_OPTIONS
                )
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
