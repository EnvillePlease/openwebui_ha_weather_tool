# -----------------------------------------------------------------------------
# Script Name : openwebui_ha_weather_tool.py
# Author      : Clark Nelson
# Company     : CNSoft OnLine
# Version     : 1.0.6
# -----------------------------------------------------------------------------

import os
import requests
import json
import logging
from pydantic import BaseModel, Field
from datetime import datetime
from zoneinfo import ZoneInfo
import httpx
import asyncio

# Open WebUI Home Assistant Weather Tool
class Tools:
    """
    Open WebUI Home Assistant Weather Tool for fetching weather data from Home Assistant.
    """

    class Valves(BaseModel):
        """
        Configuration valves for Open WebUI Home Assistant Weather Tool.
        """

        HA_URL: str = Field(
            default="https://my-home-assistant.local:8123",
            description="URL of the home assistant instance.",
        )
        HA_API_TOKEN: str = Field(
            default="",
            description="Long lived API token to give Open WebUI access to home assistant.",
        )
        HA_HOURLY_FORECAST_SENSOR_NAME: str = Field(
            default="",
            description="Name of the sensor in home assistant that contains the hourly forecast data.",
        )
        HA_DAILY_FORECAST_SENSOR_NAME: str = Field(
            default="",
            description="Name of the sensor in home assistant that contains the daily forecast data.",
        )
        HA_CURRENT_SENSOR_NAME: str = Field(
            default="",
            description="Name of the sensor in home assistant that contains the current weather data.",
        )
        HA_RANGE_SENSOR_NAME: str = Field(
            default="",
            description="Name of the sensor in home assistant that contains the weather ranges data.",
        )
        HA_CURRENT_DATE_TIME_SENSOR_NAME: str = Field(
            default="",
            description="Name of the sensor in home assistant that contains the current date and time.",
        )
        HA_TIMEZONE: str = Field(
            default="Europe/London",
            description="Home Assistant timezone, used for formatting dates and times in the weather data.",
        )
        HA_LOCATION: str = Field(
            default="96 Pooley View, Polesworth, Warwickshire, UK",
            description="Home Assistant location, used for displaying the weather data.",
        )
        
    def __init__(self):
        self.valves = self.Valves()
        pass

    async def _fetch_sensor_data_async(self, url, headers, sensor_name):
        """
        Asynchronously fetch sensor data from Home Assistant API.

        Args:
            url (_type_): URL of the Home Assistant API endpoint for the sensor.
            headers (_type_): Headers for the API request, including authorization.
            sensor_name (_type_): Name of the sensor to fetch data for.

        Returns:
            _type_: _description_
        """
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url, headers=headers)
            if response.status_code != 200:
                return (
                    None,
                    f"Sensor '{sensor_name}' not found or API error (status {response.status_code}).",
                )
            try:
                return response.json(), None
            except Exception:
                return None, f"Invalid JSON from sensor '{sensor_name}'."
        except Exception as e:
            return None, f"Network error fetching '{sensor_name}': {str(e)}"

    def _localize_forecast_times(self, forecast_list, timezone_str):
        """Attach timezone info to all datetime fields in a forecast list."""
        from zoneinfo import ZoneInfo
        from datetime import datetime

        tz = ZoneInfo(timezone_str)
        for entry in forecast_list:
            # Home Assistant usually uses "datetime" or "time" keys
            for key in ["datetime", "time"]:
                if key in entry and isinstance(entry[key], str):
                    dt_str = entry[key].replace(",", "").strip()
                    try:
                        # Try parsing as "YYYY-MM-DD HH:MM" or ISO
                        try:
                            dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
                        except ValueError:
                            dt = datetime.fromisoformat(dt_str)
                        dt = dt.replace(tzinfo=tz)
                        entry[key] = dt.isoformat()
                    except Exception as e:
                        logging.warning(
                            f"Could not parse or encode timezone for forecast {key}: {e}"
                        )
        return forecast_list

    async def get_current_weather_forecast_async(self) -> str:
        """
        Asynchronously get the current weather forecast from home assistant.
        Returns:
            str: JSON string containing the current weather forecast data.
        """
        v = self.valves

        if not v.HA_URL:
            return json.dumps({"error": "HA_URL is not set."})
        if not v.HA_API_TOKEN:
            return json.dumps({"error": "HA_API_TOKEN is not set."})

        headers = {"Authorization": f"Bearer {v.HA_API_TOKEN}"}
        sensor_names = {
            "hourly_forecast": v.HA_HOURLY_FORECAST_SENSOR_NAME,
            "daily_forecast": v.HA_DAILY_FORECAST_SENSOR_NAME,
            "current": v.HA_CURRENT_SENSOR_NAME,
            "current_range": v.HA_RANGE_SENSOR_NAME,
            "current_date_time": v.HA_CURRENT_DATE_TIME_SENSOR_NAME,
        }

        # Build a list of tasks to fetch sensor data asynchronously.
        tasks = []
        for key, name in sensor_names.items():
            if not name:
                return json.dumps({"error": f"Sensor name for '{key}' is not set."})
            url = f"{v.HA_URL}/api/states/{name}"
            tasks.append(self._fetch_sensor_data_async(url, headers, name))

        # Use asyncio.gather to run all tasks concurrently.
        results = await asyncio.gather(*tasks)
        data = {}
        # Enumerate through the results and handle errors.
        for (key, _), (d, err) in zip(sensor_names.items(), results):
            if err:
                logging.error(f"Error fetching {key}: {err}")
                return json.dumps({"error": err})
            data[key] = d

        try:
            # Check if all required keys are present in the data.
            for key in [
                "hourly_forecast",
                "daily_forecast",
                "current",
                "current_range",
                "current_date_time",
            ]:
                if data.get(key) is None:
                    return json.dumps(
                        {"error": f"No data returned for '{key}' sensor."}
                    )

            hourly_forecast = (
                data["hourly_forecast"].get("attributes", {}).get("forecast", [])
            )
            daily_forecast = (
                data["daily_forecast"].get("attributes", {}).get("forecast", [])
            )
            current = data["current"].get("attributes", {})
            current_range = data["current_range"].get("attributes", {})
            current_date_time_str = data["current_date_time"].get("state")

            # --- Robust date parsing and timezone encoding ---
            current_date_time = current_date_time_str  # fallback
            if current_date_time_str:
                try:
                    # Remove comma and extra spaces
                    dt_str = current_date_time_str.replace(",", "").strip()
                    # Try parsing as "YYYY-MM-DD HH:MM"
                    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
                    # Attach timezone
                    dt = dt.replace(tzinfo=ZoneInfo(v.HA_TIMEZONE))
                    current_date_time = dt.isoformat()
                except Exception as e:
                    logging.warning(
                        f"Could not parse or encode timezone for current_date_time: {e}"
                    )
                    current_date_time = current_date_time_str
            # --- end robust date parsing ---

            # Localize forecast datetimes
            hourly_forecast = self._localize_forecast_times(
                hourly_forecast, v.HA_TIMEZONE
            )
            daily_forecast = self._localize_forecast_times(
                daily_forecast, v.HA_TIMEZONE
            )

        except Exception as e:  # Catch any exception during attribute extraction
            logging.exception("Error extracting attributes")
            return json.dumps({"error": f"Error extracting attributes: {str(e)}"})

        # Validate the structure of the forecast data
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
                    "temperature": current.get("temperature"),
                    "temperature_high": current_range.get("max_temperature"),
                    "temperature_low": current_range.get("min_temperature"),
                },
                "humidities": {
                    "humidity": current.get("humidity"),
                    "humidity_high": current_range.get("max_humidity"),
                    "humidity_low": current_range.get("min_humidity"),
                },
                "pressures": {
                    "pressure": current.get("pressure"),
                    "pressure_high": current_range.get("max_pressure"),
                    "pressure_low": current_range.get("min_pressure"),
                },
                "lux": current.get("lx")
            },
            "weather_forecasts": {
                    "hourly_forecast": hourly_forecast,
                    "daily_forecast": daily_forecast,
            },
        }

        return json.dumps(result, indent=None, ensure_ascii=True)