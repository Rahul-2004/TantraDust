from fastapi import FastAPI, HTTPException
import requests

app = FastAPI(
    title="Dust Deposition Estimator",
    description="Estimates dust deposition on a solar panel and calculates the estimated drop in power output based on air quality and weather data.",
    version="1.0"
)

# --- Embedded Parameters ---
API_KEY = "771f03fb332a8c7f37c1cb21f66a4be0"  # Your OpenWeatherMap API key
HOURS = 168              # Time period in hours (168 hours = 1 week)
DEP_VELOCITY = 0.005     # Deposition velocity in m/s
PANEL_AREA = 1.6         # Solar panel area in m²
LOSS_COEFFICIENT = 0.001 # Loss coefficient (0.001 means 0.1% power drop per mg/m² of dust)
PANEL_POWER = 300        # Nominal power of the solar panel in Watts
# ----------------------------

def fetch_air_quality(lat: float, lon: float) -> float:
    """
    Fetch current air quality data from OpenWeatherMap for the given coordinates.
    Returns the PM2.5 concentration in µg/m³.
    """
    url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={API_KEY}"
    response = requests.get(url)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=f"Error fetching air quality data: {response.text}")
    
    data = response.json()
    try:
        # Extract PM2.5 concentration from the response data.
        pm25 = data["list"][0]["components"]["pm2_5"]
        return pm25
    except (KeyError, IndexError) as e:
        raise HTTPException(status_code=500, detail="Error parsing air quality data")

@app.get("/deposit")
def calculate_deposition(lat: float, lon: float):
    """
    Estimate dust deposition on a solar panel and the associated power loss.

    Query Parameters:
    - **lat**: Latitude of the location.
    - **lon**: Longitude of the location.

    Returns a JSON response with:
    - PM2.5 concentration (µg/m³)
    - Deposition flux (µg/m²·s)
    - Deposited mass per unit area (µg/m² and mg/m²)
    - Total dust deposited on the panel (mg)
    - Estimated percentage drop in potential power output (%)
    - Estimated absolute drop in power (W)
    """
    # Fetch PM2.5 concentration from the air quality API.
    pm25 = fetch_air_quality(lat, lon)
    
    # Calculate deposition flux (Flux = concentration * deposition velocity)
    flux = pm25 * DEP_VELOCITY  # in µg/m²·s

    # Total deposition time in seconds (convert HOURS to seconds)
    total_time_seconds = HOURS * 3600

    # Deposited mass per unit area (in µg/m²)
    mass_per_area_ug = flux * total_time_seconds

    # Convert deposited mass to mg/m²
    mass_per_area_mg = mass_per_area_ug / 1000.0

    # Total dust deposited on the solar panel (mg)
    total_dust_mg = mass_per_area_mg * PANEL_AREA

    # Estimate power loss:
    # Assume a linear relationship: percentage drop (%) = (deposited mass in mg/m²) * (loss coefficient) * 100
    estimated_power_drop_percent = mass_per_area_mg * LOSS_COEFFICIENT * 100

    # Calculate absolute power drop (W)
    absolute_power_drop = PANEL_POWER * (estimated_power_drop_percent / 100.0)

    return {
        "pm2_5_ug_per_m3": pm25,
        "deposition_flux_ug_per_m2_s": round(flux, 4),
        "deposited_mass_per_area_ug_per_m2": round(mass_per_area_ug, 2),
        "deposited_mass_per_area_mg_per_m2": round(mass_per_area_mg, 2),
        "total_dust_deposited_mg": round(total_dust_mg, 2),
        "estimated_power_drop_percent": round(estimated_power_drop_percent, 2),
        "absolute_power_drop_watts": round(absolute_power_drop, 2)
    }
