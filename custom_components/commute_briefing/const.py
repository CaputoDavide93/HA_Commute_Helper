"""Constants for the Commute Briefing integration."""

DOMAIN = "commute_briefing"

# Configuration keys
CONF_TRANSPORTAPI_APP_ID = "transportapi_app_id"
CONF_TRANSPORTAPI_APP_KEY = "transportapi_app_key"
CONF_BUS_STOP_PRIMARY = "bus_stop_primary"
CONF_BUS_STOP_BACKUP = "bus_stop_backup"
CONF_BUS_ROUTES = "bus_routes"
CONF_COMMUTE_WINDOW_START = "commute_window_start"
CONF_COMMUTE_WINDOW_END = "commute_window_end"
CONF_COMMUTE_BASELINE = "commute_baseline"
CONF_TRAFFIC_DELAY_THRESHOLD = "traffic_delay_threshold"
CONF_BUS_GAP_THRESHOLD = "bus_gap_threshold"
CONF_DAILY_QUOTA = "daily_quota"
CONF_RESERVED_FOR_MANUAL = "reserved_for_manual"
CONF_MAX_AUTO_CALLS = "max_auto_calls"
CONF_NOTIFY_SERVICE = "notify_service"
CONF_CALENDAR_ENTITY = "calendar_entity"
CONF_OFFICE_KEYWORDS = "office_keywords"
CONF_WFH_KEYWORDS = "wfh_keywords"
CONF_WAZE_ENTITY = "waze_entity"
CONF_SCRAPER_URL = "scraper_url"

# Defaults
DEFAULT_COMMUTE_WINDOW_START = "08:00"
DEFAULT_COMMUTE_WINDOW_END = "09:00"
DEFAULT_COMMUTE_BASELINE = 45
DEFAULT_TRAFFIC_DELAY_THRESHOLD = 10
DEFAULT_BUS_GAP_THRESHOLD = 20
DEFAULT_DAILY_QUOTA = 30
DEFAULT_RESERVED_FOR_MANUAL = 6
DEFAULT_MAX_AUTO_CALLS = 10
DEFAULT_OFFICE_KEYWORDS = "Office,Edinburgh"
DEFAULT_WFH_KEYWORDS = "WFH,Home,Remote"
DEFAULT_SCRAPER_URL = "http://localhost:8765"

# API endpoints
TRANSPORTAPI_BASE_URL = "https://transportapi.com/v3/uk/bus/stop"

# Attributes
ATTR_CALLS_TODAY = "calls_today"
ATTR_AUTO_CALLS_TODAY = "auto_calls_today"
ATTR_LAST_CHECK = "last_check"
ATTR_DATA_SOURCE = "data_source"
ATTR_DEPARTURES = "departures"

# Data sources
SOURCE_TRANSPORTAPI = "TransportAPI"
SOURCE_SCRAPER = "Lothian Scrape"
SOURCE_NONE = "None"
