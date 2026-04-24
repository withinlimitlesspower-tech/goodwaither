"""
weather_service.py - Service module for OpenWeatherMap API integration.

This module provides a clean interface for fetching and parsing weather data
from the OpenWeatherMap API. It handles API calls, response parsing, error
handling, and data validation.
"""

import os
import logging
from typing import Dict, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError

# Configure logging
logger = logging.getLogger(__name__)

# Constants
DEFAULT_TIMEOUT = 10  # seconds
API_BASE_URL = "https://api.openweathermap.org/data/2.5"
API_KEY_ENV_VAR = "OPENWEATHERMAP_API_KEY"


@dataclass
class WeatherData:
    """Data class representing parsed weather information."""
    temperature: float
    feels_like: float
    temp_min: float
    temp_max: float
    humidity: int
    pressure: int
    description: str
    icon: str
    wind_speed: float
    wind_deg: int
    clouds: int
    visibility: int
    city_name: str
    country: str
    timestamp: datetime
    sunrise: datetime
    sunset: datetime
    weather_id: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert WeatherData to a dictionary with serializable values."""
        data = asdict(self)
        # Convert datetime objects to ISO format strings
        for key in ['timestamp', 'sunrise', 'sunset']:
            if isinstance(data[key], datetime):
                data[key] = data[key].isoformat()
        return data


class WeatherServiceError(Exception):
    """Base exception for weather service errors."""
    pass


class APIKeyError(WeatherServiceError):
    """Raised when API key is missing or invalid."""
    pass


class CityNotFoundError(WeatherServiceError):
    """Raised when the specified city is not found."""
    pass


class RateLimitError(WeatherServiceError):
    """Raised when API rate limit is exceeded."""
    pass


class WeatherService:
    """
    Service class for interacting with the OpenWeatherMap API.

    This class handles all API communication, response parsing, and error
    handling for weather data retrieval.

    Attributes:
        api_key (str): The OpenWeatherMap API key.
        timeout (int): Request timeout in seconds.
        base_url (str): Base URL for the API.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT
    ) -> None:
        """
        Initialize the WeatherService.

        Args:
            api_key: OpenWeatherMap API key. If None, reads from environment.
            timeout: Request timeout in seconds.

        Raises:
            APIKeyError: If no API key is provided or found in environment.
        """
        self.api_key = api_key or os.environ.get(API_KEY_ENV_VAR)
        if not self.api_key:
            raise APIKeyError(
                f"API key not provided. Set {API_KEY_ENV_VAR} environment "
                f"variable or pass api_key parameter."
            )
        self.timeout = timeout
        self.base_url = API_BASE_URL
        self._session = requests.Session()
        logger.info("WeatherService initialized successfully")

    def get_current_weather(
        self,
        city: str,
        units: str = "metric"
    ) -> WeatherData:
        """
        Fetch current weather data for a specified city.

        Args:
            city: City name (e.g., "London", "New York,US").
            units: Unit system ('metric' for Celsius, 'imperial' for Fahrenheit,
                   'standard' for Kelvin).

        Returns:
            WeatherData object containing parsed weather information.

        Raises:
            CityNotFoundError: If the city is not found.
            RateLimitError: If API rate limit is exceeded.
            WeatherServiceError: For other API or network errors.
        """
        try:
            logger.info(f"Fetching weather for city: {city} (units: {units})")
            
            params = {
                "q": city,
                "appid": self.api_key,
                "units": units,
            }
            
            response = self._make_request("/weather", params)
            weather_data = self._parse_weather_response(response)
            
            logger.info(f"Successfully retrieved weather data for {city}")
            return weather_data
            
        except requests.HTTPError as e:
            status_code = e.response.status_code if e.response else 0
            if status_code == 404:
                raise CityNotFoundError(f"City '{city}' not found") from e
            elif status_code == 401:
                raise APIKeyError("Invalid API key") from e
            elif status_code == 429:
                raise RateLimitError("API rate limit exceeded") from e
            else:
                raise WeatherServiceError(
                    f"HTTP error {status_code}: {str(e)}"
                ) from e
        except (ConnectionError, Timeout) as e:
            raise WeatherServiceError(
                f"Network error: Unable to connect to weather service: {str(e)}"
            ) from e
        except RequestException as e:
            raise WeatherServiceError(
                f"Request failed: {str(e)}"
            ) from e

    def get_current_weather_by_coords(
        self,
        lat: float,
        lon: float,
        units: str = "metric"
    ) -> WeatherData:
        """
        Fetch current weather data by geographic coordinates.

        Args:
            lat: Latitude (decimal degrees).
            lon: Longitude (decimal degrees).
            units: Unit system ('metric', 'imperial', 'standard').

        Returns:
            WeatherData object containing parsed weather information.

        Raises:
            WeatherServiceError: For API or network errors.
        """
        try:
            logger.info(
                f"Fetching weather for coordinates: ({lat}, {lon}) "
                f"(units: {units})"
            )
            
            params = {
                "lat": lat,
                "lon": lon,
                "appid": self.api_key,
                "units": units,
            }
            
            response = self._make_request("/weather", params)
            weather_data = self._parse_weather_response(response)
            
            logger.info(
                f"Successfully retrieved weather data for coordinates "
                f"({lat}, {lon})"
            )
            return weather_data
            
        except requests.HTTPError as e:
            status_code = e.response.status_code if e.response else 0
            if status_code == 401:
                raise APIKeyError("Invalid API key") from e
            elif status_code == 429:
                raise RateLimitError("API rate limit exceeded") from e
            else:
                raise WeatherServiceError(
                    f"HTTP error {status_code}: {str(e)}"
                ) from e
        except (ConnectionError, Timeout) as e:
            raise WeatherServiceError(
                f"Network error: Unable to connect to weather service: {str(e)}"
            ) from e
        except RequestException as e:
            raise WeatherServiceError(
                f"Request failed: {str(e)}"
            ) from e

    def _make_request(
        self,
        endpoint: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Make an HTTP request to the OpenWeatherMap API.

        Args:
            endpoint: API endpoint path (e.g., '/weather').
            params: Query parameters for the request.

        Returns:
            Parsed JSON response as a dictionary.

        Raises:
            RequestException: For HTTP or network errors.
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self._session.get(
                url,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
            
        except RequestException:
            logger.error(
                f"Request failed for endpoint {endpoint} with params {params}"
            )
            raise

    def _parse_weather_response(
        self,
        response: Dict[str, Any]
    ) -> WeatherData:
        """
        Parse the API response into a WeatherData object.

        Args:
            response: Raw API response dictionary.

        Returns:
            WeatherData object with parsed and validated data.

        Raises:
            WeatherServiceError: If response data is invalid or missing.
        """
        try:
            # Validate required fields exist
            if not response.get("main"):
                raise WeatherServiceError("Missing 'main' data in response")
            if not response.get("weather"):
                raise WeatherServiceError("Missing 'weather' data in response")
            
            # Extract weather details
            main_data = response["main"]
            weather_info = response["weather"][0]
            wind_data = response.get("wind", {})
            clouds_data = response.get("clouds", {})
            sys_data = response.get("sys", {})
            
            # Parse timestamps
            timestamp = datetime.fromtimestamp(
                response.get("dt", 0),
                tz=timezone.utc
            )
            sunrise = datetime.fromtimestamp(
                sys_data.get("sunrise", 0),
                tz=timezone.utc
            )
            sunset = datetime.fromtimestamp(
                sys_data.get("sunset", 0),
                tz=timezone.utc
            )
            
            # Create WeatherData instance
            weather_data = WeatherData(
                temperature=main_data.get("temp", 0.0),
                feels_like=main_data.get("feels_like", 0.0),
                temp_min=main_data.get("temp_min", 0.0),
                temp_max=main_data.get("temp_max", 0.0),
                humidity=main_data.get("humidity", 0),
                pressure=main_data.get("pressure", 0),
                description=weather_info.get("description", ""),
                icon=weather_info.get("icon", ""),
                wind_speed=wind_data.get("speed", 0.0),
                wind_deg=wind_data.get("deg", 0),
                clouds=clouds_data.get("all", 0),
                visibility=response.get("visibility", 0),
                city_name=response.get("name", ""),
                country=sys_data.get("country", ""),
                timestamp=timestamp,
                sunrise=sunrise,
                sunset=sunset,
                weather_id=weather_info.get("id", 0)
            )
            
            return weather_data
            
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Failed to parse weather response: {str(e)}")
            raise WeatherServiceError(
                f"Failed to parse weather data: {str(e)}"
            ) from e

    def close(self) -> None:
        """Close the HTTP session."""
        self._session.close()
        logger.debug("WeatherService session closed")

    def __enter__(self) -> 'WeatherService':
        """Context manager entry."""
        return self

    def __exit__(self, *args) -> None:
        """Context manager exit with cleanup."""
        self.close()


# Convenience function for quick weather lookup
def get_weather(
    city: str,
    api_key: Optional[str] = None,
    units: str = "metric"
) -> Dict[str, Any]:
    """
    Convenience function to quickly get weather data for a city.

    This function creates a temporary WeatherService instance and returns
    the weather data as a dictionary.

    Args:
        city: City name.
        api_key: OpenWeatherMap API key (optional, reads from env if not provided).
        units: Unit system ('metric', 'imperial', 'standard').

    Returns:
        Dictionary containing weather data.

    Raises:
        Various WeatherServiceError subclasses for different error conditions.
    """
    with WeatherService(api_key=api_key) as service:
        weather_data = service.get_current_weather(city, units)
        return weather_data.to_dict()


# Example usage
if __name__ == "__main__":
    # Configure logging for standalone usage
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Example: Get weather for London
        weather = get_weather("London")
        print(f"Weather in {weather['city_name']}, {weather['country']}:")
        print(f"Temperature: {weather['temperature']}°C")
        print(f"Description: {weather['description']}")
        print(f"Humidity: {weather['humidity']}%")
        print(f"Wind Speed: {weather['wind_speed']} m/s")
        
    except APIKeyError as e:
        print(f"API Key Error: {e}")
    except CityNotFoundError as e:
        print(f"City Not Found: {e}")
    except RateLimitError as e:
        print(f"Rate Limit Exceeded: {e}")
    except WeatherServiceError as e:
        print(f"Weather Service Error: {e}")
    except Exception as e:
        print(f"Unexpected Error: {e}")