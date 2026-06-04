import os
import requests

_BASE = "https://discord.com/api/v10"


def _headers():
    token = os.getenv("DISCORD_BOT_TOKEN")
    return {"Authorization": f"Bot {token}", "Content-Type": "application/json"}


def _guild_id():
    return os.getenv("DISCORD_GUILD_ID")


def discord_create_category(name: str) -> str:
    r = requests.post(
        f"{_BASE}/guilds/{_guild_id()}/channels",
        json={"name": name, "type": 4},
        headers=_headers(),
    )
    data = r.json()
    if "id" in data:
        return f"Category '{data['name']}' aangemaakt (id: {data['id']})"
    return f"Fout: {data}"


def discord_create_channel(name: str, category_id: str = None, topic: str = "") -> str:
    payload = {"name": name, "type": 0}
    if category_id:
        payload["parent_id"] = category_id
    if topic:
        payload["topic"] = topic
    r = requests.post(
        f"{_BASE}/guilds/{_guild_id()}/channels",
        json=payload,
        headers=_headers(),
    )
    data = r.json()
    if "id" in data:
        return f"Channel '#{data['name']}' aangemaakt (id: {data['id']})"
    return f"Fout: {data}"


def discord_list_channels() -> str:
    r = requests.get(f"{_BASE}/guilds/{_guild_id()}/channels", headers=_headers())
    channels = r.json()
    if not isinstance(channels, list):
        return f"Fout: {channels}"
    categories = {c["id"]: c["name"] for c in channels if c["type"] == 4}
    lines = []
    for c in sorted(channels, key=lambda x: (x.get("parent_id") or "", x["name"])):
        if c["type"] == 4:
            lines.append(f"\n📁 {c['name']} (id: {c['id']})")
        elif c["type"] == 0:
            cat = categories.get(c.get("parent_id"), "—")
            lines.append(f"  # {c['name']} (id: {c['id']})")
    return "\n".join(lines) if lines else "Geen channels gevonden."


def discord_send_to_channel(channel_id: str, message: str) -> str:
    chunks = [message[i:i+2000] for i in range(0, len(message), 2000)]
    for chunk in chunks:
        r = requests.post(
            f"{_BASE}/channels/{channel_id}/messages",
            json={"content": chunk},
            headers=_headers(),
        )
        if r.status_code not in (200, 201):
            return f"Fout bij sturen: {r.json()}"
    return f"Bericht gestuurd naar channel {channel_id}."
