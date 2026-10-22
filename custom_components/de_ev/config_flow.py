"""Config flow for the Dé EV Charger development scaffold."""

from __future__ import annotations

from typing import Any

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, NAME


class DeEvConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Placeholder config flow.

    The Tuya cloud discovery, credential validation and device selection are
    implemented in later phases.
    """

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Create a single development entry."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(title=NAME, data={})

        return self.async_show_form(step_id="user")
