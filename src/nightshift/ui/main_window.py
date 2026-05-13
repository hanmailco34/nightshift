"""tkinter main window for nightshift (cycle-02).

Layout:
- Top bar: mode radio, per-monitor toggle, extended-range toggle.
- Body (left): monitor pages (Notebook tabs when per-monitor is on; a single
  global page when off).
- Side (right): schedule / autostart / fullscreen settings cards.
- Bottom: status bar (current mode + K, schedule mode, optional failure text).

Window close (X) hides to the tray; quitting only happens from the tray
"종료" menu item (the one place we reset gamma).

cycle-02 additions over cycle-01:
- Schedule + autostart + fullscreen integration via ``schedule.engine``,
  ``platform.autostart``, ``platform.fullscreen``.
- System tray via ``ui.tray``; tray menu handlers are marshalled to the tk
  main thread with ``root.after(0, ...)``.
- 5-second linear K interpolation on mode change (in ``schedule.engine``).
  Slider drags call ``scheduler.cancel_transition()`` so user input wins.
"""

from __future__ import annotations

import re
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk
from typing import Dict, List, Optional

from .. import MAX_KELVIN
from ..color import controller as ctl
from ..color import gamma
from ..color.temperature import kelvin_to_rgb
from ..config import store
from ..display.monitors import Monitor, list_monitors
from ..platform import autostart, fullscreen
from ..platform.registry import read_gdi_icm_gamma_range
from ..schedule import engine
from .tray import Tray

CLAMPED_MIN_K = 3300
UNCLAMPED_MIN_K = 1500
DEBOUNCE_MS = 200
FULLSCREEN_POLL_MS = 300
NEXT_LABEL_REFRESH_MS = 60_000

PS_COMMAND = (
    "Set-ItemProperty -Path "
    "'HKLM:\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\ICM' "
    "-Name GdiICMGammaRange -Value 256 -Type DWord"
)

_HHMM_RE = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")


def _rgb_to_hex(rgb) -> str:
    r, g, b = rgb
    return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"


class MonitorPage(ttk.Frame):
    """day/night sliders + preview boxes for one device (or the global page)."""

    def __init__(self, parent, device_name: Optional[str], header: str,
                 on_change, on_release, current_min_k: int):
        super().__init__(parent, padding=12)
        self.device_name = device_name
        self._on_change = on_change
        self._on_release = on_release
        self._refreshing = False
        self._build(header, current_min_k)

    def _build(self, header: str, min_k: int) -> None:
        ttk.Label(self, text=header, font=("Segoe UI", 11, "bold")
                  ).grid(row=0, column=0, columnspan=2, sticky="w")

        self.day_var = tk.IntVar(value=max(6500, min_k))
        self.night_var = tk.IntVar(value=max(3300, min_k))

        ttk.Label(self, text="주간 (Day)").grid(row=1, column=0, sticky="w",
                                                  pady=(10, 0))
        self.day_label = ttk.Label(self, text=f"{self.day_var.get()} K")
        self.day_label.grid(row=1, column=1, sticky="e", pady=(10, 0))
        self.day_scale = tk.Scale(
            self, from_=min_k, to=MAX_KELVIN, orient="horizontal",
            variable=self.day_var, showvalue=False, resolution=50, length=380,
            command=lambda v: self._on_slider("day", int(float(v))))
        self.day_scale.grid(row=2, column=0, columnspan=2, sticky="ew")
        self.day_scale.bind("<ButtonRelease-1>",
                            lambda _e: self._on_release_evt("day"))
        self.day_preview = tk.Frame(
            self, height=44, bg=_rgb_to_hex(kelvin_to_rgb(self.day_var.get())))
        self.day_preview.grid(row=3, column=0, columnspan=2, sticky="ew",
                              pady=(4, 14))

        ttk.Label(self, text="야간 (Night)").grid(row=4, column=0, sticky="w")
        self.night_label = ttk.Label(self, text=f"{self.night_var.get()} K")
        self.night_label.grid(row=4, column=1, sticky="e")
        self.night_scale = tk.Scale(
            self, from_=min_k, to=MAX_KELVIN, orient="horizontal",
            variable=self.night_var, showvalue=False, resolution=50, length=380,
            command=lambda v: self._on_slider("night", int(float(v))))
        self.night_scale.grid(row=5, column=0, columnspan=2, sticky="ew")
        self.night_scale.bind("<ButtonRelease-1>",
                              lambda _e: self._on_release_evt("night"))
        self.night_preview = tk.Frame(
            self, height=44, bg=_rgb_to_hex(kelvin_to_rgb(self.night_var.get())))
        self.night_preview.grid(row=6, column=0, columnspan=2, sticky="ew",
                                pady=(4, 0))

        self.columnconfigure(0, weight=1)

    def _on_slider(self, which: str, value: int) -> None:
        if self._refreshing:
            return
        if which == "day":
            self.day_label.configure(text=f"{value} K")
            self.day_preview.configure(bg=_rgb_to_hex(kelvin_to_rgb(value)))
        else:
            self.night_label.configure(text=f"{value} K")
            self.night_preview.configure(bg=_rgb_to_hex(kelvin_to_rgb(value)))
        self._on_change(self.device_name, which, value)

    def _on_release_evt(self, which: str) -> None:
        self._on_release(self.device_name, which)

    def set_values(self, day_k: int, night_k: int) -> None:
        self._refreshing = True
        try:
            self.day_var.set(day_k)
            self.night_var.set(night_k)
        finally:
            self._refreshing = False
        self.day_label.configure(text=f"{self.day_var.get()} K")
        self.night_label.configure(text=f"{self.night_var.get()} K")
        self.day_preview.configure(
            bg=_rgb_to_hex(kelvin_to_rgb(self.day_var.get())))
        self.night_preview.configure(
            bg=_rgb_to_hex(kelvin_to_rgb(self.night_var.get())))

    def update_min(self, min_k: int) -> None:
        self.day_scale.configure(from_=min_k)
        self.night_scale.configure(from_=min_k)


