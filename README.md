# OpenWebUI Home Assistant Weather Tool

This repository provides a Python tool to interface with your [Home Assistant](https://www.home-assistant.io/) instance and fetch current weather conditions, hourly forecasts, and daily forecasts. The tool is designed for easy integration with Open WebUI as a tool, or other Python-based projects that require access to weather data managed by Home Assistant.

## What Does This Code Do?

- **Fetches Weather Data**: Connects to your Home Assistant instance using the REST API to retrieve:
  - Current weather conditions (temperature, humidity, pressure, lux).
  - Hourly weather forecasts.
  - Daily weather forecasts.
  - Daily range statistics (high/low/average for temperature, humidity, pressure).

- **Returns Data as JSON**: All weather data is formatted as JSON for easy parsing and integration into other applications or user interfaces.

- **Simple Configuration**: You can configure the tool by setting the required Home Assistant URL, API token, and sensor names.

## How to Use

1. **Clone or Fork the Repository**
   - You are welcome to fork or clone this repository and use it as you wish!

2. **Install Dependencies**
   - This tool requires Python 3.7+ and the following packages:
     - `requests`
     - `pydantic`

   ```bash
   pip install requests pydantic
   ```

3. **Adapt for Your Home Assistant Instance**
   - You **must** configure the following parameters in the code to match your Home Assistant setup:
     - `HA_URL`: The base URL of your Home Assistant instance (e.g., `https://my-home-assistant.local:8123`).
     - `HA_API_TOKEN`: A long-lived access token from your Home Assistant profile.
     - `HA_HOURLY_FORECAST_SENSOR_NAME`: The sensor name for hourly forecasts.
     - `HA_DAILY_FORECAST_SENSOR_NAME`: The sensor name for daily forecasts.
     - `HA_CURRENT_SENSOR_NAME`: The sensor name for current weather data.
     - `HA_RANGE_SENSOR_NAME`: The sensor name for weather range statistics.

   These can be set by modifying the `Valves` class in `openwebui_ha_weather_tool.py`, or by extending the class to read from environment variables or a configuration file.

4. **Example Usage**

   ```python
   from openwebui_ha_weather_tool import Tools

   tools = Tools()
   tools.valves.HA_URL = "https://my-home-assistant.local:8123"
   tools.valves.HA_API_TOKEN = "your_api_token_here"
   tools.valves.HA_HOURLY_FORECAST_SENSOR_NAME = "sensor.your_hourly_forecast"
   tools.valves.HA_DAILY_FORECAST_SENSOR_NAME = "sensor.your_daily_forecast"
   tools.valves.HA_CURRENT_SENSOR_NAME = "sensor.your_current_weather"
   tools.valves.HA_RANGE_SENSOR_NAME = "sensor.your_range_sensor"

   weather_json = tools.get_hourly_weather_forecast()
   print(weather_json)
   ```

## Notes

- **Customization Required**: You will need to adapt the sensor names to match those used in your own Home Assistant instance. These can be found in your Home Assistant dashboard under Developer Tools > States.
- **API Token Security**: Keep your Home Assistant API token private. Do not commit it to public repositories.

## License & Usage

Feel free to **fork**, modify, and use this code in your own projects. No restrictions are imposed—use it at your leisure!

---

**Happy automating!**
