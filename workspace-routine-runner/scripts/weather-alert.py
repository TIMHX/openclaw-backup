#!/usr/bin/env python3
"""
NWS Weather Alert Monitor for NY/NJ Area
Monitors NWS API for severe weather alerts and notifies via Discord
"""

import json
import os
import time
import hashlib
from datetime import datetime
import urllib.request

# Configuration
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
CHANNEL_ID = "1469849142556627059"

# Zone IDs for NY/NJ area
# NJZ015 = Mercer County (Trenton area - user location)
# NJZ006 = Sussex, NJZ007 = Warren, NJZ008 = Morris
# NYZ072 = NYC
ZONE_IDS = [
    "NJZ015",  # Mercer County (Trenton - user home)
    "NJZ006",  # Sussex
    "NJZ007",  # Warren  
    "NJZ008",  # Morris
    "NJZ012",  # Middlesex
    "NJZ013",  # Western Monmouth
    "NYZ072",  # NYC
]

# Alert types to filter
SEVERE_EVENTS = [
    "Blizzard Warning",
    "Winter Storm Warning",
    "Winter Storm Watch",
    "Ice Storm Warning",
    "Snow Squall Warning",
    "Severe Thunderstorm Warning",
    "Flash Flood Warning",
    "Flood Warning",
    "Coastal Flood Warning",
    "High Wind Warning",
    "Extreme Cold Warning",
    "Heat Advisory",
]

STATE_FILE = "/tmp/nws-alert-hash.txt"

def get_alerts(zone_id):
    """Fetch active alerts for a zone from NWS API"""
    url = f"https://api.weather.gov/alerts/active?zone={zone_id}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "OpenClaw-Weather-Alert/1.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"Error fetching {zone_id}: {e}")
        return None

def check_alerts():
    """Check all zones for severe weather alerts"""
    all_alerts = []
    
    for zone_id in ZONE_IDS:
        data = get_alerts(zone_id)
        if not data or "features" not in data:
            continue
            
        for feature in data.get("features", []):
            props = feature.get("properties", {})
            event = props.get("event", "")
            
            # Filter for severe weather events
            if any(sev in event for sev in SEVERE_EVENTS):
                alert_info = {
                    "zone": zone_id,
                    "event": event,
                    "severity": props.get("severity", ""),
                    "headline": props.get("headline", ""),
                    "description": props.get("description", "")[:500],
                    "instruction": props.get("instruction", "")[:300],
                    "effective": props.get("effective", ""),
                    "expires": props.get("expires", ""),
                    "sender": props.get("senderName", ""),
                }
                # Create unique hash for this alert
                alert_hash = hashlib.md5(
                    f"{zone_id}{event}{props.get('sent', '')}".encode()
                ).hexdigest()
                alert_info["hash"] = alert_hash
                all_alerts.append(alert_info)
    
    return all_alerts

def send_discord_alert(alerts):
    """Send alert to Discord"""
    if not alerts:
        return
        
    # Build message
    msg = "⚠️ **Severe Weather Alert** ⚠️\n\n"
    
    for alert in alerts:
        msg += f"**{alert['event']}** ({alert['zone']})\n"
        msg += f"Severity: {alert['severity']}\n"
        if alert.get('headline'):
            msg += f"{alert['headline'][:200]}\n"
        msg += f"Effective: {alert['effective'][:16]}\n"
        msg += f"Expires: {alert['expires'][:16]}\n"
        msg += "---\n"
    
    # Save to file for OpenClaw to pick up
    alert_file = "/tmp/nws-weather-alert.txt"
    with open(alert_file, "w") as f:
        f.write(msg)
    
    print(msg)

def main():
    """Main loop"""
    print(f"[{datetime.now()}] Checking NWS alerts...")
    
    alerts = check_alerts()
    
    if alerts:
        print(f"Found {len(alerts)} severe weather alerts")
        send_discord_alert(alerts)
    else:
        print("No severe weather alerts found")

if __name__ == "__main__":
    main()
