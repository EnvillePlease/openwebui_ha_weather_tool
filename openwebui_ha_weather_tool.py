import os
import requests
import json
from pydantic import BaseModel, Field


class Tools:
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

    # Get the current forecast from home assistant.
    def get_current_weather_forecast(self) -> str:
        """
        Get the current weather forecast from home assistant.
        """

        # Ensure the valves are initialized
        HA_URL = self.valves.HA_URL
        HA_API_TOKEN = self.valves.HA_API_TOKEN
        HA_HOURLY_FORECAST_SENSOR_NAME = self.valves.HA_HOURLY_FORECAST_SENSOR_NAME
        HA_DAILY_FORECAST_SENSOR_NAME = self.valves.HA_DAILY_FORECAST_SENSOR_NAME
        HA_CURRENT_SENSOR_NAME = self.valves.HA_CURRENT_SENSOR_NAME
        HA_RANGE_SENSOR_NAME = self.valves.HA_RANGE_SENSOR_NAME

        try:
            # Fetch forecast data from Home Assistant
            headers = {"Authorization": f"Bearer {HA_API_TOKEN}"}
            hourly_forecast_url = (
                f"{HA_URL}/api/states/{HA_HOURLY_FORECAST_SENSOR_NAME}"
            )
            daily_forecast_url = f"{HA_URL}/api/states/{HA_DAILY_FORECAST_SENSOR_NAME}"
            current_url = f"{HA_URL}/api/states/{HA_CURRENT_SENSOR_NAME}"
            current_range_url = f"{HA_URL}/api/states/{HA_RANGE_SENSOR_NAME}"

            # Make requests to the Home Assistant API for all current and forecast data, 
            # if you're forking this code you'll need to ensure that the attribute names are correct.
            response = requests.get(hourly_forecast_url, headers=headers)
            hourly_forecast_data = response.json()

            response = requests.get(daily_forecast_url, headers=headers)
            daily_forecast_data = response.json()

            response = requests.get(current_url, headers=headers)
            current_data = response.json()

            response = requests.get(current_range_url, headers=headers)
            current_range_data = response.json()

            hourly_forecast = hourly_forecast_data["attributes"]["forecast"]
            daily_forecast = daily_forecast_data["attributes"]["forecast"]
            current = current_data["attributes"]
            current_range = current_range_data["attributes"]

            # Check if forecast data is available
            if not hourly_forecast:
                return json.dumps({"error": "No forecast data available."})

            # Prepare the result, this will need to be adapted to suit the weather data collected by your 
            # Home Assistant instance.
            result = {
                "current_weather": {
                    "temperature": current.get("temperature"),
                    "humidity": current.get("humidity"),
                    "pressure": current.get("pressure"),
                    "lux": current.get("lx"),
                    "current_weather_ranges": {
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
                "forecast": {
                    "hourly_forecast": hourly_forecast,
                    "daily_forecast": daily_forecast,
                },
            }

            # Return the forecast data as a JSON string
            return json.dumps(json.dumps(result))
        except requests.RequestException as e:  # Handle network-related errors
            return json.dumps({"error": f"Error fetching weather data: {str(e)}"})