from __future__ import annotations

import math
from typing import Tuple, Optional

import requests

from .config import load_config


_config = load_config()


def geocode_address(address: str) -> Optional[Tuple[float, float]]:
    # Try Yandex Geocoder first if key present
    if _config.yandex_maps_api_key:
        try:
            url = "https://geocode-maps.yandex.ru/1.x"
            params = {
                "apikey": _config.yandex_maps_api_key,
                "format": "json",
                "geocode": address,
                "lang": "ru_RU",
                "results": 1,
            }
            resp = requests.get(url, params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            members = (
                data.get("response", {})
                .get("GeoObjectCollection", {})
                .get("featureMember", [])
            )
            if members:
                pos = (
                    members[0]
                    .get("GeoObject", {})
                    .get("Point", {})
                    .get("pos", "")
                )
                if pos:
                    lon_str, lat_str = pos.split()
                    return float(lat_str), float(lon_str)
        except Exception:
            pass
    return None


def route_distance_km(coord_from: Tuple[float, float], coord_to: Tuple[float, float]) -> float:
    # Prefer Yandex Routing if key exists
    if _config.yandex_maps_api_key:
        try:
            url = "https://api.routing.yandex.net/v2/route"
            waypoints = f"{coord_from[1]},{coord_from[0]}|{coord_to[1]},{coord_to[0]}"
            params = {
                "apikey": _config.yandex_maps_api_key,
                "waypoints": waypoints,
                "mode": "driving",
                "lang": "ru_RU",
            }
            resp = requests.get(url, params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            distance_m = None
            routes = data.get("routes") if isinstance(data, dict) else None
            if routes:
                r0 = routes[0]
                legs = r0.get("legs") if isinstance(r0, dict) else None
                if legs and isinstance(legs, list) and legs:
                    dist_obj = legs[0].get("distance") if isinstance(legs[0], dict) else None
                    if isinstance(dist_obj, dict):
                        distance_m = dist_obj.get("value") or dist_obj.get("meters")
                if distance_m is None:
                    distance_m = r0.get("distance")
            if distance_m is not None:
                return round(float(distance_m) / 1000.0, 3)
        except Exception:
            pass
    # Fallback to OSRM
    try:
        url = (
            f"https://router.project-osrm.org/route/v1/driving/"
            f"{coord_from[1]},{coord_from[0]};{coord_to[1]},{coord_to[0]}"
        )
        params = {"overview": "false"}
        resp = requests.get(url, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        routes = data.get("routes") or []
        if routes:
            distance_m = routes[0].get("distance", 0)
            return round(float(distance_m) / 1000.0, 3)
    except Exception:
        pass
    # Fallback to haversine
    return round(haversine_km(coord_from, coord_to), 3)


def haversine_km(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    lat1, lon1 = a
    lat2, lon2 = b
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    h = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * r * math.asin(math.sqrt(h))