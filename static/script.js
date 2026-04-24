/**
 * Weather Application - Frontend Script
 * Handles form submission, fetches weather data from backend API,
 * and updates the DOM with current weather information.
 */

'use strict';

// DOM element references
const weatherForm = document.getElementById('weather-form');
const cityInput = document.getElementById('city-input');
const weatherContainer = document.getElementById('weather-container');
const errorContainer = document.getElementById('error-container');
const loadingIndicator = document.getElementById('loading-indicator');

// Weather display elements
const cityName = document.getElementById('city-name');
const temperature = document.getElementById('temperature');
const weatherDescription = document.getElementById('weather-description');
const humidity = document.getElementById('humidity');
const windSpeed = document.getElementById('wind-speed');
const weatherIcon = document.getElementById('weather-icon');
const feelsLike = document.getElementById('feels-like');
const pressure = document.getElementById('pressure');
const visibility = document.getElementById('visibility');
const sunrise = document.getElementById('sunrise');
const sunset = document.getElementById('sunset');

/**
 * Initialize the application
 * Sets up event listeners and initial state
 */
function init() {
    if (!weatherForm) {
        console.error('Weather form element not found');
        return;
    }

    weatherForm.addEventListener('submit', handleFormSubmit);
    
    // Hide weather container and error container initially
    if (weatherContainer) weatherContainer.style.display = 'none';
    if (errorContainer) errorContainer.style.display = 'none';
    if (loadingIndicator) loadingIndicator.style.display = 'none';
    
    // Check for saved city in localStorage
    const savedCity = localStorage.getItem('lastCity');
    if (savedCity && cityInput) {
        cityInput.value = savedCity;
        fetchWeatherData(savedCity);
    }
}

/**
 * Handle form submission event
 * @param {Event} event - The form submission event
 */
async function handleFormSubmit(event) {
    event.preventDefault();
    
    const city = cityInput.value.trim();
    
    if (!city) {
        showError('Please enter a city name');
        return;
    }
    
    // Save city to localStorage
    localStorage.setItem('lastCity', city);
    
    await fetchWeatherData(city);
}

/**
 * Fetch weather data from backend API
 * @param {string} city - The city name to fetch weather for
 */
async function fetchWeatherData(city) {
    showLoading(true);
    hideError();
    hideWeather();
    
    try {
        const response = await fetch(`/api/weather?city=${encodeURIComponent(city)}`);
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => null);
            throw new Error(errorData?.error || `HTTP error! status: ${response.status}`);
        }
        
        const weatherData = await response.json();
        displayWeatherData(weatherData);
        
    } catch (error) {
        console.error('Error fetching weather data:', error);
        showError(error.message || 'Failed to fetch weather data. Please try again.');
    } finally {
        showLoading(false);
    }
}

/**
 * Display weather data in the DOM
 * @param {Object} data - The weather data object from the API
 */
function displayWeatherData(data) {
    if (!data) {
        showError('No weather data received');
        return;
    }
    
    try {
        // Update city name
        if (cityName) cityName.textContent = `${data.name}, ${data.sys?.country || ''}`;
        
        // Update temperature
        if (temperature) temperature.textContent = `${Math.round(data.main?.temp || 0)}°C`;
        
        // Update weather description
        if (weatherDescription) {
            weatherDescription.textContent = data.weather?.[0]?.description 
                ? data.weather[0].description.charAt(0).toUpperCase() + data.weather[0].description.slice(1)
                : 'N/A';
        }
        
        // Update weather icon
        if (weatherIcon && data.weather?.[0]?.icon) {
            weatherIcon.src = `https://openweathermap.org/img/wn/${data.weather[0].icon}@2x.png`;
            weatherIcon.alt = data.weather[0].description || 'Weather icon';
        }
        
        // Update additional weather details
        if (humidity) humidity.textContent = `${data.main?.humidity || 'N/A'}%`;
        if (windSpeed) windSpeed.textContent = `${data.wind?.speed || 'N/A'} m/s`;
        if (feelsLike) feelsLike.textContent = `${Math.round(data.main?.feels_like || 0)}°C`;
        if (pressure) pressure.textContent = `${data.main?.pressure || 'N/A'} hPa`;
        if (visibility) visibility.textContent = `${(data.visibility || 0) / 1000} km`;
        
        // Format and display sunrise/sunset times
        if (sunrise && data.sys?.sunrise) {
            sunrise.textContent = formatUnixTimestamp(data.sys.sunrise);
        }
        if (sunset && data.sys?.sunset) {
            sunset.textContent = formatUnixTimestamp(data.sys.sunset);
        }
        
        // Show the weather container
        showWeather();
        
    } catch (error) {
        console.error('Error displaying weather data:', error);
        showError('Error displaying weather data');
    }
}

/**
 * Format a Unix timestamp to readable time string
 * @param {number} timestamp - Unix timestamp in seconds
 * @returns {string} Formatted time string
 */
function formatUnixTimestamp(timestamp) {
    const date = new Date(timestamp * 1000);
    return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: true
    });
}

/**
 * Show the weather container
 */
function showWeather() {
    if (weatherContainer) {
        weatherContainer.style.display = 'block';
        weatherContainer.classList.add('fade-in');
    }
}

/**
 * Hide the weather container
 */
function hideWeather() {
    if (weatherContainer) {
        weatherContainer.style.display = 'none';
        weatherContainer.classList.remove('fade-in');
    }
}

/**
 * Show an error message to the user
 * @param {string} message - The error message to display
 */
function showError(message) {
    if (errorContainer) {
        errorContainer.textContent = message;
        errorContainer.style.display = 'block';
        errorContainer.classList.add('fade-in');
    }
}

/**
 * Hide the error container
 */
function hideError() {
    if (errorContainer) {
        errorContainer.style.display = 'none';
        errorContainer.classList.remove('fade-in');
    }
}

/**
 * Show or hide the loading indicator
 * @param {boolean} isLoading - Whether to show loading state
 */
function showLoading(isLoading) {
    if (loadingIndicator) {
        loadingIndicator.style.display = isLoading ? 'block' : 'none';
    }
    
    // Disable/enable form elements during loading
    if (cityInput) cityInput.disabled = isLoading;
    const submitButton = weatherForm?.querySelector('button[type="submit"]');
    if (submitButton) submitButton.disabled = isLoading;
}

/**
 * Debounce function to limit API calls
 * @param {Function} func - The function to debounce
 * @param {number} wait - Milliseconds to wait
 * @returns {Function} Debounced function
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Add input event listener with debounce for auto-search
if (cityInput) {
    const debouncedSearch = debounce((event) => {
        const city = event.target.value.trim();
        if (city.length >= 3) {
            localStorage.setItem('lastCity', city);
            fetchWeatherData(city);
        }
    }, 1000);
    
    cityInput.addEventListener('input', debouncedSearch);
}

// Initialize the application when DOM is ready
document.addEventListener('DOMContentLoaded', init);

// Export functions for testing (if using modules)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        init,
        handleFormSubmit,
        fetchWeatherData,
        displayWeatherData,
        formatUnixTimestamp,
        showError,
        hideError,
        showLoading,
        debounce
    };
}