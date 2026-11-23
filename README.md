# Gate Watch

A small self-hosted watcher for IP cameras. It reads your camera's RTSP stream, looks for **people inside an area you draw**, and sends a **Telegram** alert with a snapshot. Once a day it tells you whether anything was seen.

- Runs on any always-on home machine (a spare PC, mini PC or home server) in Docker. No cloud, no subscription.
- Person detection uses YOLOv8n on the CPU (about 2 frames per second per camera).
- Several cameras, each with its own zone and rule.
- Family members can be added from inside the bot.

> This is a convenience tool, not a certified alarm system. Cameras, Wi-Fi, power and AI can all fail. Don't rely on it alone for anything important.

## What it does

| Feature | Detail |
|---|---|
| Zone alert | Alert when a person's feet are inside your zone for 3 frames in a row |
| Dwell rule | Optional `dwell_s`: only alert if the person *stays* that many seconds (good for a car: ignore passers-by, catch someone lingering) |
| Snapshot | The alert photo has the zone and the detected person outlined |
| Cooldown | One alert per camera per 2 minutes, so one visitor is not 30 messages |
| Daily report | 12:00 India time (IST), covering the previous 24 hours: "nothing detected" or a list of detections by camera |
| Camera down | A message if a camera sends no video for 5 minutes, and another when it's back |
| Commands | `arm`, `disarm`, `status` (any approved person); `allow <id>`, `remove <id>`, `members` (owner only) |

Change the report time or timezone in `gatewatch/report.py` (`REPORT_HOUR`, `IST`).

## How it works

```
 camera / NVR --RTSP--> gate-watch (Docker) --> Telegram (you + family)
                          |-- YOLOv8n person detector
                          |-- your zones (cameras.json)
                          '-- SQLite log (daily report, arm state, members)
```