class MainWindow:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("nightshift")
        self.root.geometry("960x600")
        try:
            self.root.iconbitmap(default="")
        except tk.TclError:
            pass

        self.cfg = store.load()
        self.monitors: List[Monitor] = []
        try:
            self.monitors = list_monitors()
        except OSError as exc:
            messagebox.showerror("nightshift",
                                 f"모니터 목록을 가져오지 못했습니다: {exc}")

        if self.monitors:
            if store.ensure_monitor_entries(
                    self.cfg, [m.device_name for m in self.monitors]):
                store.save(self.cfg)

        self.controller = ctl.from_config(self.cfg)
        self.pages: Dict[Optional[str], MonitorPage] = {}
        self._debounce_job: Optional[str] = None

        # cycle-02 state
        self._paused = False
        self._fullscreen_active = False
        self._first_minimize = True
        self._fullscreen_after: Optional[str] = None
        self._next_label_after: Optional[str] = None

        # Coordinators
        self.scheduler = engine.Scheduler(
            self.controller,
            get_devices=lambda: [m.device_name for m in self.monitors],
            root=self.root,
            get_cfg=lambda: self.cfg,
            on_mode_change=self._on_external_mode_change,
        )
        self.tray = Tray(
            on_open=lambda: self.root.after(0, self._tray_open),
            on_toggle_pause=lambda: self.root.after(0, self._tray_toggle_pause),
            on_night_now=lambda: self.root.after(0, self._tray_night_now),
            on_quit=lambda: self.root.after(0, self._tray_quit),
            is_paused=lambda: self._paused,
        )

        self._build_ui()
        self._refresh_pages()
        if self.monitors:
            # Snap to the current target mode immediately, no interpolation.
            target = engine.current_target_mode(datetime.now(), self.cfg)
            self.controller.set_mode(target)
            self.mode_var.set(target)
            self._apply_now()

        autostart.sync_with_config(self.cfg)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---- UI construction -------------------------------------------------
    def _build_ui(self) -> None:
        # top
        top = ttk.Frame(self.root, padding=(14, 12))
        top.pack(side="top", fill="x")

        self.mode_var = tk.StringVar(value=self.controller.mode)
        ttk.Label(top, text="현재 모드:").pack(side="left")
        ttk.Radiobutton(top, text="주간", variable=self.mode_var, value="day",
                         command=self._on_mode_change
                         ).pack(side="left", padx=(8, 0))
        ttk.Radiobutton(top, text="야간", variable=self.mode_var, value="night",
                         command=self._on_mode_change
                         ).pack(side="left", padx=(6, 18))

        self.per_var = tk.BooleanVar(value=self.controller.per_monitor_enabled)
        ttk.Checkbutton(top, text="모니터별 개별 설정",
                         variable=self.per_var, command=self._on_per_change
                         ).pack(side="left", padx=(0, 18))

        self.ext_var = tk.BooleanVar(value=self.controller.extended_range)
        ttk.Checkbutton(top, text="확장 색온도 범위 (1500K까지)",
                         variable=self.ext_var, command=self._on_extended_change
                         ).pack(side="left")

        ttk.Separator(self.root, orient="horizontal").pack(fill="x", padx=14)

        # status bar (bottom — packed early so right/left fill remaining)
        self.status_var = tk.StringVar(value="")
        self.status_label = ttk.Label(
            self.root, textvariable=self.status_var, foreground="gray",
            padding=(14, 6), anchor="w")
        self.status_label.pack(side="bottom", fill="x")

        # side card (right)
        self.side = ttk.Frame(self.root, padding=(0, 8, 14, 8))
        self.side.pack(side="right", fill="y")
        self._build_side_card()

        # body (left, takes the remainder)
        self.body = ttk.Frame(self.root)
        self.body.pack(side="left", fill="both", expand=True,
                       padx=(14, 8), pady=(8, 4))

        # Pause banner — created hidden, packed on demand above side+body.
        self.pause_banner = tk.Label(
            self.root, text="", bg="#f1c40f", fg="#2c3e50",
            font=("Segoe UI", 11, "bold"), padx=14, pady=8, anchor="w")

    def _build_side_card(self) -> None:
        # Schedule
        sched = ttk.LabelFrame(self.side, text="스케줄", padding=10)
        sched.pack(fill="x", pady=(0, 8))

        self.sched_mode_var = tk.StringVar(
            value="astral" if self.cfg["toggles"]["use_sunset"] else "manual")
        ttk.Radiobutton(sched, text="수동 시간", variable=self.sched_mode_var,
                         value="manual", command=self._on_schedule_mode_change
                         ).grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(sched, text="일출/일몰", variable=self.sched_mode_var,
                         value="astral", command=self._on_schedule_mode_change
                         ).grid(row=0, column=1, sticky="w")

        ttk.Label(sched, text="주간 시작").grid(row=1, column=0, sticky="w",
                                                   pady=(8, 0))
        self.day_start_var = tk.StringVar(
            value=str(self.cfg["schedule"].get("day_start", "07:00")))
        e = ttk.Entry(sched, textvariable=self.day_start_var, width=8)
        e.grid(row=1, column=1, sticky="e", pady=(8, 0))
        e.bind("<FocusOut>", lambda _e: self._on_schedule_field_changed())
        e.bind("<Return>", lambda _e: self._on_schedule_field_changed())

        ttk.Label(sched, text="야간 시작").grid(row=2, column=0, sticky="w")
        self.night_start_var = tk.StringVar(
            value=str(self.cfg["schedule"].get("night_start", "21:00")))
        e = ttk.Entry(sched, textvariable=self.night_start_var, width=8)
        e.grid(row=2, column=1, sticky="e")
        e.bind("<FocusOut>", lambda _e: self._on_schedule_field_changed())
        e.bind("<Return>", lambda _e: self._on_schedule_field_changed())

        ttk.Label(sched, text="위도").grid(row=3, column=0, sticky="w",
                                               pady=(8, 0))
        self.lat_var = tk.StringVar(value=str(self.cfg["location"]["lat"]))
        e = ttk.Entry(sched, textvariable=self.lat_var, width=10)
        e.grid(row=3, column=1, sticky="e", pady=(8, 0))
        e.bind("<FocusOut>", lambda _e: self._on_schedule_field_changed())
        e.bind("<Return>", lambda _e: self._on_schedule_field_changed())

        ttk.Label(sched, text="경도").grid(row=4, column=0, sticky="w")
        self.lon_var = tk.StringVar(value=str(self.cfg["location"]["lon"]))
        e = ttk.Entry(sched, textvariable=self.lon_var, width=10)
        e.grid(row=4, column=1, sticky="e")
        e.bind("<FocusOut>", lambda _e: self._on_schedule_field_changed())
        e.bind("<Return>", lambda _e: self._on_schedule_field_changed())

        ttk.Button(sched, text="적용",
                   command=self._on_schedule_field_changed
                   ).grid(row=5, column=0, columnspan=2, sticky="e",
                          pady=(10, 0))

        self.next_label = ttk.Label(sched, text="", foreground="dimgray",
                                      font=("Segoe UI", 8))
        self.next_label.grid(row=6, column=0, columnspan=2, sticky="w",
                              pady=(8, 0))
        sched.columnconfigure(0, weight=1)

        # Autostart
        auto = ttk.LabelFrame(self.side, text="자동 실행", padding=10)
        auto.pack(fill="x", pady=(0, 8))
        self.autostart_var = tk.BooleanVar(
            value=self.cfg["toggles"]["autostart"])
        ttk.Checkbutton(auto, text="Windows 시작 시 자동 실행",
                         variable=self.autostart_var,
                         command=self._on_autostart_change).pack(anchor="w")

        # Other toggles
        other = ttk.LabelFrame(self.side, text="기타", padding=10)
        other.pack(fill="x")
        self.disable_fs_var = tk.BooleanVar(
            value=self.cfg["toggles"]["disable_on_fullscreen"])
        ttk.Checkbutton(other, text="전체화면 앱에서 비활성화",
                         variable=self.disable_fs_var,
                         command=self._on_disable_fs_change).pack(anchor="w")

    # ---- monitor pages ---------------------------------------------------
    def _current_min_k(self) -> int:
        return UNCLAMPED_MIN_K if self.controller.extended_range else CLAMPED_MIN_K

    def _refresh_pages(self) -> None:
        for child in self.body.winfo_children():
            child.destroy()
        self.pages.clear()

        min_k = self._current_min_k()

        if self.per_var.get() and self.monitors:
            nb = ttk.Notebook(self.body)
            nb.pack(fill="both", expand=True)
            for m in self.monitors:
                page = MonitorPage(
                    nb, m.device_name,
                    f"{m.label}  ({m.width}x{m.height})",
                    self._on_slider_change, self._on_slider_release, min_k)
                tgt = self.controller.monitors.get(
                    m.device_name, self.controller.global_targets)
                page.set_values(int(tgt["day_k"]), int(tgt["night_k"]))
                nb.add(page, text=f"Monitor {m.index + 1}")
                self.pages[m.device_name] = page
        else:
            page = MonitorPage(
                self.body, None, "전체 모니터 (글로벌)",
                self._on_slider_change, self._on_slider_release, min_k)
            g = self.controller.global_targets
            page.set_values(int(g["day_k"]), int(g["night_k"]))
            page.pack(fill="both", expand=True)
            self.pages[None] = page

    # ---- slider callbacks ------------------------------------------------
    def _on_slider_change(self, device: Optional[str], which: str,
                          value: int) -> None:
        # User input wins over any in-flight interpolation.
        self.scheduler.cancel_transition()
        if self.mode_var.get() != which:
            self.mode_var.set(which)
            self.controller.set_mode(which)  # type: ignore[arg-type]
        self.controller.set_temperature(
            device, which, value)  # type: ignore[arg-type]
        if self._debounce_job is not None:
            self.root.after_cancel(self._debounce_job)
        self._debounce_job = self.root.after(DEBOUNCE_MS, self._apply_now)

    def _on_slider_release(self, device: Optional[str], which: str) -> None:
        if self._debounce_job is not None:
            self.root.after_cancel(self._debounce_job)
            self._debounce_job = None
        self._apply_now()
        self._save()

    def _apply_now(self) -> None:
        self._debounce_job = None
        if not self.monitors or self._fullscreen_active or self._paused:
            self._refresh_status()
            return
        failed = self.controller.apply_current(
            [m.device_name for m in self.monitors])
        self._refresh_status(failed)

    def _save(self) -> None:
        self.cfg["per_monitor_enabled"] = self.controller.per_monitor_enabled
        self.cfg["extended_range"] = self.controller.extended_range
        self.cfg["global"] = dict(self.controller.global_targets)
        self.cfg["monitors"] = {d: dict(v)
                                 for d, v in self.controller.monitors.items()}
        store.save(self.cfg)

    # ---- top-bar callbacks ----------------------------------------------
    def _on_mode_change(self) -> None:
        self.scheduler.cancel_transition()
        self.controller.set_mode(self.mode_var.get())  # type: ignore[arg-type]
        self._apply_now()
        self._save()

    def _on_per_change(self) -> None:
        self.controller.set_per_monitor_enabled(self.per_var.get())
        if self.controller.per_monitor_enabled:
            for m in self.monitors:
                if m.device_name not in self.controller.monitors:
                    self.controller.monitors[m.device_name] = dict(
                        self.controller.global_targets)
        self._refresh_pages()
        self._apply_now()
        self._save()

    def _on_extended_change(self) -> None:
        if not self.ext_var.get():
            self.controller.set_extended_range(False)
            self._refresh_pages()
            self._apply_now()
            self._save()
            return
        if not self._show_extended_dialog():
            self.ext_var.set(False)
            return
        self.controller.set_extended_range(True)
        self._refresh_pages()
        self._apply_now()
        self._save()

    # ---- side-card callbacks --------------------------------------------
    def _on_schedule_mode_change(self) -> None:
        self.cfg["toggles"]["use_sunset"] = (
            self.sched_mode_var.get() == "astral")
        store.save(self.cfg)
        self._refresh_next_label_now()
        self._refresh_status()

    def _on_schedule_field_changed(self) -> None:
        # Validate + persist. Silently ignore invalid entries (revert var).
        ds, ns = self.day_start_var.get().strip(), self.night_start_var.get().strip()
        if _HHMM_RE.match(ds) and _HHMM_RE.match(ns):
            self.cfg["schedule"]["day_start"] = ds
            self.cfg["schedule"]["night_start"] = ns
        else:
            self.day_start_var.set(self.cfg["schedule"]["day_start"])
            self.night_start_var.set(self.cfg["schedule"]["night_start"])

        try:
            lat = float(self.lat_var.get().strip())
            lon = float(self.lon_var.get().strip())
            self.cfg["location"]["lat"] = lat
            self.cfg["location"]["lon"] = lon
        except ValueError:
            self.lat_var.set(str(self.cfg["location"]["lat"]))
            self.lon_var.set(str(self.cfg["location"]["lon"]))

        store.save(self.cfg)
        self._refresh_next_label_now()
        self._refresh_status()

    def _on_autostart_change(self) -> None:
        self.cfg["toggles"]["autostart"] = bool(self.autostart_var.get())
        store.save(self.cfg)
        autostart.sync_with_config(self.cfg)

    def _on_disable_fs_change(self) -> None:
        self.cfg["toggles"]["disable_on_fullscreen"] = bool(
            self.disable_fs_var.get())
        store.save(self.cfg)

    # ---- extended-range opt-in dialog (unchanged from cycle-01) ---------
    def _show_extended_dialog(self) -> bool:
        primary = next((m for m in self.monitors if m.primary),
                        self.monitors[0] if self.monitors else None)
        if primary is None:
            messagebox.showerror(
                "nightshift",
                "모니터가 감지되지 않아 자가 진단을 할 수 없습니다.")
            return False

        win = tk.Toplevel(self.root)
        win.title("확장 색온도 범위")
        win.transient(self.root)
        win.grab_set()
        win.geometry("560x400")
        win.resizable(False, False)

        ttk.Label(win, text="확장 색온도 범위 (1500K까지)",
                  font=("Segoe UI", 12, "bold")
                  ).pack(pady=(14, 4), padx=16, anchor="w")
        ttk.Label(win, wraplength=520, justify="left",
                  text=("Windows는 기본적으로 강한 색온도 변화(대략 3300K 미만)를 "
                        "거부합니다. 더 따뜻한 색을 쓰려면 한 번만 관리자 권한으로 "
                        "레지스트리 값을 설정하고 Windows를 재부팅해야 합니다. "
                        "(f.lux 설치 프로그램도 같은 방식)")
                  ).pack(padx=16, anchor="w")

        cur = read_gdi_icm_gamma_range()
        state_text = (
            "현재 상태: GdiICMGammaRange 값이 설정되어 있지 않음"
            if cur is None
            else f"현재 상태: GdiICMGammaRange = {cur}"
                 + (" (확장 모드용 값)" if cur == 256 else "")
        )
        ttk.Label(win, text=state_text, foreground="dimgray"
                  ).pack(padx=16, pady=(10, 4), anchor="w")

        ttk.Label(win,
                  text="1) 관리자 권한 PowerShell에서 다음 명령 실행:",
                  font=("Segoe UI", 9, "bold")
                  ).pack(padx=16, pady=(8, 2), anchor="w")
        cmd_box = tk.Text(win, height=4, wrap="word")
        cmd_box.insert("1.0", PS_COMMAND)
        cmd_box.configure(state="disabled")
        cmd_box.pack(padx=16, fill="x")

        ttk.Label(win,
                  text="2) Windows 재부팅 후 아래 \"이미 설정함 + 재부팅 완료\" 클릭.",
                  font=("Segoe UI", 9, "bold")
                  ).pack(padx=16, pady=(8, 4), anchor="w")

        result = {"ok": False}

        def copy_cmd() -> None:
            self.root.clipboard_clear()
            self.root.clipboard_append(PS_COMMAND)
            self.root.update()
            messagebox.showinfo("nightshift", "클립보드에 복사했습니다.",
                                 parent=win)

        def confirm() -> None:
            prev_k = self.controller.target_for(primary.device_name)
            prev_clamp = not self.controller.extended_range
            ok = False
            try:
                ok = gamma.apply_kelvin(primary.device_name, 2000,
                                         clamp_to_windows_limit=False)
            except OSError:
                ok = False
            try:
                gamma.apply_kelvin(primary.device_name, prev_k,
                                    clamp_to_windows_limit=prev_clamp)
            except OSError:
                pass
            if not ok:
                messagebox.showwarning(
                    "nightshift",
                    "자가 진단 실패. GdiICMGammaRange가 아직 256이 아니거나 Windows "
                    "재부팅이 필요합니다. 관리자 명령을 실행하고 재부팅한 후 다시 "
                    "시도해 주세요.",
                    parent=win)
                return
            result["ok"] = True
            win.destroy()

        btns = ttk.Frame(win)
        btns.pack(side="bottom", fill="x", padx=16, pady=14)
        ttk.Button(btns, text="명령 복사", command=copy_cmd).pack(side="left")
        ttk.Button(btns, text="취소", command=win.destroy
                   ).pack(side="right")
        ttk.Button(btns, text="이미 설정함 + 재부팅 완료",
                   command=confirm).pack(side="right", padx=(0, 8))

        self.root.wait_window(win)
        return result["ok"]

    # ---- background ticks -----------------------------------------------
    def _fullscreen_tick(self) -> None:
        if self.monitors and self.cfg["toggles"]["disable_on_fullscreen"] and not self._paused:
            visible = fullscreen.is_fullscreen_app_visible(self.monitors)
            if visible and not self._fullscreen_active:
                self._fullscreen_active = True
                self.controller.reset_all(
                    [m.device_name for m in self.monitors])
            elif not visible and self._fullscreen_active:
                self._fullscreen_active = False
                self.controller.apply_current(
                    [m.device_name for m in self.monitors])
            self._refresh_status()
        elif self._fullscreen_active:
            # toggle was turned off mid-fullscreen — restore
            self._fullscreen_active = False
            self.controller.apply_current(
                [m.device_name for m in self.monitors])
            self._refresh_status()
        self._fullscreen_after = self.root.after(
            FULLSCREEN_POLL_MS, self._fullscreen_tick)

    def _refresh_next_label_now(self) -> None:
        try:
            nt = engine.next_transition(datetime.now(), self.cfg)
            target = engine.current_target_mode(datetime.now(), self.cfg)
            kind = "야간" if target == "day" else "주간"
            self.next_label.configure(text=f"다음 {kind} 전환: {nt.strftime('%H:%M')}")
        except Exception:
            self.next_label.configure(text="")

    def _refresh_next_label_loop(self) -> None:
        self._refresh_next_label_now()
        self._next_label_after = self.root.after(
            NEXT_LABEL_REFRESH_MS, self._refresh_next_label_loop)

    def _refresh_status(self, failed: Optional[List[str]] = None) -> None:
        mode_label = "주간" if self.controller.mode == "day" else "야간"
        sched_label = "일몰감지" if self.cfg["toggles"]["use_sunset"] else "수동"
        primary = next((m for m in self.monitors if m.primary),
                        self.monitors[0] if self.monitors else None)
        k_text = ""
        if primary:
            k = self.controller.target_for(primary.device_name)
            k_text = f" {k}K"
        if self._paused:
            base = "일시중지 — 모든 모니터 정상색"
            fg = "dimgray"
        elif self._fullscreen_active:
            base = f"전체화면 감지 — 임시 정상색 (모드 {mode_label})"
            fg = "dimgray"
        else:
            base = f"{mode_label}{k_text} - {sched_label} 스케줄"
            fg = "gray"
        if failed:
            base += f"   |   적용 실패: {', '.join(failed)}"
            fg = "#c0392b"
        self.status_var.set(base)
        self.status_label.configure(foreground=fg)

    # ---- external mode change (from scheduler interpolation finish) ------
    def _on_external_mode_change(self, mode: str) -> None:
        # Keep the top-bar radio in sync when the scheduler auto-transitions.
        if self.mode_var.get() != mode:
            self.mode_var.set(mode)
        self._refresh_status()

    # ---- pause banner ----------------------------------------------------
    def _show_pause_banner(self) -> None:
        self.pause_banner.configure(
            text="⏸  일시중지됨 — 모든 모니터 정상색. 트레이에서 다시 시작하세요.")
        try:
            self.pause_banner.pack(side="top", fill="x", before=self.side)
        except tk.TclError:
            self.pause_banner.pack(side="top", fill="x")

    def _hide_pause_banner(self) -> None:
        self.pause_banner.pack_forget()

    # ---- tray handlers (run on tk main thread via after) ----------------
    def _tray_open(self) -> None:
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def _tray_toggle_pause(self) -> None:
        if self._paused:
            self._paused = False
            self._hide_pause_banner()
            self.scheduler.resume()
            target = engine.current_target_mode(datetime.now(), self.cfg)
            self.controller.set_mode(target)
            self.mode_var.set(target)
            self._apply_now()
        else:
            self._paused = True
            self._show_pause_banner()
            self.scheduler.pause()
            if self.monitors:
                self.controller.reset_all(
                    [m.device_name for m in self.monitors])
        self._refresh_status()

    def _tray_night_now(self) -> None:
        self.scheduler.cancel_transition()
        if self._paused:
            self._paused = False
            self._hide_pause_banner()
            self.scheduler.resume()
        self.mode_var.set("night")
        # Don't pre-set controller.mode — let the transition end-step do it
        # so on_mode_change fires correctly.
        self.scheduler.begin_transition_now("night")
        self._refresh_status()

    def _tray_quit(self) -> None:
        self._do_quit()

    # ---- shutdown -------------------------------------------------------
    def _on_close(self) -> None:
        # cycle-02: closing the window minimises to tray instead of resetting.
        if self._first_minimize:
            self._first_minimize = False
            self.tray.notify("nightshift는 트레이에서 계속 실행됩니다. "
                             "트레이 메뉴 '종료'로 완전히 끄세요.")
        self.root.withdraw()

    def _do_quit(self) -> None:
        self.scheduler.stop()
        if self._fullscreen_after is not None:
            try:
                self.root.after_cancel(self._fullscreen_after)
            except tk.TclError:
                pass
        if self._next_label_after is not None:
            try:
                self.root.after_cancel(self._next_label_after)
            except tk.TclError:
                pass
        if self.monitors:
            self.controller.reset_all(
                [m.device_name for m in self.monitors])
        try:
            self.tray.stop()
        except Exception:
            pass
        self.root.destroy()

    def run(self) -> None:
        self.tray.start()
        self.scheduler.start()
        self._refresh_next_label_loop()
        self._fullscreen_tick()
        self._refresh_status()
        self.root.mainloop()


def run() -> int:
    win = MainWindow()
    win.run()
    return 0
