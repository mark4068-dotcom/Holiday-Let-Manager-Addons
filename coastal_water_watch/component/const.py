"""Constants for Coastal Water Watch."""

DOMAIN = "coastal_water_watch"
PLATFORMS = ["sensor"]
CONF_LOCATION = "location"
CONF_UPDATE_INTERVAL = "update_interval"
DEFAULT_UPDATE_INTERVAL = 10
UPDATE_INTERVAL_OPTIONS = (5, 10, 15, 30)
DEFAULT_REQUEST_TIMEOUT_SECONDS = 20
EVENT_OVERFLOW_STARTED = f"{DOMAIN}_overflow_started"
EVENT_OVERFLOW_ENDED = f"{DOMAIN}_overflow_ended"

EA_BASE_URL = "https://environment.data.gov.uk"
SOUTHERN_WATER_RSW_SERVICE = (
    "https://services-eu1.arcgis.com/6qJmARkS2dt2IjVA/arcgis/rest/services/"
    "COR_RW_RSW_DATA_VIEW/FeatureServer"
)
