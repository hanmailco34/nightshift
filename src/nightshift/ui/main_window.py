"""tkinter main window.

Layout:
- Top bar: mode radio (day/night), per-monitor toggle, extended-range toggle.
- Body: a ttk.Notebook with one MonitorPage per monitor when per-monitor is
  on; otherwise a single global MonitorPage.
- Bottom: placeholder for cycle-02 (schedule / tray / autostart).

Slider behavior:
- Dragging a slider re-applies the gamma ramp through a 200ms debounce.
- Releasing the slider (<ButtonRelease-1>) flushes the pending apply and
  persists the config.
- Touching a slider auto-switches the current mode to that slider's mode.

Extended-range toggle flow:
- OFF -> ON opens a modal dialog explaining the one-time GdiICMGammaRange
  registry change + Windows reboot, lets the user copy the PowerShell
  command to their clipboard, and on confirmation runs a self-diagnostic
  (deep-warm apply on the primary monitor, then restore). If the diagnostic
  fails the toggle is reverted.
- ON -> OFF is free: clamp turns back on; the saved K values are preserved.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Dict, List, Optional

from .. import MAX_KELVIN
from ..color import controller as ctl
from ..color import gamma
from ..color.temperature import kelvin_to_rgb
from ..config import store
from ..display.monitors import Monitor, list_monitors
from ..platform.registry import read_gdi_icm_gamma_range

CLAMPED_MIN_K = 3300
UNCLAMPED_MIN_K = 1500
DEBOUNCE_MS = 200

PS_COMMAND = (
    "Set-ItemProperty -Path "
    "'HKLM:\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\ICM' "
    "-Name GdiICMGammaRange -Value 256 -Type DWord"
)


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
            variable=self.day_var, showvalue=False, resolution=50, length=420,
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
            variable=self.night_var, showvalue=False, resolution=50, length=420,
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
        self.root.geometry("760x600")
        try:
            self.root.iconbitmap(default="")  # use system default
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

        self._build_ui()
        self._refresh_pages()
        if self.monitors:
            self._apply_now()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---- UI construction -------------------------------------------------
    def _build_ui(self) -> None:
        top = ttk.Frame(self.root, padding=(14, 12))
        top.pack(fill="x")

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

        self.body = ttk.Frame(self.root)
        self.body.pack(fill="both", expand=True, padx=14, pady=(8, 4))

        foot = ttk.Frame(self.root, padding=(14, 6))
        foot.pack(fill="x")
        ttk.Label(foot, foreground="gray",
                  text="스케줄 / 트레이 / 자동실행은 cycle-02에서 추가됩니다."
                  ).pack(side="left")

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
        if not self.monitors:
            return
        failed = self.controller.apply_current(
            [m.device_name for m in self.monitors])
        if failed:
            print(f"nightshift: apply_kelvin returned False for {failed}")

    def _save(self) -> None:
        self.cfg["per_monitor_enabled"] = self.controller.per_monitor_enabled
        self.cfg["extended_range"] = self.controller.extended_range
        self.cfg["global"] = dict(self.controller.global_targets)
        self.cfg["monitors"] = {d: dict(v)
                                 for d, v in self.controller.monitors.items()}
        store.save(self.cfg)

    # ---- top-bar callbacks ----------------------------------------------
    def _on_mode_change(self) -> None:
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

    # ---- extended-range opt-in dialog -----------------------------------
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
            self.root.update()  # required so clipboard sticks after window closes
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

    # ---- shutdown --------------------------------------------------------
    def _on_close(self) -> None:
        if self.monitors:
            self.controller.reset_all([m.device_name for m in self.monitors])
        self._save()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def run() -> int:
    win = MainWindow()
    win.run()
    return 0
