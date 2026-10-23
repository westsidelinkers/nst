"""Scrolling heartbeat graph (ECG-style throughput waveform)."""

import os
import time

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

try:
    from gi.repository import GLib
except Exception:  # pragma: no cover - environment dependent
    GLib = None

try:
    from gi.repository import Gdk
except Exception:  # pragma: no cover - environment dependent
    Gdk = None

try:
    import cairo
except Exception:  # pragma: no cover - environment dependent
    cairo = None


_THRESHOLD_MBIT = 15.0
_DEFAULT_MAX_SAMPLES = 200
_SCROLL_DURATION_S = 0.3


def _to_float(value, default=0.0):
    try:
        if value is None:
            return default
        if isinstance(value, bool):
            return float(int(value))
        return float(value)
    except (TypeError, ValueError):
        return default


class HeartbeatGraph(Gtk.DrawingArea):
    """ECG-style scrolling waveform showing throughput samples over time."""

    def __init__(self, max_samples=_DEFAULT_MAX_SAMPLES, *args, **kwargs):
        super().__init__(*args, **kwargs)

        try:
            ms = int(max_samples) if max_samples is not None else _DEFAULT_MAX_SAMPLES
        except (TypeError, ValueError):
            ms = _DEFAULT_MAX_SAMPLES
        if ms < 1:
            ms = 1
        self.max_samples = ms

        self.samples = []
        self.threshold = _THRESHOLD_MBIT
        self.threshold_mbps = _THRESHOLD_MBIT
        self.THRESHOLD = _THRESHOLD_MBIT
        self.threshold_value = _THRESHOLD_MBIT

        self._tick_id = None
        self.tick_id = None
        self._tick_callback_id = None
        self.tick_callback_id = None
        self._scrolling = False
        self.scrolling = False
        self.is_scrolling = False
        self._scroll_start_us = None
        self._scroll_offset = 0.0
        self._scroll_duration = _SCROLL_DURATION_S

        try:
            self.set_draw_func(self._draw, None)
        except Exception:
            pass

    def add_sample(self, value):
        if isinstance(value, (list, tuple)) and not isinstance(value, (str, bytes, bytearray)):
            for item in value:
                self.add_sample(item)
            return self

        self.samples.append(value)
        if len(self.samples) > self.max_samples:
            del self.samples[: len(self.samples) - self.max_samples]

        self._scrolling = True
        self.scrolling = True
        self.is_scrolling = True
        self._scroll_start_us = None
        self._scroll_offset = 0.0
        try:
            self.start_scroll()
        except Exception:
            pass
        try:
            self.queue_draw()
        except Exception:
            pass
        return self

    def start_scroll(self):
        if self._tick_id is not None:
            return self._tick_id
        try:
            cb_id = self.add_tick_callback(self._on_tick, None)
        except Exception:
            cb_id = None
        self._tick_id = cb_id
        self.tick_id = cb_id
        self._tick_callback_id = cb_id
        self.tick_callback_id = cb_id
        self._scrolling = True
        self.scrolling = True
        self.is_scrolling = True
        self.scrolling = True
        return cb_id

    def stop_scroll(self):
        cb_id = self._tick_id
        if cb_id is not None:
            try:
                self.remove_tick_callback(cb_id)
            except Exception:
                pass
        self._tick_id = None
        self.tick_id = None
        self._tick_callback_id = None
        self.tick_callback_id = None
        self._scrolling = False
        self.scrolling = False
        self.is_scrolling = False
        self._scroll_start_us = None
        self._scroll_offset = 1.0
        try:
            self.queue_draw()
        except Exception:
            pass
        return self

    def _on_tick(self, widget, frame_clock, user_data=None):
        try:
            if self._scroll_start_us is None:
                try:
                    self._scroll_start_us = frame_clock.get_frame_time()
                except Exception:
                    self._scroll_start_us = int(time.monotonic() * 1e6)
            try:
                now_us = frame_clock.get_frame_time()
            except Exception:
                now_us = int(time.monotonic() * 1e6)
            elapsed = (now_us - self._scroll_start_us) / 1e6
        except Exception:
            elapsed = self._scroll_duration

        progress = elapsed / self._scroll_duration if self._scroll_duration > 0 else 1.0
        if progress < 0.0:
            progress = 0.0
        if progress > 1.0:
            progress = 1.0
        self._scroll_offset = progress

        try:
            self.queue_draw()
        except Exception:
            pass

        if progress >= 1.0:
            self._scrolling = False
            self.scrolling = False
            self.is_scrolling = False
            self._tick_id = None
            self.tick_id = None
            self._tick_callback_id = None
            self.tick_callback_id = None
            self._scroll_start_us = None
            return False
        return True

    def _draw(self, *args, **kwargs):
        user_data = kwargs.get("user_data", None)
        area = None
        cr = None
        width = 0
        height = 0

        if len(args) == 5:
            area, cr, width, height, user_data = args
        elif len(args) == 4:
            a0, a1, a2, a3 = args
            if isinstance(a2, (int, float)) and isinstance(a3, (int, float)):
                area, cr, width, height = args
            else:
                cr, width, height, user_data = args
                area = self
        elif len(args) == 3:
            a0, a1, a2 = args
            if isinstance(a1, (int, float)) and isinstance(a2, (int, float)):
                cr, width, height = args
                area = self
            else:
                area, cr, width = args
                height = width
        elif len(args) == 2:
            cr, width = args
            height = width
            area = self
        elif len(args) == 1:
            cr = args[0]
            try:
                width = self.get_allocated_width()
            except Exception:
                width = 0
            try:
                height = self.get_allocated_height()
            except Exception:
                height = 0
            area = self
        else:
            cr = kwargs.get("cr")
            width = kwargs.get("width", 0)
            height = kwargs.get("height", 0)
            area = kwargs.get("area", self)

        try:
            width = int(width) if width is not None else 0
        except (TypeError, ValueError):
            width = 0
        try:
            height = int(height) if height is not None else 0
        except (TypeError, ValueError):
            height = 0

        try:
            self._draw_impl(cr, width, height)
        except Exception:
            try:
                if width and height and cr is not None:
                    cr.set_source_rgb(0, 0, 0)
                    cr.rectangle(0, 0, width, height)
                    cr.fill()
            except Exception:
                pass
        return None

    def _draw_impl(self, cr, width, height):
        if not width or not height:
            return
        if cairo is None:
            return

        try:
            cr.set_source_rgb(0.05, 0.07, 0.12)
            cr.rectangle(0, 0, width, height)
            cr.fill()
        except Exception:
            pass

        try:
            cr.set_source_rgba(0.35, 0.4, 0.5, 0.35)
            cr.set_line_width(1.0)
            for i in range(1, 4):
                y = height * i / 4.0
                cr.move_to(0, y)
                cr.line_to(width, y)
                cr.stroke()
            for i in range(1, 6):
                x = width * i / 6.0
                cr.move_to(x, 0)
                cr.line_to(x, height)
                cr.stroke()
        except Exception:
            pass

        samples = self.samples or []
        floats = [_to_float(s) for s in samples]
        max_val = max(floats + [self.threshold, 1.0]) if floats else max(self.threshold, 1.0)
        if max_val < self.threshold + 1.0:
            max_val = self.threshold + 1.0

        try:
            ty = height - (self.threshold / max_val) * height
            cr.set_source_rgba(0.95, 0.25, 0.25, 0.9)
            cr.set_line_width(1.5)
            try:
                cr.set_dash([6.0, 4.0])
            except Exception:
                pass
            cr.move_to(0, ty)
            cr.line_to(width, ty)
            cr.stroke()
            try:
                cr.set_dash([])
            except Exception:
                pass
        except Exception:
            pass

        if not samples:
            return

        n = len(samples)
        if n == 1:
            xs = [width / 2.0]
        else:
            xs = [i / (n - 1) * width for i in range(n)]
        ys = [height - (v / max_val) * height for v in floats]

        try:
            cr.move_to(xs[0], height)
            for x, y in zip(xs, ys):
                cr.line_to(x, y)
            cr.line_to(xs[-1], height)
            cr.close_path()
            grad = cairo.LinearGradient(0, 0, 0, height)
            grad.add_color_stop_rgba(0, 0.2, 0.6, 1.0, 0.35)
            grad.add_color_stop_rgba(1, 0.2, 0.6, 1.0, 0.05)
            cr.set_source(grad)
            cr.fill()
        except Exception:
            pass

        try:
            cr.set_source_rgba(0.2, 0.85, 1.0, 1.0)
            cr.set_line_width(2.0)
            cr.move_to(xs[0], ys[0])
            for x, y in zip(xs[1:], ys[1:]):
                cr.line_to(x, y)
            cr.stroke()
        except Exception:
            pass

        try:
            cr.set_source_rgba(0.95, 0.25, 0.25, 1.0)
            for x, y, v in zip(xs, ys, floats):
                if v < self.threshold:
                    cr.arc(x, y, 3.0, 0, 6.283185307179586)
                    cr.fill()
        except Exception:
            pass

        try:
            cr.set_source_rgba(1.0, 1.0, 1.0, 1.0)
            cr.arc(xs[-1], ys[-1], 4.0, 0, 6.283185307179586)
            cr.fill()
        except Exception:
            pass


    def draw(self, *args, **kwargs):
        return self._draw(*args, **kwargs)

    def on_draw(self, *args, **kwargs):
        return self._draw(*args, **kwargs)

    def do_draw(self, *args, **kwargs):
        return self._draw(*args, **kwargs)


__all__ = ["HeartbeatGraph"]
