#!/usr/bin/env python3
"""
NWS + wttr.in Weather Alert Monitor
Dual-channel monitoring:
1. NWS API - Severe weather alerts
2. wttr.in - Any precipitation (rain/snow), extreme temps, high wind
"""

import json
import os
import time
import hashlib
import urllib.request
from datetime import datetime

# Configuration
USER_LOCATION = "Trenton+NJ"

# Zone IDs for NY/NJ area
ZONE_IDS = [
    "NJZ015",  # Mercer County (Trenton - user home)
    "NJZ006",  # Sussex
    "NJZ007",  # Warren  
    "NJZ008",  # Morris
    "NJZ012",  # Middlesex
    "NJZ013",  # Western Monmouth
    "NYZ072",  # NYC
]

# NWS Alert types to filter
SEVERE_EVENTS = [
    # Winter Weather
    "Blizzard Warning", "Winter Storm Warning", "Winter Storm Watch",
    "Winter Storm Advisory", "Ice Storm Warning", "Ice Storm Advisory",
    "Snow Squall Warning", "Snow Squall Watch", "Heavy Snow Warning",
    "Heavy Snow Advisory", "Snow Advisory", "Freezing Rain Advisory",
    "Freezing Drizzle Advisory", "Sleet Warning", "Sleet Advisory",
    "Wind Chill Warning", "Wind Chill Advisory", "Cold Weather Advisory",
    "Extreme Cold Warning", "Hard Freeze Warning", "Freeze Warning", "Frost Advisory",
    # Thunderstorms
    "Severe Thunderstorm Warning", "Severe Thunderstorm Watch",
    "Severe Thunderstorm Advisory", "Flash Flood Warning", "Flash Flood Watch",
    "Flash Flood Advisory", "Flood Warning", "Flood Watch", "Flood Advisory",
    "Urban Flood Advisory", "Small Stream Flood Advisory",
    # Coastal
    "Coastal Flood Warning", "Coastal Flood Watch", "Coastal Flood Advisory",
    "Storm Surge Warning", "Storm Surge Watch", "High Surf Warning", "High Surf Advisory",
    "Rip Current Statement",
    # Wind
    "High Wind Warning", "High Wind Watch", "High Wind Advisory",
    "Wind Advisory", "Gusty Wind Warning",
    # Heat
    "Heat Warning", "Excessive Heat Warning", "Heat Advisory", "Excessive Heat Watch",
    # Other
    "Tornado Warning", "Tornado Watch", "Tornado Advisory",
    "Special Weather Statement", "Hazardous Weather Outlook",
    "Air Quality Alert", "Red Flag Warning", "Fire Weather Watch",
    "Dense Fog Advisory", "Dense Smoke Advisory",
]

# Temperature thresholds (Fahrenheit)
TEMP_HOT_THRESHOLD = 95
TEMP_COLD_THRESHOLD = 25
WIND_THRESHOLD = 25  # mph

def get_nws_alerts():
    """Fetch severe weather alerts from NWS API"""
    all_alerts = []
    for zone_id in ZONE_IDS:
        url = f"https://api.weather.gov/alerts/active?zone={zone_id}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "OpenClaw-Weather-Alert/1.0"})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
        except Exception as e:
            print(f"Error fetching NWS {zone_id}: {e}")
            continue
            
        if not data or "features" not in data:
            continue
            
        for feature in data.get("features", []):
            props = feature.get("properties", {})
            event = props.get("event", "")
            
            if any(sev in event for sev in SEVERE_EVENTS):
                alert_info = {
                    "source": "NWS",
                    "zone": zone_id,
                    "event": event,
                    "severity": props.get("severity", ""),
                    "headline": props.get("headline", ""),
                    "effective": props.get("effective", ""),
                    "expires": props.get("expires", ""),
                }
                alert_hash = hashlib.md5(
                    f"{zone_id}{event}{props.get('sent', '')}".encode()
                ).hexdigest()
                alert_info["hash"] = alert_hash
                all_alerts.append(alert_info)
    
    return all_alerts

