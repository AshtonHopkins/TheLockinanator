# TheLockinanator

A deliberately tongue-in-cheek computer-vision focus tool: it watches you through
your webcam and "punishes" you when you stop concentrating. Look away too long or
sneak a glance at your phone and your **focus meter** drains — when it bottoms
out, you get blasted (alarm into headphones, fart sounds out of a speaker).

Everything runs **locally on your machine**. No video is recorded or uploaded —
frames are processed in memory and discarded.

> Status: MVP. Windows-only for now. It's not meant to be taken too seriously,
> but it works.

## How it works

- **Detection (webcam, MediaPipe):** head-pose look-away, a hand/posture phone
  heuristic, and absence (no face). Brief glances are free — only distraction
  sustained past a short grace period counts.
- **Focus meter:** drains on an accelerating curve (a full meter empties after
  ~10s of continuous distraction) and refills steadily (~2 min of focus to
  refill). Hitting zero fires a punishment, then the meter resets to ~50% with a
  short cooldown.
- **Breaks:** a 5-minute break, available once per rolling hour. Walking away
  (sustained absence) auto-burns an available break; if none is available, the
  meter just drains.
- **Punishment:** device-aware audio — alarm for headphones, fart sounds for
  speakers (override in config). The on-screen alert is a small, low-key toast so
  you can refocus fast.
- **Sessions & stats:** open-ended start/stop from the silly control window or the
  tray. Each session is logged to a local SQLite DB with an end-of-session score.

## Requirements

- Windows 10/11
- Python 3.11+ (tested on 3.14)
- A webcam

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Run

```powershell
.\.venv\Scripts\python.exe -m thelockinanator
```

On first run it downloads the MediaPipe face/hand models into
`thelockinanator/assets/models/` (cached afterwards). The control window opens;
hit **START** and it tucks into the system tray so it won't distract you. Restore
it, take a break, or quit from the tray icon. Tick **Show camera preview** to see
what the detector sees (handy for tuning).

## Customizing

- **Art:** drop PNGs (transparent backgrounds look best) into
  `thelockinanator/assets/images/` named `Eagle.png`, `Monster.png`,
  `Mushroom.png`, `Tank.png`, `Kitten.png`. Missing files render as labeled
  placeholders.
- **Sounds:** replace `thelockinanator/assets/sounds/alarm.wav` and `fart.wav`
  (the bundled ones are functional placeholders).
- **Config:** create `config/user_config.json` to override any default from
  `config/default_config.json` (only include the keys you want to change). For
  example, force fart sounds and tune sensitivity:

  ```json
  {
    "audio": { "output_override": "speaker", "volume": 0.8 },
    "detection": { "look_away_pitch_deg": 25 }
  }
  ```

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The core logic (focus meter, session/break rules, detector decisions, engine,
stats, orchestrator) is covered by fast, hardware-free tests.

## Roadmap (not yet implemented)

- App/website allowlist monitoring
- More extreme, opt-in punishments
- Eye-gaze refinement and a true "book mode"
- macOS/Linux support

## License

See [LICENSE](LICENSE).
