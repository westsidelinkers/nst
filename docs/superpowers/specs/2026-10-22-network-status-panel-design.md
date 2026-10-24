# Network Status Panel — Design Document

**Date:** 2026-10-22
**Project:** nst (Network Status Tool)
**Target:** Fedora 44 Sway Atomic (sericea base), Sway 1.11 / wlroots 0.19.3
**Status:** Approved by user

## 1. Intent and why

The user (a single developer on a Fedora 44 Sway Atomic laptop) wants a desktop panel that answers one question: "is my internet actually slow right now, and why?" Today, when a video buffers or a page hangs, the user opens a browser, searches "speed test", clicks through to a speedtest site, waits through ads, and runs a 20-second test — just to confirm the network is degraded. That detour is the product problem.

The panel replaces that detour with a glanceable verdict: "ISP LIMITED", "RADIO DEGRADED", "HIGH LATENCY", or "HEALTHY", backed by a visible measurement and a breakdown of where the bottleneck is (local Wi-Fi vs. upstream ISP).

Secondary goals: surface the Fedora Atomic-specific signals that no existing tool shows (pending OS updates, reboot required, failed units, firmware updates), plus battery health, public IP, device count, and general system metrics — in a stylish, always-visible panel that matches the user's existing Tokyo Night desktop theme.

## 2. Goals, non-goals, anti-goals

