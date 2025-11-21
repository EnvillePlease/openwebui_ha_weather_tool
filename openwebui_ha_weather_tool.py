# -----------------------------------------------------------------------------
# Script Name : openwebui_ha_weather_tool.py
# Author      : Clark Nelson
# Company     : CNSoft OnLine
# Version     : 1.0.7
# -----------------------------------------------------------------------------

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import httpx
import asyncio
from pydantic import BaseModel, Field
from zoneinfo import ZoneInfo

# Configure minimal logging for debugging and errors
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Tools:
    """
    Open WebUI Home Assistant Weather Tool for fetching weather data from Home Assistant.

    Notes:
    - Methods are async where network IO is required.
    - Returns JSON strings for easy integration with systems expecting text payloads.
    """

    class Valves(BaseModel):
        """Configuration valves for Open WebUI Home Assistant Weather Tool."""

        HA_URL: str = Field(
            default="https://my-home-assistant.local:8123",
            description="URL of the Home Assistant instance.",
        )
        HA_API_TOKEN: str = Field(
            default="",
            description="Long lived API token to give Open WebUI access to Home Assistant.",
        )
        HA_HOURLY_FORECAST_SENSOR_NAME: str = Field(
            default="",
            description="Name of the sensor in Home Assistant that contains the hourly forecast data.",
        )
        HA_DAILY_FORECAST_SENSOR_NAME: str = Field(
            default="",
            description="Name of the sensor in Home Assistant that contains the daily forecast data.",
        )
        HA_CURRENT_SENSOR_NAME: str = Field(
            default="",
            description="Name of the sensor in Home Assistant that contains the current weather data.",
        )
        HA_RANGE_SENSOR_NAME: str = Field(
            default="",
            description="Name of the sensor in Home Assistant that contains the weather ranges data.",
        )
        HA_CURRENT_DATE_TIME_SENSOR_NAME: str = Field(
            default="",
            description="Name of the sensor in Home Assistant that contains the current date and time.",
        )
        HA_TIMEZONE: str = Field(
            default="Europe/London",
            description="Home Assistant timezone, used for formatting dates and times in the weather data.",
        )
        HA_LOCATION: str = Field(
            default="96 Pooley View, Polesworth, Warwickshire, UK",
            description="Home Assistant location, used for displaying the weather data.",
        )
        # New valves: units for display/concatenation
        HA_TEMPERATURE_UNIT: str = Field(
            default="°C",
            description="Unit string to append to temperature readings (e.g. '°C').",
        )
        HA_HUMIDITY_UNIT: str = Field(
            default="%",
            description="Unit string to append to humidity readings (e.g. '%').",
        )
        HA_PRESSURE_UNIT: str = Field(
            default="hPa",
            description="Unit string to append to pressure readings (e.g. 'hPa').",
        )

    def __init__(self) -> None:
        # Instance configuration container
        self.valves = self.Valves()

    # -------------------------
    # Helper methods
    # -------------------------
    def _build_headers(self) -> Dict[str, str]:
        """Create HTTP headers for Home Assistant API calls."""
        return {"Authorization": f"Bearer {self.valves.HA_API_TOKEN}"}

    def _get_sensor_url(self, sensor_name: str) -> str:
        """Return the full API URL for a given sensor name."""
        return f"{self.valves.HA_URL.rstrip('/')}/api/states/{sensor_name}"

    def _parse_datetime(self, dt_value: str, tz_name: str) -> str:
        """
        Parse a datetime-like string and attach timezone info.
        Returns ISO formatted string on success, original value on failure.
        Handles common formats and ISO strings.
        """
        if not dt_value or not isinstance(dt_value, str):
            return dt_value

        tz = ZoneInfo(tz_name)
        s = dt_value.replace(",", "").strip()
        # Try common formats in order
        parse_attempts = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M",
        ]
        for fmt in parse_attempts:
            try:
                dt = datetime.strptime(s, fmt)
                dt = dt.replace(tzinfo=tz)
                return dt.isoformat()
            except ValueError:
                continue

        # Last resort: try fromisoformat (handles offsets) and ensure tz
        try:
            dt = datetime.fromisoformat(s)
            # attach timezone if naive
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=tz)
            return dt.isoformat()
        except Exception as e:
            logger.debug("Datetime parsing failed for '%s': %s", s, e)
            # return original string if parsing fails
            return dt_value

    def _localize_forecast_times(self, forecast_list: List[Dict[str, Any]], timezone_str: str) -> List[Dict[str, Any]]:
        """
        Attach timezone info to all datetime-like fields in a forecast list.
        Modifies the list in place and returns it for convenience.
        """
        if not isinstance(forecast_list, list):
            return forecast_list

        for entry in forecast_list:
            # Check common keys that Home Assistant uses
            for key in ("datetime", "time", "datetime_utc", "timestamp"):
                if key in entry and isinstance(entry[key], str):
                    entry[key] = self._parse_datetime(entry[key], timezone_str)
        return forecast_list

    def _format_value_with_unit(self, value: Any, unit: str) -> Optional[str]:
        """Return a string with the value concatenated with unit, or None if value is None."""
        if value is None:
            return None
        # Keep simple formatting: use Python's default string conversion
        try:
            return f"{value}{unit}"
        except Exception:
            return str(value)

    # -------------------------
    # Networking
    # -------------------------
    async def _fetch_sensor_data_async(self, url: str, headers: Dict[str, str], sensor_name: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Asynchronously fetch sensor data from Home Assistant API.
        Returns tuple: (data_dict_or_None, error_message_or_None)
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)
        except Exception as e:
            return None, f"Network error fetching '{sensor_name}': {str(e)}"

        if response.status_code != 200:
            return None, f"Sensor '{sensor_name}' not found or API error (status {response.status_code})."

        try:
            return response.json(), None
        except Exception as e:
            return None, f"Invalid JSON from sensor '{sensor_name}': {e}"

    # -------------------------
    # Public API
    # -------------------------
    async def get_current_weather_forecast_async(self) -> str:
        """
        Asynchronously fetch and return a combined weather payload as a JSON string.
        The payload includes current readings, ranges, and hourly/daily forecasts.

        Returns:
            JSON string (on error returns {"error": "..."} as JSON string).
        """
        v = self.valves

        # Validate basic config
        if not v.HA_URL:
            return json.dumps({"error": "HA_URL is not set."})
        if not v.HA_API_TOKEN:
            return json.dumps({"error": "HA_API_TOKEN is not set."})

        headers = self._build_headers()

        # Sensors we expect to query
        sensor_names = {
            "hourly_forecast": v.HA_HOURLY_FORECAST_SENSOR_NAME,
            "daily_forecast": v.HA_DAILY_FORECAST_SENSOR_NAME,
            "current": v.HA_CURRENT_SENSOR_NAME,
            "current_range": v.HA_RANGE_SENSOR_NAME,
            "current_date_time": v.HA_CURRENT_DATE_TIME_SENSOR_NAME,
        }

        # Ensure all sensor names configured
        missing = [k for k, name in sensor_names.items() if not name]
        if missing:
            return json.dumps({"error": f"Sensor name(s) not set for: {', '.join(missing)}"})

        # Build tasks preserving key order for mapping results
        keys = []
        tasks = []
        for key, name in sensor_names.items():
            keys.append(key)
            tasks.append(self._fetch_sensor_data_async(self._get_sensor_url(name), headers, name))

        # Run tasks concurrently
        results = await asyncio.gather(*tasks)

        # Map results into a dict keyed by sensor role
        data: Dict[str, Any] = {}
        for key, (d, err) in zip(keys, results):
            if err:
                logger.error("Error fetching %s: %s", key, err)
                return json.dumps({"error": err})
            data[key] = d

        # Extract attributes safely
        try:
            hourly_forecast = (data["hourly_forecast"].get("attributes", {}) or {}).get("forecast", [])
            daily_forecast = (data["daily_forecast"].get("attributes", {}) or {}).get("forecast", [])
            current = (data["current"].get("attributes", {}) or {})
            current_range = (data["current_range"].get("attributes", {}) or {})
            current_date_time_str = data["current_date_time"].get("state")
        except Exception as e:
            logger.exception("Error extracting attributes")
            return json.dumps({"error": f"Error extracting attributes: {str(e)}"})

        # Parse current datetime robustly and attach timezone
        current_date_time = current_date_time_str
        if current_date_time_str:
            current_date_time = self._parse_datetime(current_date_time_str, v.HA_TIMEZONE)

        # Localize forecast times
        hourly_forecast = self._localize_forecast_times(hourly_forecast, v.HA_TIMEZONE)
        daily_forecast = self._localize_forecast_times(daily_forecast, v.HA_TIMEZONE)

        # Validate forecasts
        if not hourly_forecast:
            return json.dumps({"error": "No hourly forecast data available."})
        if not daily_forecast:
            return json.dumps({"error": "No daily forecast data available."})

        result = {
            "current_date_time": current_date_time,
            "current_timezone": v.HA_TIMEZONE,
            "current_location": v.HA_LOCATION,
            "current_weather": {
                "temperatures": {
                    # Values concatenated with configured temperature unit
                    "current_temperature": self._format_value_with_unit(current.get("temperature"), v.HA_TEMPERATURE_UNIT),
                    "temperature_high": self._format_value_with_unit(current_range.get("max_temperature"), v.HA_TEMPERATURE_UNIT),
                    "temperature_low": self._format_value_with_unit(current_range.get("min_temperature"), v.HA_TEMPERATURE_UNIT),
                },
                "humidities": {
                    # Values concatenated with configured humidity unit
                    "humidity": self._format_value_with_unit(current.get("humidity"), v.HA_HUMIDITY_UNIT),
                    "humidity_high": self._format_value_with_unit(current_range.get("max_humidity"), v.HA_HUMIDITY_UNIT),
                    "humidity_low": self._format_value_with_unit(current_range.get("min_humidity"), v.HA_HUMIDITY_UNIT),
                },
                "pressures": {
                    # Values concatenated with configured pressure unit
                    "pressure": self._format_value_with_unit(current.get("pressure"), v.HA_PRESSURE_UNIT),
                    "pressure_high": self._format_value_with_unit(current_range.get("max_pressure"), v.HA_PRESSURE_UNIT),
                    "pressure_low": self._format_value_with_unit(current_range.get("min_pressure"), v.HA_PRESSURE_UNIT),
                },
                "lux": current.get("lx"),
            },
            "weather_forecasts": {
                "hourly_forecast": hourly_forecast,
                "daily_forecast": daily_forecast,
            },
        }

        # Compact JSON string output
        return json.dumps(result, separators=(",", ":"), ensure_ascii=True)