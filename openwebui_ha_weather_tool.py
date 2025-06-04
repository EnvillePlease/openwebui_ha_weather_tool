import os
import requests
import json
from pydantic import BaseModel, Field

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

    def __init__(self):
        self.valves = self.Valves()
        pass

    def _fetch_sensor_data(self, url, headers, sensor_name):
        """
        Fetch sensor data from Home Assistant API.

        Args:
            url (_type_): URL of the Home Assistant API endpoint for the sensor.
            headers (_type_): Headers for the API request, including authorization.
            sensor_name (_type_): Name of the sensor to fetch data for.

        Returns:
            _type_: _description_
        """
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                return None, f"Sensor '{sensor_name}' not found or API error (status {response.status_code})."
            try:
                return response.json(), None
            except json.JSONDecodeError:
                return None, f"Invalid JSON from sensor '{sensor_name}'."
        except requests.RequestException as e:
            return None, f"Network error fetching '{sensor_name}': {str(e)}"

    def get_current_weather_forecast(self) -> str:
        """
        Get the current weather forecast from home assistant.
        """
        HA_URL = self.valves.HA_URL
        HA_API_TOKEN = self.valves.HA_API_TOKEN
        HA_HOURLY_FORECAST_SENSOR_NAME = self.valves.HA_HOURLY_FORECAST_SENSOR_NAME
        HA_DAILY_FORECAST_SENSOR_NAME = self.valves.HA_DAILY_FORECAST_SENSOR_NAME
        HA_CURRENT_SENSOR_NAME = self.valves.HA_CURRENT_SENSOR_NAME
        HA_RANGE_SENSOR_NAME = self.valves.HA_RANGE_SENSOR_NAME

        headers = {"Authorization": f"Bearer {HA_API_TOKEN}"}

        sensor_urls = {
            "hourly_forecast": (f"{HA_URL}/api/states/{HA_HOURLY_FORECAST_SENSOR_NAME}", HA_HOURLY_FORECAST_SENSOR_NAME),
            "daily_forecast": (f"{HA_URL}/api/states/{HA_DAILY_FORECAST_SENSOR_NAME}", HA_DAILY_FORECAST_SENSOR_NAME),
            "current": (f"{HA_URL}/api/states/{HA_CURRENT_SENSOR_NAME}", HA_CURRENT_SENSOR_NAME),
            "current_range": (f"{HA_URL}/api/states/{HA_RANGE_SENSOR_NAME}", HA_RANGE_SENSOR_NAME),
        }

        data = {}
        for key, (url, name) in sensor_urls.items():
            if not name:
                return json.dumps({"error": f"Sensor name for '{key}' is not set."})
            d, err = self._fetch_sensor_data(url, headers, name)
            if err:
                return json.dumps({"error": err})
            data[key] = d

        try:
            hourly_forecast = data["hourly_forecast"].get("attributes", {}).get("forecast", [])
            daily_forecast = data["daily_forecast"].get("attributes", {}).get("forecast", [])
            current = data["current"].get("attributes", {})
            current_range = data["current_range"].get("attributes", {})
        except Exception as e:
            return json.dumps({"error": f"Error extracting attributes: {str(e)}"})

        if not hourly_forecast:
            return json.dumps({"error": "No hourly forecast data available."})
        if not daily_forecast:
            return json.dumps({"error": "No daily forecast data available."})

        result = {
            "current_weather_readings": {
                "temperature": current.get("temperature"),
                "humidity": current.get("humidity"),
                "pressure": current.get("pressure"),
                "lux": current.get("lx"),
                "current_weather_maximum_minimum_ranges": {
                    "temperature_high": current_range.get("max_temperature"),
                    "temperature_low": current_range.get("min_temperature"),
                    "temperature_average": current_range.get("avg_temperature"),
                    "humidity_high": current_range.get("max_humidity"),
                    "humidity_low": current_range.get("min_humidity"),
                    "humidity_average": current_range.get("avg_humidity"),
                    "pressure_high": current_range.get("max_pressure"),
                    "pressure_low": current_range.get("min_pressure"),
                    "pressure_average": current_range.get("avg_pressure"),
                },
            },
            "weather_forecast": {
                "hourly_weather_forecast": hourly_forecast,
                "daily_weather_forecast": daily_forecast,
            },
        }

        return json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True)