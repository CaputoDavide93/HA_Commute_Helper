# 🚗 Home Assistant Commute Briefing

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/CaputoDavide93/HA_Commute_Helper?style=for-the-badge)](https://github.com/CaputoDavide93/HA_Commute_Helper/releases)
[![License](https://img.shields.io/github/license/CaputoDavide93/HA_Commute_Helper?style=for-the-badge)](LICENSE)

A **free-first, multi-source** commute briefing integration for Home Assistant that provides smart morning notifications with real-time traffic and bus information.

<p align="center">
  <a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=CaputoDavide93&repository=HA_Commute_Helper&category=integration">
    <img src="https://my.home-assistant.io/badges/hacs_repository.svg" alt="Open your Home Assistant instance and open a repository inside the Home Assistant Community Store." />
  </a>
</p>

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🚗 **Traffic ETA** | Real-time travel time via Waze integration (free, unlimited) |
| 🚌 **Bus Departures** | Live bus times via TransportAPI (free tier: 30 req/day) |
| 🔄 **Smart Fallback** | Automatic scraping fallback when API quota exhausted |
| 📊 **Quota Management** | Intelligent API usage to stay within free limits |
| 📅 **Calendar Integration** | Only notifies on office days based on your calendar |
| 🔔 **Smart Notifications** | Morning briefings with actionable refresh button |
| ⚙️ **Easy Setup** | UI-based configuration - no YAML editing required! |

---

## 📦 Installation

### Method 1: HACS (Recommended)

<p align="center">
  <a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=CaputoDavide93&repository=HA_Commute_Helper&category=integration">
    <img src="https://my.home-assistant.io/badges/hacs_repository.svg" alt="Open your Home Assistant instance and open a repository inside the Home Assistant Community Store." />
  </a>
</p>

**Or manually add to HACS:**

1. Open **HACS** in Home Assistant
2. Click **Integrations** → **⋮** (menu) → **Custom repositories**
3. Add: `https://github.com/CaputoDavide93/HA_Commute_Helper`
4. Select category: **Integration**
5. Click **Add** → Search "Commute Briefing" → **Install**
6. **Restart Home Assistant**

### Method 2: Manual Installation

1. Download the [latest release](https://github.com/CaputoDavide93/HA_Commute_Helper/releases)
2. Extract and copy `custom_components/commute_briefing/` to your HA `config/custom_components/`
3. **Restart Home Assistant**

---

## 🚀 Add Integration to Home Assistant

After installation, add the integration:

<p align="center">
  <a href="https://my.home-assistant.io/redirect/config_flow_start/?domain=commute_briefing">
    <img src="https://my.home-assistant.io/badges/config_flow_start.svg" alt="Open your Home Assistant instance and start setting up a new integration." />
  </a>
</p>

**Or manually:** Go to **Settings** → **Devices & Services** → **Add Integration** → Search "**Commute Briefing**"

---

## 🔧 Prerequisites

### 1. TransportAPI Account (Free)

1. Sign up at [developer.transportapi.com](https://developer.transportapi.com/signup)
2. Create an application to get your **App ID** and **App Key**
3. Free tier: **30 requests/day** (plenty for commute checks!)

### 2. Waze Travel Time Integration

Set up the Waze integration to get traffic data:

<p align="center">
  <a href="https://my.home-assistant.io/redirect/brand/?brand=waze_travel_time">
    <img src="https://my.home-assistant.io/badges/brand.svg" alt="Open your Home Assistant instance and start setting up Waze Travel Time." />
  </a>
</p>

Configure:
- **Origin**: Your home address
- **Destination**: Your work address  
- **Region**: Your region (e.g., EU)

### 3. Scraper Microservice (Optional)

For fallback bus data when API quota is exhausted:

```bash
cd scraper-microservice
docker-compose up -d
```

Verify it's running:
```bash
curl http://localhost:8765/health
```

---

## ⚙️ Configuration Wizard

The integration uses a **4-step setup wizard**:

### Step 1: TransportAPI Credentials

| Field | Description | Example |
|-------|-------------|---------|
| **App ID** | Your TransportAPI application ID | `abc123` |
| **App Key** | Your TransportAPI application key | `xyz789...` |
| **Primary Bus Stop** | ATCO/NaPTAN code for your stop | `6200206710` |
| **Backup Bus Stop** | Optional backup stop code | *(optional)* |
| **Bus Routes Filter** | Comma-separated routes | `43,X43` |

> 💡 **Finding your bus stop code:** Search on [TransportAPI](https://developer.transportapi.com/) or check your local transport authority website.

### Step 2: Commute Settings

| Field | Description | Default |
|-------|-------------|---------|
| **Commute Window Start** | When checks begin | `08:00` |
| **Commute Window End** | When checks end | `09:00` |
| **Baseline Time** | Normal commute (minutes) | `45` |
| **Traffic Delay Threshold** | Minutes delay to trigger alert | `10` |
| **Bus Gap Threshold** | Minutes until bus to trigger alert | `20` |

### Step 3: Integrations

| Field | Description |
|-------|-------------|
| **Waze Entity** | Your Waze Travel Time sensor |
| **Calendar Entity** | Work calendar for office day detection |
| **Notification Service** | e.g., `notify.mobile_app_iphone` |
| **Office Keywords** | Calendar keywords for office days |
| **WFH Keywords** | Calendar keywords for work-from-home |
| **Scraper URL** | Fallback scraper URL |

### Step 4: Quota Management

| Field | Description | Default |
|-------|-------------|---------|
| **Daily Quota** | Total API calls allowed | `30` |
| **Reserved for Manual** | Calls saved for manual refresh | `6` |
| **Max Auto Calls** | Maximum automatic calls/day | `10` |

---

## 📱 Entities Created

After setup, you'll have these entities:

### Sensors

| Entity | Description |
|--------|-------------|
| `sensor.commute_briefing_next_bus_minutes` | Minutes until next bus |
| `sensor.commute_briefing_next_bus_time` | Next bus departure time (HH:MM) |
| `sensor.commute_briefing_next_bus_route` | Next bus route number |
| `sensor.commute_briefing_next_bus_status` | Status: On time / Late / Early |
| `sensor.commute_briefing_traffic_time` | Current traffic time (minutes) |
| `sensor.commute_briefing_traffic_delay` | Delay vs baseline (minutes) |
| `sensor.commute_briefing_bus_data_source` | Data source: TransportAPI / Scraper |
| `sensor.commute_briefing_api_calls_today` | API calls used today |
| `sensor.commute_briefing_auto_api_calls_today` | Automatic API calls today |
| `sensor.commute_briefing_last_check` | Last data refresh timestamp |

### Binary Sensors

| Entity | Description |
|--------|-------------|
| `binary_sensor.commute_briefing_commute_day` | Is today an office day? |
| `binary_sensor.commute_briefing_can_call_api_auto` | Can make automatic API calls? |
| `binary_sensor.commute_briefing_can_call_api_manual` | Can make manual API calls? |
| `binary_sensor.commute_briefing_potential_issue` | Traffic/bus issue detected? |

### Buttons

| Entity | Description |
|--------|-------------|
| `button.commute_briefing_refresh_commute` | Manually refresh all data |
| `button.commute_briefing_send_notification` | Send notification now |
| `button.commute_briefing_reset_counters` | Reset daily API counters |

---

## 🎨 Dashboard Example

Add this card to your Lovelace dashboard:

```yaml
type: vertical-stack
cards:
  - type: entities
    title: 🚗 Commute Briefing
    show_header_toggle: false
    entities:
      - entity: sensor.commute_briefing_traffic_time
        name: Traffic Time
        icon: mdi:car
      - entity: sensor.commute_briefing_traffic_delay
        name: Delay vs Usual
        icon: mdi:clock-alert
      - type: divider
      - entity: sensor.commute_briefing_next_bus_route
        name: Next Bus
        icon: mdi:bus
      - entity: sensor.commute_briefing_next_bus_minutes
        name: Arrives In
        icon: mdi:timer-sand
      - entity: sensor.commute_briefing_next_bus_status
        name: Status
        icon: mdi:information
      - type: divider
      - entity: binary_sensor.commute_briefing_commute_day
        name: Office Day
      - entity: sensor.commute_briefing_api_calls_today
        name: API Calls Today
      - entity: sensor.commute_briefing_bus_data_source
        name: Data Source

  - type: horizontal-stack
    cards:
      - type: button
        entity: button.commute_briefing_refresh_commute
        name: Refresh
        icon: mdi:refresh
        tap_action:
          action: call-service
          service: button.press
          target:
            entity_id: button.commute_briefing_refresh_commute

      - type: button
        entity: button.commute_briefing_send_notification
        name: Notify
        icon: mdi:bell
        tap_action:
          action: call-service
          service: button.press
          target:
            entity_id: button.commute_briefing_send_notification
```

---

## 🔔 Notification Example

When you receive a commute briefing notification:

```
🚗 Commute Briefing

Traffic: 52 min (+7 vs usual)
🚌 Bus: Route 43 in 8 min at 07:38 — On time (TransportAPI)

[Refresh]
```

---

## 📊 How It Works

### Quota Management

The integration intelligently manages your free API quota:

```
Daily Quota (30)
├── Reserved for Manual (6) → Always available for button presses
└── Available for Auto (24)
    └── Max Auto Calls (10) → Limits automatic usage
```

### Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    Commute Check                             │
├─────────────────────────────────────────────────────────────┤
│  1. Check if office day (calendar)                          │
│  2. Get traffic time (Waze - always free)                   │
│  3. Get bus times:                                          │
│     ├── Try TransportAPI (if quota available)               │
│     └── Fallback to Scraper (if API unavailable)            │
│  4. Calculate delays & issues                               │
│  5. Send notification (if configured)                       │
└─────────────────────────────────────────────────────────────┘
```

### Office Day Detection

The integration checks your calendar for keywords:

| Type | Keywords (configurable) | Result |
|------|------------------------|--------|
| **Office** | "Office", "Edinburgh" | ✅ Notifications enabled |
| **WFH** | "WFH", "Home", "Remote" | ❌ Notifications disabled |

---

## 🛠️ Services

| Service | Description |
|---------|-------------|
| `commute_briefing.refresh_commute` | Manually refresh all data |
| `commute_briefing.send_notification` | Send a briefing notification |
| `commute_briefing.reset_counters` | Reset daily API counters |

### Example Automation

```yaml
automation:
  - alias: "Morning Commute Check"
    trigger:
      - platform: time
        at: "07:30:00"
    condition:
      - condition: state
        entity_id: binary_sensor.commute_briefing_commute_day
        state: "on"
    action:
      - service: commute_briefing.refresh_commute
      - delay: "00:00:05"
      - service: commute_briefing.send_notification
```

---

## 🐛 Troubleshooting

### No Bus Data

1. ✅ Verify your ATCO code is correct
2. ✅ Check TransportAPI credentials are valid
3. ✅ Ensure API quota isn't exhausted (check `sensor.commute_briefing_api_calls_today`)
4. ✅ Test scraper: `curl http://localhost:8765/health`

### Notifications Not Sending

1. ✅ Verify notification service name (e.g., `notify.mobile_app_iphone`)
2. ✅ Check `binary_sensor.commute_briefing_commute_day` is "on"
3. ✅ Review Home Assistant logs for errors

### API Quota Exceeded

The integration automatically falls back to scraping. To reduce API usage:
- Lower "Max Auto Calls" in settings
- Increase delay thresholds
- Reduce "Reserved for Manual"

### Integration Not Loading

1. ✅ Check HA logs: **Settings → System → Logs**
2. ✅ Verify files in `custom_components/commute_briefing/`
3. ✅ Restart Home Assistant completely

---

## 📁 Project Structure

```
HA_Commute_Helper/
├── custom_components/
│   └── commute_briefing/
│       ├── __init__.py          # Integration setup
│       ├── manifest.json        # Integration metadata
│       ├── config_flow.py       # UI configuration wizard
│       ├── coordinator.py       # Data fetching & management
│       ├── sensor.py            # Sensor entities
│       ├── binary_sensor.py     # Binary sensor entities
│       ├── button.py            # Button entities
│       ├── const.py             # Constants & defaults
│       ├── services.yaml        # Service definitions
│       ├── hacs.json            # HACS metadata
│       └── translations/
│           └── en.json          # English translations
├── scraper-microservice/
│   ├── app.py                   # FastAPI scraper
│   ├── Dockerfile               # Docker build
│   ├── docker-compose.yml       # Docker Compose
│   └── requirements.txt         # Python dependencies
├── packages/
│   └── commute_briefing.yaml    # Alternative YAML config
└── README.md
```

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [Home Assistant](https://www.home-assistant.io/) - The amazing home automation platform
- [TransportAPI](https://www.transportapi.com/) - UK transport data API
- [Waze](https://www.waze.com/) - Traffic data provider
- [HACS](https://hacs.xyz/) - Home Assistant Community Store

---

<p align="center">
  <strong>If you find this integration useful, please consider giving it a ⭐ star!</strong>
</p>