A person counts as "in the zone" when the **bottom-centre of their detection box** (roughly their feet) is inside your polygon. That is why zones should be drawn on the floor, see [Mapping a tight zone](#mapping-a-tight-zone).

## Requirements

- An always-on machine on the same network as the camera, with Docker and Docker Compose.
- A camera or NVR that serves **RTSP**. Dahua-based cameras (including CP Plus) work out of the box. Anything else works if you give it its RTSP URL (see [Other cameras](#other-cameras)).
- A Telegram account.
- About 2 GB of disk for the image and 1.5 GB of RAM.

## Setup

### 1. Get the code

```bash
git clone https://github.com/shivam27k/gate-watch.git
cd gate-watch
mkdir -p data
```

### 2. Create a Telegram bot

1. In Telegram, open **@BotFather**, send `/newbot`, pick a name and a username ending in `bot`.
2. Copy the **token** it gives you. Treat it like a password.
3. Open your new bot and send it `/start`.
4. Find your chat id: open `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser and look for `"chat":{"id":123456789`. That number is your chat id.

### 3. Configure

```bash
cp .env.example .env
```

Edit `.env` with the camera address and login, your bot token and your chat id. Never commit this file (it is in `.gitignore`).

### 4. Build

```bash
docker compose build
```

The first build downloads PyTorch (CPU) and takes a while.

### 5. Find which channel is which camera

An NVR has numbered channels. Grab a test frame from each so you can see which is which:

```bash
docker compose run --rm gatewatch python scripts/grab_frame.py 1 2 3 4
```

This writes `data/frame_ch1.jpg`, `data/frame_ch2.jpg`, and so on. Open them and note which camera is on which channel.

### 6. Draw your zones

Follow [Mapping a tight zone](#mapping-a-tight-zone) below, then put the result in `data/cameras.json`. Start from the example:

```bash
cp cameras.example.json data/cameras.json
```

### 7. Check the zones, then run

```bash
docker compose run --rm gatewatch python scripts/preview_zone.py data/cameras.json car data/frame_ch1.jpg data/preview_car.jpg
```

Open `data/preview_car.jpg` and confirm the yellow area is where you meant. Then:

```bash
docker compose up -d
docker compose logs -f
```

You should get a "Watch started" message on Telegram. Walk into a zone to test it, and walk outside to check it stays quiet.

## Mapping a tight zone

The zone is what keeps the alerts useful. A tight zone around exactly the area you care about means no alerts for the street, neighbours or passing cars.

**The one rule: draw the floor, not the person.** The program checks the person's *feet*, so draw the patch of ground where a person would stand: in front of the car door, across the gateway, on the doorstep. A zone drawn at head height in the picture will miss people or trigger from behind it.

### Using the zone picker (no install)

1. Open [`tools/zone-picker.html`](tools/zone-picker.html) in any web browser (double-click the file).
2. Choose a frame, for example `data/frame_ch1.jpg`.
3. Fill in a **name** (used in alerts, e.g. `car`), the **channel** number, and **stay seconds** (0 = alert immediately).
4. Click the corners of the area, going around it in order. The yellow shape updates as you click. **Undo point** and **Clear** fix mistakes.
5. Click **Copy JSON** and paste the block into the list in `data/cameras.json`.

Everything runs in your browser. The image is not uploaded anywhere.

### What `cameras.json` looks like

```json
[
  { "name": "car",  "channel": 1, "dwell_s": 5, "zone": [[0.20,0.55],[0.75,0.55],[0.80,0.95],[0.15,0.95]] },
  { "name": "gate", "channel": 2, "dwell_s": 0, "zone": [[0.05,0.50],[0.45,0.50],[0.50,0.98],[0.02,0.98]] }
]
```

Zone points are fractions of the picture (0 to 1, left to right and top to bottom), so they keep working if you change the stream resolution. Use **3 or more** points.

### Tips for good zones

- **Make it a bit bigger than the object.** For a car, draw from about 1 metre out around the car, not exactly along its edge, so a person reaching for a door handle is inside it.
- **Keep it off the pavement/road** unless you want passers-by to trigger it.
- **Use `dwell_s` for things people pass near**: 5 seconds works for a parked car. Use `0` for a gate or door where any entry should alert.
- **Check at night.** Infrared mode changes the picture, so test with a night frame if possible.
- **A person standing at the very edge** may flicker in and out; the 3-frame rule absorbs most of this. Move the edge outward if it bothers you.
- **Look at your alert snapshots.** They show the zone and the detected person, so you can see exactly why it fired and adjust.

After editing `data/cameras.json`, restart: `docker compose restart`.

## Family access

The bot is not open to everyone: it sends photos from your home. To add a family member:

1. They open your bot in Telegram and send any message. They get "Not authorized yet".
2. You get "*Name* (id) wants access. Reply `allow <id>` to approve."
3. You reply `allow 123456789`. They now get every alert and can use `arm`, `disarm` and `status`.

Only the owner (the chat id in `.env`) can `allow` / `remove` people. `members` lists everyone.

## Other cameras

For a camera that is not Dahua/CP Plus, give the full RTSP URL in `cameras.json`:

```json
{ "name": "porch", "url": "rtsp://user:pass@192.168.1.50:554/stream1", "zone": [[0.1,0.5],[0.9,0.5],[0.9,0.95],[0.1,0.95]] }
```

Find your camera's RTSP URL in its manual or on a site like iSpyConnect's camera database. Passwords with special characters must be URL-encoded (`@` becomes `%40`). The URL here lives in `data/`, which is git-ignored. To grab test frames from such a camera, use any tool that can save a still from RTSP (for example `ffmpeg -i <url> -frames:v 1 data/frame.jpg`).

## Tuning

| Want | Change |
|---|---|
| Fewer false alarms | Tighten the zone; raise `conf` in `gatewatch/detector.py` (default 0.5); use `dwell_s` |
| Faster alerts | Lower `Trigger(3, ...)` frame count in `gatewatch/main.py` |
| Less CPU | Edit `cpus` in `docker-compose.yml`; the loop runs about 2 frames per second |
| Different cooldown | `cooldown_s` default 120 in `gatewatch/logic.py` |

## Troubleshooting

- **No frames / "unreachable" message:** check the IP, login and that the camera is on the same network. Test the stream with VLC using the same RTSP URL.
- **Digest/401 errors:** wrong password, or the camera locked the account after too many tries.
- **Nothing alerts:** run `preview_zone.py` and check the zone covers the floor where people stand; check the bot is `arm`ed (`status`).
- **Container restarts:** `docker compose logs gatewatch`.
- **No Telegram messages:** you must send `/start` to the bot once before it can message you.

## Security notes

- `.env` and `data/` hold your camera password, bot token and snapshots. Keep them private; they are git-ignored.
- If a token or password leaks, revoke the token in @BotFather (`/revoke`) and change the camera password.
- No ports are opened; the container only makes outbound connections (to your camera and to Telegram).

## Development

```bash
pip install pytest
python -m pytest
```

The decision logic (zone test, dwell, cooldown, commands, report) is covered by unit tests with fake cameras and a fake Telegram. The RTSP reader, the YOLO model and real Telegram calls are not covered by tests.

## Limitations

- It detects *a person in a place*, not intent. "Tampering" with a car is approximated by "someone stayed in the zone".
- Night, rain, heavy shadows and very small or distant people reduce accuracy.
- If the host loses power or Wi-Fi it can't alert you. A missing daily report is your hint.

## License

MIT
