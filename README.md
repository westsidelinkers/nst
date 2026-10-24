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
- **Live trend graph** — crypto-style throughput chart with a gradient fill,
  green/red trend line and a highlighted latest point. Dips below the threshold
  line mark the video-buffering moments.
- **Data-driven bars** — thin bars between label and value; width is proportional
  to the current measurement and animates smoothly only when the data changes
  (instant under reduced motion).
- **Transparent on black** — fully transparent panel floating on the workspace,
  tokyonight palette, JetBrainsMono Nerd Font.
- **Fedora Atomic-specific signals** — pending rpm-ostree updates, reboot
  required, failed systemd units, firmware updates.
- **Addon modules** — bufferbloat (LAN vs WAN), public IP / ISP, battery health
  (74% of design capacity on this machine), CPU usage / RAM usage / disk, IPv6
  status, device count.
- **Three-tier measurement** — continuous passive (free), scheduled capacity
  probe (8×5 MB, every 8 h, 120 MB/day budget), on-demand full speedtest.
- **CacheFly primary, Cloudflare backup** — rotation on rate limit (429).
- **Bufferbloat detection** — LAN +39.9 ms (Wi-Fi queues under load), WAN +0.4 ms
  (ISP has effective AQM). Explains why videos stutter even when throughput looks
  fine.
- **Sci-fi aesthetic** — corner brackets, scanlines, circuit traces, crypto-style
  trend chart, optional full-screen ambient layer.

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

## Install

```sh
./install.sh
```

This installs `~/.local/bin/nst`, creates `~/.config/nst/config.toml`, and
enables/starts the `nst.service` systemd user unit. The unit is bound to
`sway-session.target` (`PartOf=`), so it stops when Sway exits and starts
again on the next session; `Restart=always` restarts it if it crashes.

## Notes

- **Layer shell runtime:** `gtk4-layer-shell` 1.3.0 is installed on the host and
  the app runs with the host Python/GTK stack. Run it through the `nst`
  launcher (`~/.local/bin/nst`), which points `PYTHONPATH` at the source tree.

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
├── CHANGELOG.md
└── README.md
```

## Status

**v1.0.0 — v1 feature freeze.** The core panel, addons, live trend graph,
data-driven bars, and systemd autostart are complete. Further
customizations are reserved for **v1.2.1**.

## Versioning

- **v1.0.0** — frozen v1 feature set.
- **v1.2.1** — future customizations; not part of v1.

## Roadmap

- **v1.0.0** — Frozen v1 feature set: core panel, addons, live trend graph, data-driven bars, systemd autostart.
- **v1.0.1** — Notifications, offline resilience, diagnostics bundle export.
- **v1.0.2** — Packet loss + jitter trend sparkline (last 5 minutes), VoIP MOS estimate.
- **v1.0.3** — IPv6 status + path MTU / MTU discovery, DNS resolver benchmark.
- **v1.0.4** — Device discovery improvements, new-device alerts.
- **v1.0.5** — Historical logging/export (CSV/JSON), alert rules engine.
- **v1.0.6** — Comparison mode, per-interface / per-SSID history, data-usage quotas.
- **v1.0.7** — Wi-Fi channel/interference scan, roaming / signal history, mesh node signal.
- **v1.0.8** — Captive-portal detection, VPN status and tunnel latency, proxy/PAC detection, DNS-over-HTTPS/TLS + DNSSEC status.
- **v1.0.9** — Duplicate-IP / ARP conflict detection, gateway and DHCP diagnostics, NTP offset, MTU black-hole detection, route trace + ASN/region view.
- **v1.2.0** — ISP throttling detection, local `iperf3` test, Flatpak/systemd health, failed systemd units, power-profile switching, GPU busy% / RC6, per-device bandwidth, per-interface comparison, ambient starfield, DNS/WebRTC leak checks, IP reputation, firewall/conntrack diagnostics, certificate expiry checks, multicast/IGMP visibility.
- **v1.2.1** — Future customizations.
- **v1.2.2** — Tier 2 modules: Flatpak update count, failed systemd units, power profile switching, GPU busy% via RC6 residency.


## License

MIT License. See `LICENSE` for details.