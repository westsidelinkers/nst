# nst — Network Status Tool

A desktop network status panel for **Fedora Atomic (Sway)** that answers one question:
**"is my internet actually slow right now, and why?"**

Instead of opening a browser, searching "speed test", and waiting through ads,
the panel shows a glanceable verdict — **ISP LIMITED**, **RADIO DEGRADED**,
**HIGH LATENCY**, or **HEALTHY** — backed by a visible measurement and a
breakdown of where the bottleneck is (local Wi-Fi vs. upstream ISP).

## Features

- **Verdict engine** — four verdicts computed from passive signals (throughput,
  latency, signal strength, retransmits, bufferbloat) plus a scheduled capacity
  probe. Distinguishes "slow" from "busy" (saturated link) from "broken" (idle
  but degraded).
- **Scrolling heartbeat graph** — ECG-style waveform showing throughput over time.
  Dips below the threshold line mark the video-buffering moments.
- **Data-driven musical bars** — thin animated bars between label and value,
  bouncing ±15% around a base height proportional to the current value.
- **Transparent on black** — fully transparent panel floating on the workspace,
  tokyonight palette, JetBrainsMono Nerd Font.
- **Fedora Atomic-specific signals** — pending rpm-ostree updates, reboot
  required, failed systemd units, firmware updates.
- **Addon modules** — bufferbloat (LAN vs WAN), public IP / ISP, battery health
  (74% of design capacity on this machine), CPU / RAM / temp / disk, IPv6
  status, device count.
- **Three-tier measurement** — continuous passive (free), scheduled capacity
  probe (8×5 MB, every 8 h, 120 MB/day budget), on-demand full speedtest.
- **CacheFly primary, Cloudflare backup** — rotation on rate limit (429).
- **Bufferbloat detection** — LAN +39.9 ms (Wi-Fi queues under load), WAN +0.4 ms
  (ISP has effective AQM). Explains why videos stutter even when throughput looks
  fine.
- **Sci-fi aesthetic** — corner brackets, scanlines, circuit traces, oscilloscope
  waveform, optional full-screen ambient layer.

## Target environment

- Fedora 44 Sway Atomic (sericea base), Sway 1.11 / wlroots 0.19.3
- Intel UHD 620 (i915, Mesa 26.0.3, OpenGL 4.6)
- 1366×768 single panel, 60 Hz
- 2-core / 4-thread i3-7020U, 8 GB RAM, ~16.4 Wh usable battery

## Tech stack

- Python 3.14 + PyGObject 3.56 + GTK4 4.22 + libadwaita 1.9
- gtk4-layer-shell 1.3.0 (wlr-layer-shell protocol)
- Cairo (python3-cairo 1.28.0) for sparklines
- TOML config, systemd user unit autostart
- rpm-ostree for layering gtk4-layer-shell (no reboot for additions)

## Notes

- Signal strength thresholds: the UI marks signal as good at >= -67 dBm and warn at
  >= -75 dBm, while the verdict engine treats only < -75 dBm as radio-degraded
  (so the -67..-75 dBm band is a display-level warning that does not by itself
  change the verdict).

## Project structure

```
nst/
├── docs/superpowers/
│   ├── specs/2026-10-22-network-status-panel-design.md
│   └── plans/2026-10-22-network-status-panel-plan.md
├── src/nst/
│   ├── config.py
│   ├── measurement/       # throughput, verdict, T0, T1, bufferbloat
│   ├── ui/                # panel, tiles, heartbeat, expanded, css
│   ├── addons/            # bufferbloat, public_ip, battery, os_updates, cpu_mem, wifi
│   └── autostart.py
├── tests/
├── pyproject.toml
├── config.toml.example
└── README.md
```

## Status

**Design complete.** Implementation plan written (14 tasks, TDD). Not yet implemented.

## License

TBD