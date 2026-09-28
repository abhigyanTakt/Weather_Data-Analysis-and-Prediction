"""
Resilient External API Clients Package for ClimaTrend.
Wraps all network requests with timeouts, exponential retries, TTL caching,
and graceful offline fallbacks.
"""

from climatrend.climate.clients.base_client import BaseResilientClient
from climatrend.climate.clients.open_meteo_client import OpenMeteoClient
from climatrend.climate.clients.disaster_client import DisasterClient
from climatrend.climate.clients.emission_client import EmissionClient

__all__ = [
    "BaseResilientClient",
    "OpenMeteoClient",
    "DisasterClient",
    "EmissionClient",
]
