import os
import requests

_HA_URL = os.getenv("HA_URL", "").rstrip("/")
_HA_TOKEN = os.getenv("HA_TOKEN", "")


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_HA_TOKEN}",
        "Content-Type": "application/json",
    }


def ha_get_state(entity_id: str) -> str:
    if not _HA_URL or not _HA_TOKEN:
        return "HA_URL of HA_TOKEN niet ingesteld in .env"
    try:
        r = requests.get(f"{_HA_URL}/api/states/{entity_id}", headers=_headers(), timeout=10)
        r.raise_for_status()
        data = r.json()
        state = data.get("state", "?")
        attrs = data.get("attributes", {})
        friendly = attrs.get("friendly_name", entity_id)
        unit = attrs.get("unit_of_measurement", "")
        extra = ""
        if "temperature" in attrs:
            extra = f"  temp={attrs['temperature']}"
        if "brightness" in attrs:
            pct = round(attrs["brightness"] / 255 * 100)
            extra = f"  helderheid={pct}%"
        return f"{friendly}: {state}{unit}{extra}"
    except requests.HTTPError as e:
        return f"HA fout {e.response.status_code}: {e.response.text[:200]}"
    except Exception as e:
        return f"Fout: {e}"


def ha_call_service(domain: str, service: str, entity_id: str = None, data: dict = None) -> str:
    if not _HA_URL or not _HA_TOKEN:
        return "HA_URL of HA_TOKEN niet ingesteld in .env"
    payload = dict(data or {})
    if entity_id:
        payload["entity_id"] = entity_id
    try:
        r = requests.post(
            f"{_HA_URL}/api/services/{domain}/{service}",
            headers=_headers(),
            json=payload,
            timeout=10,
        )
        r.raise_for_status()
        return f"OK — {domain}.{service}" + (f" op {entity_id}" if entity_id else "")
    except requests.HTTPError as e:
        return f"HA fout {e.response.status_code}: {e.response.text[:200]}"
    except Exception as e:
        return f"Fout: {e}"


def ha_list_entities(domain: str = None) -> str:
    if not _HA_URL or not _HA_TOKEN:
        return "HA_URL of HA_TOKEN niet ingesteld in .env"
    try:
        r = requests.get(f"{_HA_URL}/api/states", headers=_headers(), timeout=15)
        r.raise_for_status()
        entities = r.json()
        if domain:
            entities = [e for e in entities if e["entity_id"].startswith(f"{domain}.")]
        lines = []
        for e in sorted(entities, key=lambda x: x["entity_id"]):
            name = e.get("attributes", {}).get("friendly_name", "")
            lines.append(f"{e['entity_id']}  ({e['state']})" + (f"  — {name}" if name else ""))
        if not lines:
            return f"Geen entities gevonden{f' voor domain {domain}' if domain else ''}."
        return "\n".join(lines[:100]) + (f"\n… (+{len(lines)-100})" if len(lines) > 100 else "")
    except requests.HTTPError as e:
        return f"HA fout {e.response.status_code}: {e.response.text[:200]}"
    except Exception as e:
        return f"Fout: {e}"