### Goals
- Replace the browser speed-test detour with a glanceable, always-visible verdict.
- Distinguish "slow" from "busy" (saturated link) from "broken" (idle but degraded).
- Distinguish "local Wi-Fi is the problem" from "upstream ISP is the problem" — they send the user to different fixes.
- Surface Fedora Atomic-specific signals: pending rpm-ostree updates, reboot required, failed systemd units, firmware updates.
- Surface battery health (the user's pack is at 74% of design capacity — a real issue).
- Show how many devices are on the local network.
- Match the existing Tokyo Night visual language and the user's 32 px waybar aesthetic.
- Run unprivileged, native on the host, surviving OS upgrades.

### Non-goals (v1)
- Replacing waybar entirely (the panel complements the existing bar).
- Multi-monitor support (single output: eDP-1, 1366×768).
- GNOME-on-Wayland support (the user runs Sway; layer-shell is Sway/wlroots-only).
- A settings GUI (configuration is a TOML file).
- Per-process bandwidth attribution (requires root/eBPF).
- Pip-installable plugin system (packaging pain on Atomic; use config-driven modules + subprocess hooks instead).
- A screensaver (the user wants the aesthetic in the workspace, not a blank-screen mode).

### Anti-goals
- Do not show a raw Mbit/s number as the headline. A number without context is what sent the user to Google. The headline is a verdict.
- Do not run a 5 MB single-stream probe. It reports ~67 Mbit/s on a 38 Mbit/s link — 78% too high, measuring TCP ramp, not capacity.
- Do not continuously animate at 60 fps. On a 2-core laptop with 16.4 Wh usable battery, that costs 24–63% of the pack per 8-hour session.
- Do not attempt to log into the router. The Nokia GPON HGU's client list is session-gated; use the ARP/mDNS proxy instead.
- Do not use 8.8.8.8 as a DNS resolver. It measured 87 ms median / 261 ms max from this network. Use the router resolver (14 ms) or 9.9.9.9 (8 ms).

## 3. Constraints

### Hardware
- Intel Core i3-7020U (Kaby Lake, 2 cores / 4 threads, 2.3 GHz base)
- Intel UHD 620 integrated graphics (i915 driver, Mesa iris)
- 8 GB RAM, zram swap 7.6 GB
- 1366×768 single panel (eDP-1, AU Optronics, 60 Hz)
- Battery: 22.19 Wh at 73.97% of design capacity (30 Wh design), 1076 cycles → ~16.4 Wh usable
- No gcc, rust, cargo, make, meson, ninja, or dnf on the host
- rpm-ostree is the only package manager; layering requires `rpm-ostree install -yA` (live-applies additions without reboot)

### OS / environment
- Fedora 44.1.7 "Sway Atomic", sericea base ref, ostree/Atomic
- Sway 1.11 / wlroots 0.19.3, Wayland-only (XWayland present)
- waybar 0.15.0 already running as the bar (32 px, bottom, Tokyo Night palette)
- No user-authored systemd user units today; autostart uses sway `exec` lines + XDG autostart
- gtk4-layer-shell 1.3.0 available as a Fedora 44 package (deps already in base)
- GTK4 4.22.1, libadwaita 1.9.0, python3-gobject 3.56.2, python3-cairo 1.28.0 installed
- Flatpak only has freedesktop runtime 25.08 (GTK3-only); org.gnome.Platform absent
- The `gi` namespace in the Toolbx container is an empty decoy — real PyGObject is on the host

### Network
- Wi-Fi client on "RYAN 5G" (5 GHz, channel 44, 80 MHz, WPA2), interface `wlp2s0`, IP 192.168.1.64/24
- Gateway: 192.168.1.254 (Nokia GPON HGU, ISP-branded Bell/Safaricom)
- Sustained throughput: ~38 Mbit/s down (40.6 Mbit/s up), burst 77–141 Mbit/s for ~1.3 s
- Wi-Fi radio: 175.5 Mbit/s negotiated (VHT-MCS 4, 80 MHz), zero retransmits, zero beacon loss, signal −68 to −72 dBm
- ISP: Safaricom (Kenya), CGNAT 100.77.0.1, public IP 105.164.128.136
- No WAN IPv6 (link-local only)
- Bufferbloat: LAN +39.9 ms, WAN +0.4 ms
- DNS via router (192.168.1.254) through systemd-resolved stub 127.0.0.53
- 2 devices visible on the network (router + 1 Android phone at 192.168.1.69)
- Cloudflare `__down` hard cap: 99,999,999 bytes; rate-limits after ~830 MB (429, ~55 min cooldown)
- CacheFly `100mb.test` has no cap and no rate limit — independent confirmation of 38.1 Mbit/s sustained

### Visual
- Tokyo Night palette: bg #1a1b26, fg #c0caf5, blue #7aa2f7, cyan #7dcfff, purple #bb9af7, green #9ece6a, yellow #e0af68, red #f7768e, muted #a9b1d6, dim #414868
- Font: "JetBrainsMono Nerd Font", 12 px (installed at ~/.local/share/fonts/JetBrainsMono/)
- Waybar: 32 px, bottom, transparent bg, 6 px border-radius chips, spacing 6 px
- Screen: 1366×768, single output, 60 Hz

## 4. How it gets made (decisions as decided)

### 4.1 Standalone panel, not a waybar extension
waybar's `custom/*` module can render text, icons, tooltips, and click actions, but it cannot show charts, popups, custom layouts, or interactive controls. The user wants a "stylish" panel with a scrolling heartbeat graph, data-driven bars, and an expanded detail view — all of which exceed waybar's capabilities. The panel is a separate layer-shell surface that complements waybar.

### 4.2 Form factor: floating tile cluster, bottom-left

**Keyboard mode (builder's call, settle here):** The collapsed panel uses `Gtk4LayerShell.KeyboardMode.NONE` (never receives focus). The expanded panel switches to `KeyboardMode.ON_DEMAND` so it can receive Escape to close. When collapsed, it switches back to NONE. This resolves the apparent conflict between "closes with Escape" and "never receives focus" — the expanded state is the only one that takes focus, and only while open.
- Placement: anchored bottom-left, 34 px above waybar (which occupies the bottom 32 px)
- Collapsed size: 434×172 px, 6 tiles in a 3×2 grid
- Expanded size: ~560×520 px, opens on click, closes with a click or Escape
- Transparency: fully transparent background (no fill, no solid tiles) — only text, bars, brackets, and sparkline are visible. The black workspace shows through.
- Corner brackets: 4 L-shaped brackets at the panel corners (targeting-reticle aesthetic)
- Scanlines: subtle horizontal lines, 6 s CSS scroll animation
- Glow border: faint blue glow around the panel edges

### 4.3 Technology stack
- Language: Python 3.14 (host interpreter)
- UI toolkit: GTK4 4.22 + libadwaita 1.9
- Layer-shell: gtk4-layer-shell 1.3.0 (wlr-layer-shell protocol, Sway/wlroots compatible)
- Rendering: Cairo via Gtk.DrawingArea (python3-cairo 1.28.0, already a dependency of python3-gobject) for panel sparklines, bars, and static elements. OpenGL via GtkGLArea or GskShader for the optional ambient starfield layer (Mesa 26.0.3, Intel iris driver, OpenGL 4.6, accelerated) — Cairo CPU rendering at 60 fps on 1366×768 is unsuitable (~0.5–1.3 W). Vulkan is a viable alternative (Intel ANV ICD present) but unverified at runtime (vulkaninfo not installed). Software fallback: llvmpipe (swrast).- Config: TOML (~/.config/nst/config.toml)
- State: ~/.local/state/nst/ (XDG state dir, survives OS upgrades)
- Cache: ~/.local/cache/nst/ (XDG cache dir)
- Installation: `rpm-ostree install -yA gtk4-layer-shell` (live-applies, no reboot, persists across upgrades/rebases)
- Script location: ~/.local/bin/nst (survives OS upgrades, no root needed)

### 4.4 Autostart
- Primary: systemd user unit (~/.config/systemd/user/nst.service) with WantedBy=sway-session.target and an ExecStartPre guard that waits for `swaymsg -t get_outputs` to succeed (mitigates the classic "GTK app starts before compositor is ready" race).
- Alternative: XDG autostart .desktop file in ~/.config/autostart/ (uses the host's existing sway-xdg-autostart.target wiring).
- Fallback: sway `exec` line in ~/.config/sway/config.d/90-nst.conf with the same readiness guard.

### 4.5 Measurement strategy
Three tiers, respecting a 120 MB/day data budget:

| Tier | What | When | Cost |
|---|---|---|---|
| T0 — Passive, free, continuous | Interface counters (/proc/net/dev), ping to gateway and 1.1.1.1, DNS timing (systemd-resolved), TCP+TLS handshake timing, signal strength (iw), rx_dropped rate, battery/power | Every 1–2 seconds | ~0 bytes |
| T1 — Scheduled capacity probe | 8 parallel connections × 5 MB = 40 MB total to CacheFly (primary) / Cloudflare (backup), with 2-second ramp discard | Every 8 hours (~3 probes/day) | ~42 MB wire per probe, ~126 MB/day |
| T2 — On-demand full speedtest | 8 parallel × 5 MB (same as T1) or a full 20 MB probe on demand | User clicks "Run speed test now" | ~42 MB per click |

Why 8×5 MB and not 5 MB single-stream: A 5 MB single-stream transfer completes in ~0.6 s, entirely inside the TCP slow-start ramp. It reports ~67 Mbit/s on a link whose sustained capacity is ~38 Mbit/s. Eight parallel connections phase-align the ramp so the plateau dominates, reporting 39.8 Mbit/s (within 4% of true sustained). A browser speedtest reports ~42.5 Mbit/s — close enough that the user recognises the number.

**Probe volume (builder's call, settle here):** One probe per scheduled run (40 MB). The headline number is the median of the last 3 probe results, not 3 trials per run. This keeps the daily cost at 3 probes × 40 MB = 120 MB/day, matching the user's stated budget. The "3 trials" in the research was a measurement methodology, not a production requirement. The fixed 8×5 MB size and the "discard first 2 seconds" are the same operation: 8 connections each pull 5 MB (40 MB total, ~8 s at 40 Mbit/s), and the result is computed by discarding the first 2 seconds of the aggregate rate trace, then averaging the rest.

Cloudflare rate limiting: Cloudflare returns HTTP 429 after ~830 MB of probing. CacheFly (cachefly.cachefly.net/100mb.test) has no cap and no observed rate limit, and independently confirms 38.6 Mbit/s. CacheFly is the primary probe host; Cloudflare is the backup, with rotation on 429.

Probe design details:
- Fixed-duration approach: run 8 parallel connections for a fixed window, discard the first 2 seconds (ramp), average the rest. This makes the result independent of probe size.
- Take the median of 3 trials to kill the ±10% variance.
- Never probe when the link is busy (passive counters show >5 Mbit/s of our own traffic) — the probe would measure shared bandwidth, not capacity.
- The bytes=0 metadata probe (0 bytes, ~107 ms) provides a free reachability + latency check every 1–2 seconds.

**T0 HTTP endpoint (builder's call, settle here):** Use Cloudflare `__down?bytes=1` (1 byte, ~245 ms TTFB median) for the frequent passive probe — it provides DNS timing, TCP connect, TLS handshake, and TTFB in a single `curl -w` call. At 1 byte of payload it will not trigger Cloudflare's bulk rate limit (which kicks in after ~830 MB). CacheFly is reserved for the T1 capacity probe. The `bytes=0` variant (0 bytes, ~107 ms) is an alternative if Cloudflare starts rate-limiting the 1-byte requests; CacheFly's `100mb.test` with `Range: bytes=0-0` is the fallback.

**Module update cadence (builder's call, settle here):** The T0 loop (1–2 s) handles fast-changing metrics: throughput, latency, signal, rx_dropped rate, battery percentage. Slow-changing metrics use separate, longer timers or D-Bus signals: rpm-ostree status / fwupd every 5 minutes (or on systemd unit change); public IP every 1 hour (or on network change via NM D-Bus signal); ARP device count every 30 seconds; CPU/RAM/temp/disk every 5 seconds; signal strength every 5 seconds (or on NM D-Bus signal); power profile on D-Bus signal change. This avoids polling expensive commands every 1–2 seconds.

### 4.6 Verdict engine
The panel's headline is one of four verdicts, computed from the passive signals plus the last scheduled probe:

| Verdict | Condition |
|---|---|
| HEALTHY | Sustained throughput ≥ 30 Mbit/s, ping avg ≤ 20 ms, signal ≥ −67 dBm, rx_dropped rate ≤ 0.2/s |
| ISP LIMITED | Sustained throughput < 30 Mbit/s, radio healthy (signal ≥ −67, retransmits 0, beacon loss 0), WAN latency normal |
| RADIO DEGRADED | Signal < −75 dBm OR rx_dropped rate > 1.0/s OR retransmits > 0 OR beacon loss > 0 |
| HIGH LATENCY | Ping avg > 50 ms OR jitter > 20 ms OR WAN bufferbloat > 10 ms (with normal throughput) |

On this machine, the expected verdict is ISP LIMITED — the radio is healthy but the sustained rate is ~38 Mbit/s of a 175.5 Mbit/s negotiated link.

**Verdict precedence (builder's call, settle here):** The four conditions are evaluated in severity order — RADIO DEGRADED > HIGH LATENCY > ISP LIMITED > HEALTHY — and the first one that matches wins. The default (no condition matches) is HEALTHY. The signal warning band (−67 to −75 dBm) is a display-level concern (yellow signal tile) and does not by itself change the verdict; a verdict changes only when a condition above is met. "WAN latency normal" means WAN RTT avg ≤ 20 ms and WAN bufferbloat ≤ 5 ms. "Normal throughput" for HIGH LATENCY means sustained throughput ≥ 15 Mbit/s (above the critical threshold). "Jitter" is the mdev (standard deviation of RTT) reported by ping. If two conditions match simultaneously, the more severe one wins.

### 4.7 Data-driven musical bars
Each tile has a thin animated bar between the label and the value:
- Bar height = value as a percentage of its reference (signal: −90 to −50 dBm scale; throughput: % of sustained capacity ~38 Mbit/s, NOT the radio link rate of 175.5 Mbit/s; latency: inverse %; retransmits: 0–10/s scale; bufferbloat: 0–100 ms scale; CPU: 0–100%; disk: 0–100% free). The radio link rate (175.5 Mbit/s) is shown as a separate metric, not used for bar scaling. This prevents healthy throughput from appearing as ~22% (which would read as degraded).- Bounce ±15% around the base height via CSS @keyframes on transform: scaleY() with transform-origin: bottom
- Color = state: green (good), yellow (warning), red (bad)
- Shimmer sweep across each bar (CSS @keyframes on transform: translateX())
- Cost: ~0.05–0.15 W for all bars combined (declarative CSS, no Python loop)
- Pause on battery / when idle; prefers-reduced-motion kills all animations

### 4.8 Scrolling heartbeat graph
- ECG-style scrolling waveform showing throughput samples over time
- New samples appended on the right, old ones scroll out
- Dips below the threshold line (15 Mbit/s) are marked with red dots
- 20–30 fps via Gtk.DrawingArea + add_tick_callback, throttled to idle when no new data
- Cost: ~0.2 W during scroll, ~0 W when idle
- The most valuable animation: directly shows the video-buffering moments as dips

### 4.9 Addon modules (config-driven)
The panel uses a config.toml module registry. Each module is a Python class with update(sample) and optional animate() methods. Modules can be enabled/disabled/reordered without code changes.

Tier 1 (v1):
- Bufferbloat indicator — LAN +39.9 ms, WAN +0.4 ms (measured). Detects Wi-Fi queueing vs. ISP queueing. Unprivileged, works.
- Public IP / ISP — ifconfig.co/json (105.164.128.136, Safaricom, Kenya). Cloudflare /meta is 403.
- Battery health — UPower Capacity (73.97%), cycles (1076), charge threshold (not set). A "battery at 74%" indicator.
- Pending OS updates / reboot required — rpm-ostree status (native host). Currently up to date, no reboot needed.
- CPU / RAM / temp / disk — all clean reads from /proc and /sys.
- Signal strength, channel, band, width — from iw dev wlp2s0 link.
- IPv6 status — link-local only, no WAN IPv6. Honest badge.
- Devices on network — best-effort ARP neighbor table + mDNS (2 devices: router + 1 Android phone). Labeled "devices seen," not "users on Wi-Fi."

Tier 2 (v1.2.2):
- Flatpak update count (9 pending, ~1.8 GB)
- Failed systemd units (1 system failure — benign Atomic quirk)
- Power profile (tuned-ppd, switchable via D-Bus)
- GPU busy% via RC6 residency sampling (i915 has no gpu_busy_percent sysfs, intel_gpu_top not installed)

Integration points:
- Config-driven module registry (config.toml) — primary
- Status file (~/.local/state/nst/status.json) watched via Gio.FileMonitor (inotify) — allows any external tool to push metrics
- custom/* subprocess hooks — waybar-compatible semantics (exec, interval, signal-driven updates, click actions), opt-in with security guardrails

### 4.10 Animation strategy
- Animate on change, not on a clock. Sample at 1 Hz (free), run redraw loops only during transitions.
- CSS transitions for state changes (verdict chip, bar widths, colors) — declarative, no Python, ~0 W
- CSS @keyframes for musical bars (infinite, but paused on battery/idle) — ~0.05 W
- DrawingArea + add_tick_callback for heartbeat scroll (20–30 fps, burst only) — ~0.2 W during scroll
- Adw.TimedAnimation + Adw.Easing for number tweening (200–300 ms) — negligible
- prefers-reduced-motion: bound to CSS provider at runtime; kills all animations when enabled
- Battery-aware: "on battery" means the battery is discharging AND below 30% (or whatever threshold the builder picks). When on AC power, always animate. When on battery but above 30%, animate at reduced intensity (slower frame rate, fewer effects). When on battery and below 30%, pause all non-essential animations.
- Focus/idle gating: the panel is a layer-shell surface with keyboard mode NONE, so it never receives focus. "Animate" means: the panel is visible (not occluded by a fullscreen window) AND the system is not idle (idle time < 5 minutes via org.freedesktop.login1 IdleSinceHint). When idle or occluded, stop all redraw loops and pause CSS animations. When active, resume.
- Never 60 fps always-on — costs 24–63% of the usable battery pack per 8-hour session

### 4.11 Verdict engine
Four verdicts computed from passive signals + last scheduled probe (see section 4.6). The verdict chip cross-fades between states via CSS transition.

### 4.12 Bufferbloat measurement
- LAN bufferbloat: +39.9 ms (Wi-Fi queues badly under load)
- WAN bufferbloat: +0.4 ms (ISP has effective AQM)
- Measured via ping -c 10 -i 0.2 to gateway and 1.1.1.1 during a background download
- No root required; ping -f requires root (not usable)
- This is the single most diagnostic signal for "why is my video stuttering"

**Bufferbloat load source (builder's call, settle here):** The T1 scheduled probe (8×5 MB) already saturates the link, so bufferbloat is measured during the T1 probe — no extra download needed. Latency is sampled immediately before, during (mid-probe), and after the probe. Between scheduled probes, the passive ping average and jitter serve as a proxy for bufferbloat trends. The T1 probe's own traffic counts toward the 120 MB/day budget.

**Cold-start behavior (builder's call, settle here):** On first launch or after state loss (e.g., ~/.local/state/nst/ deleted), the panel runs an immediate T1 probe in the background. Until the first probe completes (~8 s), the verdict shows "MEASURING..." and the capacity bar shows 0. The passive T0 signals (latency, signal, rx_dropped) are live immediately and can drive a preliminary verdict (HIGH LATENCY or RADIO DEGRADED) even before the capacity number arrives.

**Occlusion detection (builder's call, settle here):** The panel is a layer-shell surface at layer TOP. Gdk.FrameClock already stops painting when the surface is occluded at the compositor level (Sway handles this for layer-shell surfaces). No Sway IPC tree inspection is needed. The "animate only when visible" gating is handled by the frame clock automatically. The "on battery" gating uses UPower's `OnBattery` property.
## 5. What's left to the builder

The following are intentionally left to the builder's judgment:

1. Exact panel dimensions and layout. The mockups show ~434×172 collapsed and ~560×520 expanded, but the builder should tune these for the 1366×768 screen and the waybar's 32 px bottom bar.

2. Probe scheduling implementation. The 8-hour interval is a target; the builder decides whether to use a systemd timer, a Python GLib.timeout_add_seconds, or a cron job. The key constraint: probe only when idle (passive counters < 5 Mbit/s), and rotate hosts on 429.

3. Heartbeat scroll algorithm. The mockup shows a canvas-based scroll; the builder decides the buffer size (e.g., 200 samples at 1 Hz = 3.3 minutes of history), scroll speed, and whether to use a ring buffer or a deque.

4. Addon module API. The config.toml schema and the Module base class interface are left to the builder. Suggested: update(sample: dict) -> None, render() -> Gtk.Widget, optional animate().

5. Error handling and retry logic. Cloudflare 429, DNS failures, interface down, no network — the builder decides how to surface these in the UI (e.g., "last good: 4 min ago" vs. a red indicator).

6. Testing. The builder should add unit tests for the verdict engine and the measurement math (throughput calculation, rx_dropped rate, bufferbloat delta). Integration tests require a real network interface.

7. Packaging. The design specifies ~/.local/bin/nst + rpm-ostree install -yA gtk4-layer-shell, but the builder could also create a COPR RPM or a Flatpak (if they accept the sandbox limitations on /proc).

8. Icon / app desktop file. Whether to install a .desktop file in ~/.local/share/applications/ and an icon.

9. Logging. Where and how to log (journald, file, stdout). The builder decides based on debugging needs.

10. The "Run speed test now" button. Whether it runs the same 8×5 MB probe or a larger 20 MB probe for a more authoritative number. The mockup shows 8×5 MB; a larger probe on demand gives a more stable result.

## Appendix A: Key measured values (reference for thresholds)

| Metric | Good | Warning | Critical | Measured baseline |
|---|---|---|---|---|
| Download throughput (sustained) | ≥ 30 Mbit/s | 15–30 Mbit/s | < 15 Mbit/s | 38.1 Mbit/s (50 MB, n=6) |
| Upload throughput | ≥ 25 Mbit/s | 8–25 Mbit/s | < 8 Mbit/s | 44.6 Mbit/s (5 MB, n=6) |
| DNS (ms) | ≤ 25 | 25–60 | > 60 | 3.87 ms (curl, median) |
| TCP connect (ms) | ≤ 60 | 60–150 | > 150 | 20.9 ms (median) |
| TLS handshake (ms) | ≤ 150 | 150–300 | > 300 | 63.5 ms (median) |
| TTFB (ms) | ≤ 400 | 400–1000 | > 1000 | 245.2 ms (median, excl. 2 outliers) |
| RTT avg (ms) | ≤ 20 | 20–50 | > 50 | 11.84 ms (1.1.1.1, 30 pkts) |
| RTT max (ms) | ≤ 50 | 50–150 | > 150 | 15.58 ms (1.1.1.1) |
| rx_dropped rate (/s) | ≤ 0.2 | 0.2–1.0 | > 1.0 | 0.072/s (load-independent) |
| Signal (dBm) | ≥ −67 | −67 to −75 | < −75 | −68 to −72 |
| Beacon loss | 0 | 1 | ≥ 2 | 0 (all 7 samples) |
| Bufferbloat LAN (ms) | ≤ 10 | 10–30 | > 30 | +39.9 ms |
| Bufferbloat WAN (ms) | ≤ 5 | 5–15 | > 15 | +0.4 ms |
| Battery health | ≥ 80% | 70–80% | < 70% | 73.97% (1076 cycles) |

## Appendix D: GPU capabilities (verified)

| Item | Value |
|---|---|
| GPU | Intel HD Graphics 620 (Kaby Lake GT2, PCI 8086:5916, i915 driver) |
| Mesa | 26.0.3-4.fc44 (iris DRI driver) |
| OpenGL | 4.6 Core Profile (Mesa 26.0.3), GLES 3.2, accelerated=yes, ~7.8 GB unified memory |
| Vulkan loader | 1.4.341.0-1.fc44, Intel ANV ICD (libvulkan_intel.so) present, LVP software fallback |
| Software renderer | llvmpipe (swrast_dri.so, libgallium) |
| RC6 residency | Enabled, accumulating (GPU idles well) |
| Sway | 1.11 (wlroots 0.19.3) |
| glxinfo | Available (/usr/bin/glxinfo) |
| vulkaninfo | NOT installed |
| gtk4-demo | NOT installed |

**Rendering verdict:** OpenGL via Mesa (iris) is the primary strategy for the ambient starfield layer. Vulkan is a plausible alternative but needs runtime verification. Cairo CPU is unsuitable for full-screen 60 fps (~0.5–1.3 W on this hardware).

## Appendix B: Verified package versions (Fedora 44)

| Package | Version | Notes |
|---|---|---|
| gtk4 | 4.22.5-2.fc44 | Host has 4.22.1 |
| libadwaita | 1.9.4-1.fc44 | Host has 1.9.0 |
| gtk4-layer-shell | 1.3.0-1.fc44 | Not yet installed; deps in base |
| pygobject3 | 3.56.3-1.fc44 | Host has 3.56.2 |
| python3.14 | 3.14.8-1.fc44 | Host has 3.14.3 |
| python-pip | 26.0.1-3.fc44 | Externally-managed (PEP 668) |
| python3-cairo | 1.28.0-5.fc44 | Required by pygobject3 |
| sway | 1.11-3.fc44 | wlroots0.19 dependency |
| waybar | 0.15.0-2.fc44 | Already running |
| sway-systemd | 0.4.1-4.fc44 | Session integration |
| NetworkManager | 1.56.0-1.fc44 | Host bus accessible |
| upower | 1.91.1-1.fc44 | Host bus accessible |
| fwupd | 2.1.1 | D-Bus accessible; CLI host-only |
| tuned | (present) | tuned-ppd serves power profiles |

## Appendix C: Source URLs

- gtk4-layer-shell: https://packages.fedoraproject.org/pkgs/gtk4-layer-shell/gtk4-layer-shell/fedora-44.html
- gtk4-layer-shell API: https://wmww.github.io/gtk4-layer-shell/gtk4-layer-shell-GTK4-Layer-Shell.html
- rpm-ostree admin handbook: https://coreos.github.io/rpm-ostree/administrator-handbook/
- Flatpak sandbox permissions: https://docs.flatpak.org/en/latest/sandbox-permissions.html
- NetworkManager D-Bus (wireless): https://networkmanager.pages.freedesktop.org/NetworkManager/NetworkManager/gdbus-org.freedesktop.NetworkManager.Device.Wireless.html
- Kernel interface statistics: https://www.kernel.org/doc/html/latest/networking/statistics.html
- GTK4 CSS properties: https://docs.gtk.org/gtk4/css-properties.html
- libadwaita docs: https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/
- GTK4 frame clock: https://docs.gtk.org/gdk4/class.FrameClock.html
- waybar custom module: https://man.archlinux.org/man/waybar-custom.5.en
- sway-systemd: https://packages.fedoraproject.org/pkgs/sway-systemd/sway-systemd/fedora-44.html
- Cloudflare speed test: https://github.com/cloudflare/speedtest
- LibreSpeed: https://github.com/librespeed/speedtest
- wlr-layer-shell protocol: https://wayland.app/protocols/wlr-layer-shell-unstable-v1
- Nerd Fonts: https://github.com/ryanoasis/nerd-fonts