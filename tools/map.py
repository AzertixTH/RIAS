import json
import urllib.request
import urllib.parse

_BASE = "http://127.0.0.1:5731"
_OSRM = "https://router.project-osrm.org/route/v1/driving"


def geocode(place: str) -> tuple[float, float]:
    url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(place)}&format=json&limit=1"
    req = urllib.request.Request(url, headers={"User-Agent": "RIAS/1.0"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        results = json.loads(resp.read())
    if not results:
        raise ValueError(f"Locatie niet gevonden: {place}")
    return float(results[0]["lat"]), float(results[0]["lon"])


def _post(path: str, data: dict) -> bool:
    body = json.dumps(data).encode()
    req = urllib.request.Request(f"{_BASE}{path}", data=body, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=5)
        return True
    except Exception:
        return False


def map_show(locations: list[dict]) -> str:
    """
    Toon locaties op de kaart. Elke locatie: {"lat": float, "lon": float, "label": str}
    """
    markers = [{"lat": l["lat"], "lon": l["lon"], "label": l.get("label", "")} for l in locations]
    center = [locations[0]["lat"], locations[0]["lon"]] if locations else [50.85, 4.35]
    _post("/update", {"markers": markers, "center": center, "zoom": 10})
    return f"Kaart bijgewerkt met {len(markers)} locatie(s). Open http://127.0.0.1:5731"


def map_route(start_lat: float, start_lon: float, end_lat: float, end_lon: float,
              start_label: str = "Start", end_label: str = "Einde") -> str:
    """
    Bereken een route via OSRM en toon op kaart.
    """
    url = f"{_OSRM}/{start_lon},{start_lat};{end_lon},{end_lat}?overview=full&geometries=geojson"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
        coords = data["routes"][0]["geometry"]["coordinates"]
        route = [[c[1], c[0]] for c in coords]
        distance_km = round(data["routes"][0]["distance"] / 1000, 1)
        duration_min = round(data["routes"][0]["duration"] / 60)
        markers = [
            {"lat": start_lat, "lon": start_lon, "label": start_label},
            {"lat": end_lat, "lon": end_lon, "label": end_label},
        ]
        _post("/update", {"markers": markers, "route": route, "zoom": 10})
        return f"Route: {distance_km} km — ~{duration_min} min. Open http://127.0.0.1:5731"
    except Exception as e:
        return f"map_route error: {e}"


def map_clear() -> str:
    _post("/clear", {})
    return "Kaart geleegd."
