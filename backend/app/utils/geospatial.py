from __future__ import annotations

"""Geospatial utilities for zone boundary operations.

NOTE: Full implementation is owned by Member 1 / plant GIS team.
These stubs define the module interface so other modules can import safely.
"""


def point_in_polygon(lat: float, lon: float, polygon_geojson: dict) -> bool:
    """Test whether a [lat, lon] coordinate lies inside a GeoJSON Polygon.

    Uses a simple ray-casting algorithm.
    """
    try:
        coordinates = polygon_geojson["coordinates"][0]
    except (KeyError, IndexError):
        return False

    n = len(coordinates)
    inside = False
    x, y = lon, lat  # GeoJSON uses [lon, lat] order
    j = n - 1
    for i in range(n):
        xi, yi = coordinates[i]
        xj, yj = coordinates[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi + 1e-10) + xi):
            inside = not inside
        j = i
    return inside


def bbox_from_polygon(polygon_geojson: dict) -> dict:
    """Return {min_lon, min_lat, max_lon, max_lat} bounding box for a GeoJSON polygon."""
    try:
        coords = polygon_geojson["coordinates"][0]
    except (KeyError, IndexError):
        return {}
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return {
        "min_lon": min(lons), "min_lat": min(lats),
        "max_lon": max(lons), "max_lat": max(lats),
    }
