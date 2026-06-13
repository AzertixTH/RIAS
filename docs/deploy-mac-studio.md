# Deploy checklist — Mac Studio (RIAS server)

Doel: Mac Studio draait headless **Ollama** (lokale LLM, bereikbaar over LAN/Tailscale)
en **`server.py`** (Discord bot + API + trading watcher). Geen Claude Code op deze
machine — alles hieronder is handmatig via terminal/SSH.

---

## 0. Vooraf — naam & toegang

- [ ] Kies een hostnaam voor de Mac (Norse conventie: Vanaheim/Bifröst/Midgard/Mímir
      staan nog vrij). Zet die naam in System Settings → General → Sharing → "Computer Name".
- [ ] System Settings → General → Sharing → **Remote Login** aanzetten (SSH server aan)
- [ ] Tailscale installeren als je dat al gebruikt (zie `STT_URL` opmerking onder stap 5) —
      geeft een vast `100.x.x.x` adres, onafhankelijk van WiFi/LAN
- [ ] Sleep uitschakelen voor server-gebruik:
  ```bash
  sudo pmset -a sleep 0 disksleep 0 displaysleep 10
  ```

---

## 1. Basis tools

```bash
xcode-select --install        # command line tools
brew install python@3.12 git ollama
```

---

## 2. Ollama — lokaal LLM, bereikbaar over LAN

```bash
brew services start ollama
ollama pull <modelnaam>        # bv qwen3:30b — kies op basis van RAM van de Mac
```

Standaard luistert Ollama enkel op `127.0.0.1`. Voor LAN-toegang:

```bash
launchctl setenv OLLAMA_HOST "0.0.0.0"
brew services restart ollama
```

> Dit `setenv` is per login-session. Voor persistente boot-config: edit
> `~/Library/LaunchAgents/homebrew.mxcl.ollama.plist` en voeg toe:
> ```xml
> <key>EnvironmentVariables</key>
> <dict>
>     <key>OLLAMA_HOST</key>
>     <string>0.0.0.0</string>
> </dict>
> ```
> dan `brew services restart ollama`.

- [ ] Test lokaal: `curl http://localhost:11434/api/tags`
- [ ] Test vanaf Odin: `curl http://<mac-ip-of-tailscale-ip>:11434/api/tags`
- [ ] Als macOS Firewall aanstaat (System Settings → Network → Firewall):
      `ollama` toevoegen aan toegestane apps, of firewall uit voor LAN-only gebruik

---

## 3. Repo + Python omgeving

```bash
git clone https://github.com/AzertixTH/RIAS.git
cd RIAS
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium     # nodig voor Kage's browser tools
```

---

## 4. `.env` configureren

```bash
cp .env.example .env
```

Vul in (`nano .env` of `vim .env`):

| Key | Waarde |
|---|---|
| `ASSISTANT_NAME` / `USER_NAME` | zoals bij Odin |
| `DISCORD_BOT_TOKEN` | bot token |
| `OPENROUTER_API_KEY` | voor cloud-agents (Kage/Echo/Loki) |
| `ANTHROPIC_API_KEY` | indien Kage Claude API gebruikt |
| `ELEVENLABS_API_KEY` / `MISTRAL_AI_API_KEY` | enkel als Discord TTS/voice attachments gebruikt worden |
| `SAGA_PATH` | pad naar gesyncte Saga-map (zie stap 5) |
| `AETHER_PATH` | pad naar gesyncte Aether-map (zie stap 5) |
| `*_MODEL` | indien je hier de lokale Ollama wil gebruiken voor een agent: `LLM_BASE_URL=http://localhost:11434` + modelnaam uit `ollama list` |

---

## 5. Saga/Aether sync

Curator, memory en `trading_db` schrijven naar `SAGA_PATH` — die map bestaat nu enkel
lokaal op Odin (Obsidian vault).

- [ ] Sync-mechanisme opzetten (Syncthing aanbevolen — beide richtingen, geen cloud)
- [ ] `SAGA_PATH`/`AETHER_PATH` in `.env` naar de gesyncte locatie laten wijzen
- [ ] Check: `ls "$SAGA_PATH"` toont `USER.md`, `MEMORY.md`, `sessions/`

**Let op `STT_URL`** (`platforms/discord_bot.py`) — default
`http://100.98.53.100:10300/v1/audio/transcriptions` (Tailscale-adres van je STT-server).
Als de Mac in hetzelfde Tailnet zit werkt dit automatisch; anders `STT_URL` in `.env`
overschrijven of voice-attachments in Discord negeren (faalt graceful met `[STT error: ...]`).

---

## 6. Eerste test run (handmatig, voorgrond)

```bash
source venv/bin/activate
python server.py
```

- [ ] Discord bot komt online
- [ ] API reageert: `curl http://localhost:8000/docs`
- [ ] Geen import errors in de output
- [ ] Ctrl+C om te stoppen

---

## 7. Auto-start via launchd

`~/Library/LaunchAgents/com.rias.server.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.rias.server</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/<gebruiker>/RIAS/venv/bin/python</string>
        <string>/Users/<gebruiker>/RIAS/server.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/<gebruiker>/RIAS</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/<gebruiker>/RIAS/server.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/<gebruiker>/RIAS/server.err</string>
</dict>
</plist>
```

```bash
launchctl load ~/Library/LaunchAgents/com.rias.server.plist
launchctl list | grep rias        # status check
tail -f ~/RIAS/server.log
```

---

## 8. Verificatie vanaf Odin

- [ ] `curl http://<mac>:11434/api/tags` → Ollama bereikbaar
- [ ] `curl http://<mac>:8000/docs` → API bereikbaar
- [ ] Discord bot reageert op een testbericht
- [ ] (optioneel) Odin's `.env`: `LLM_BASE_URL=http://<mac-ip>:11434` zetten als de
      CLI op Odin de lokale Ollama-modellen moet gebruiken

---

## Bekend "later"-item

`tools/registry.py` → `text_to_speech` doet `from core.voice import speak`, en
`core/voice.py` zet `sd.default.device = 'pipewire'` (Linux-only). Op de Mac geeft dit
een fout terug aan het model (gevangen door `_execute_tool_safe`, geen crash) —
maar de tool werkt niet en heeft op een headless server ook geen zin. Fix: regel
verwijderen/conditioneel maken in `core/voice.py`, of `text_to_speech` uit de
toolset filteren voor Discord-conversaties die op de Mac draaien.