def get_wttr_weather():
    """Fetch weather from wttr.in"""
    try:
        url = f"https://wttr.in/{USER_LOCATION}?format=j1"
        req = urllib.request.Request(url, headers={"User-Agent": "OpenClaw-Weather-Alert/1.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"Error fetching wttr.in: {e}")
        return None

def check_wttr_alerts():
    """Check wttr.in for precipitation, extreme temps, high wind"""
    alerts = []
    data = get_wttr_weather()
    
    if not data:
        return alerts
    
    try:
        current = data.get("current_condition", [{}])[0]
        
        # Get weather description - these are lists with "value" key
        weatherDesc_list = current.get("weatherDesc", [])
        weatherDesc = weatherDesc_list[0].get("value", "").lower() if weatherDesc_list else ""
        
        weatherCode = str(current.get("weatherCode", "")).lower()
        
        # Temperature
        temp_f = int(current.get("temp_F", 0))
        
        # Wind speed in mph
        wind_mph = int(current.get("windspeedMiles", 0))
        
        # Precipitation
        precip = float(current.get("precipInches", "0"))
        
        # Check for precipitation keywords
        precip_keywords = ["rain", "drizzle", "shower", "thunderstorm", "snow", "sleet", "ice", "hail", "mist", "fog"]
        has_precip = any(kw in weatherDesc for kw in precip_keywords)
        
        # Check for snow-specific keywords
        snow_keywords = ["snow", "sleet", "ice", "blizzard"]
        has_snow = any(kw in weatherDesc for kw in snow_keywords)
        
        # Check for any rain/snow in forecast (next 3 hours)
        weather_data = data.get("weather", [])
        forecast_precip = False
        if weather_data and len(weather_data) > 0:
            hourly_data = weather_data[0].get("hourly", [])[:3]
            for hour in hourly_data:
                hour_desc = hour.get("weatherDesc", [{}])
                if hour_desc:
                    hour_text = hour_desc[0].get("value", "").lower()
                    if any(kw in hour_text for kw in precip_keywords):
                        forecast_precip = True
                        break
        
        # Build alert if conditions met - ANY rain or snow
        if has_precip or has_snow or forecast_precip:
            precip_type = "Snow" if has_snow else "Rain"
            alert_info = {
                "source": "wttr.in",
                "event": f"{precip_type} Expected",
                "severity": "Advisory",
                "description": f"Current: {weatherDesc} ({temp_f}°F). {precip_type} in forecast: {forecast_precip}",
                "wind": f"{wind_mph} mph",
                "hash": "wttr-precip",
            }
            alerts.append(alert_info)
            print(f"  -> Precipitation detected: {weatherDesc}")
        
        # Check extreme temperature
        try:
            feelslike_f = int(current.get("FeelsLikeF", "0"))
        except:
            feelslike_f = temp_f
        
        if temp_f >= TEMP_HOT_THRESHOLD or feelslike_f >= TEMP_HOT_THRESHOLD:
            alert_info = {
                "source": "wttr.in",
                "event": "Extreme Heat",
                "severity": "Warning",
                "description": f"Temperature: {temp_f}°F (feels like {feelslike_f}°F, >= {TEMP_HOT_THRESHOLD}°F)",
                "hash": "wttr-heat",
            }
            alerts.append(alert_info)
            print(f"  -> Extreme heat: {temp_f}°F (feels {feelslike_f}°F)")
        
        if temp_f <= TEMP_COLD_THRESHOLD or feelslike_f <= TEMP_COLD_THRESHOLD:
            alert_info = {
                "source": "wttr.in",
                "event": "Extreme Cold",
                "severity": "Warning",
                "description": f"Temperature: {temp_f}°F (feels like {feelslike_f}°F, <= {TEMP_COLD_THRESHOLD}°F)",
                "hash": "wttr-cold",
            }
            alerts.append(alert_info)
            print(f"  -> Extreme cold: {temp_f}°F (feels {feelslike_f}°F)")
        
        # Check high wind
        if wind_mph >= WIND_THRESHOLD:
            alert_info = {
                "source": "wttr.in",
                "event": "High Wind",
                "severity": "Advisory",
                "description": f"Wind: {wind_mph} mph (>= {WIND_THRESHOLD} mph)",
                "hash": "wttr-wind",
            }
            alerts.append(alert_info)
            print(f"  -> High wind: {wind_mph} mph")
            
    except Exception as e:
        print(f"Error parsing wttr.in data: {e}")
    
    return alerts

def save_alerts(nws_alerts, wttr_alerts):
    """Save alerts to file"""
    if not nws_alerts and not wttr_alerts:
        print("No weather alerts found")
        return
    
    msg = "🌤️ **Weather Alert** 🌤️\n\n"
    
    if nws_alerts:
        msg += "⚠️ **NWS Severe Alerts**\n"
        for alert in nws_alerts:
            msg += f"• **{alert['event']}** ({alert['zone']})\n"
            msg += f"  Severity: {alert['severity']}\n"
            if alert.get('headline'):
                msg += f"  {alert['headline'][:100]}\n"
            msg += "\n"
    
    if wttr_alerts:
        msg += "📡 **Local Weather Alerts (wttr.in)**\n"
        for alert in wttr_alerts:
            msg += f"• **{alert['event']}**\n"
            msg += f"  {alert.get('description', '')}\n"
            msg += "\n"
    
    with open("/tmp/nws-weather-alert.txt", "w") as f:
        f.write(msg)
    
    print(msg)

def main():
    print(f"[{datetime.now()}] Checking weather alerts...")
    
    # Channel 1: NWS severe alerts
    print("  [NWS] Checking severe weather alerts...")
    nws_alerts = get_nws_alerts()
    if nws_alerts:
        print(f"  -> Found {len(nws_alerts)} NWS alerts")
    
    # Channel 2: wttr.in precipitation/temp/wind
    print("  [wttr.in] Checking local weather...")
    wttr_alerts = check_wttr_alerts()
    
    # Save combined alerts
    save_alerts(nws_alerts, wttr_alerts)

if __name__ == "__main__":
    main()
