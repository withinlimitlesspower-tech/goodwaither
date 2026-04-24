"""
main.py - FastAPI server for weather application.

This module provides a FastAPI server that acts as a proxy between the frontend
and the OpenWeatherMap API. It handles API key management, request validation,
and error handling.

Endpoints:
    GET /weather/{city}: Fetch current weather for a given city.
    GET /health: Health check endpoint.
"""

import os
import logging
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Weather Application API",
    description="A FastAPI server that fetches weather data from OpenWeatherMap API",
    version="1.0.0",
)

# CORS configuration to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Constants
OPENWEATHERMAP_BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")

if not API_KEY:
    logger.warning("OPENWEATHERMAP_API_KEY not found in environment variables")


class WeatherResponse(BaseModel):
    """Pydantic model for weather API response."""
    city: str = Field(..., description="City name")
    country: str = Field(..., description="Country code")
    temperature: float = Field(..., description="Current temperature in Celsius")
    feels_like: float = Field(..., description="Feels like temperature in Celsius")
    humidity: int = Field(..., description="Humidity percentage")
    pressure: int = Field(..., description="Atmospheric pressure in hPa")
    description: str = Field(..., description="Weather description")
    icon: str = Field(..., description="Weather icon code")
    wind_speed: float = Field(..., description="Wind speed in m/s")
    wind_deg: int = Field(..., description="Wind direction in degrees")
    clouds: int = Field(..., description="Cloudiness percentage")
    visibility: int = Field(..., description="Visibility in meters")
    sunrise: int = Field(..., description="Sunrise timestamp")
    sunset: int = Field(..., description="Sunset timestamp")
    timestamp: int = Field(..., description="Data timestamp")


class ErrorResponse(BaseModel):
    """Pydantic model for error responses."""
    detail: str = Field(..., description="Error message")
    status_code: int = Field(..., description="HTTP status code")


@app.get("/weather/{city}", response_model=WeatherResponse)
async def get_weather(
    city: str,
    units: Optional[str] = Query("metric", description="Units: metric, imperial, or standard"),
) -> WeatherResponse:
    """
    Fetch current weather data for a given city from OpenWeatherMap API.

    Args:
        city: Name of the city to fetch weather for.
        units: Unit system (metric, imperial, standard). Defaults to metric.

    Returns:
        WeatherResponse: Parsed weather data.

    Raises:
        HTTPException: If API key is missing, request fails, or city is not found.
    """
    if not API_KEY:
        logger.error("API key is not configured")
        raise HTTPException(
            status_code=500,
            detail="Weather API key is not configured. Please set OPENWEATHERMAP_API_KEY in .env file.",
        )

    # Validate units parameter
    valid_units = ["metric", "imperial", "standard"]
    if units not in valid_units:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid units '{units}'. Must be one of: {', '.join(valid_units)}",
        )

    params = {
        "q": city,
        "appid": API_KEY,
        "units": units,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            logger.info(f"Fetching weather data for city: {city}")
            response = await client.get(OPENWEATHERMAP_BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()

    except httpx.HTTPStatusError as e:
        status_code = e.response.status_code
        if status_code == 404:
            logger.warning(f"City not found: {city}")
            raise HTTPException(
                status_code=404,
                detail=f"City '{city}' not found. Please check the spelling and try again.",
            )
        elif status_code == 401:
            logger.error("Invalid API key")
            raise HTTPException(
                status_code=500,
                detail="Invalid API key. Please check your OpenWeatherMap API key.",
            )
        else:
            logger.error(f"HTTP error {status_code} for city {city}: {str(e)}")
            raise HTTPException(
                status_code=status_code,
                detail=f"Failed to fetch weather data: {e.response.text}",
            )

    except httpx.RequestError as e:
        logger.error(f"Request error for city {city}: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"Unable to connect to weather service. Please try again later.",
        )

    except Exception as e:
        logger.error(f"Unexpected error for city {city}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred. Please try again later.",
        )

    # Parse and return weather data
    try:
        weather_data = WeatherResponse(
            city=data["name"],
            country=data["sys"]["country"],
            temperature=data["main"]["temp"],
            feels_like=data["main"]["feels_like"],
            humidity=data["main"]["humidity"],
            pressure=data["main"]["pressure"],
            description=data["weather"][0]["description"].capitalize(),
            icon=data["weather"][0]["icon"],
            wind_speed=data["wind"]["speed"],
            wind_deg=data["wind"]["deg"],
            clouds=data["clouds"]["all"],
            visibility=data.get("visibility", 0),
            sunrise=data["sys"]["sunrise"],
            sunset=data["sys"]["sunset"],
            timestamp=data["dt"],
        )
        logger.info(f"Successfully retrieved weather data for {city}")
        return weather_data

    except KeyError as e:
        logger.error(f"Missing expected field in API response: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Unexpected response format from weather service.",
        )


@app.get("/health")
async def health_check():
    """
    Health check endpoint to verify the server is running.

    Returns:
        dict: Status of the server.
    """
    return {
        "status": "healthy",
        "api_key_configured": bool(API_KEY),
        "version": "1.0.0",
    }


@app.get("/")
async def root():
    """
    Root endpoint providing API information.

    Returns:
        dict: API information and available endpoints.
    """
    return {
        "message": "Weather Application API",
        "docs": "/docs",
        "endpoints": {
            "weather": "/weather/{city}",
            "health": "/health",
        },
    }


if __name__ == "__main__":
    import uvicorn

    # Run the FastAPI server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True,
        log_level="info",
    )