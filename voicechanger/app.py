import os
import queue
import subprocess
import sys
import tkinter as tk
import traceback
from pathlib import Path
from tkinter import messagebox, ttk

from voicechanger import engine as audio
from voicechanger.hotkeys import HotkeyListener
from voicechanger.presets import PresetError, load_presets
from voicechanger.settings import error_log_path, load_settings, save_settings

APP_TITLE = "Voice Changer"
PRESETS_PATH = Path(__file__).resolve().parent.parent / "presets.json"
PRESET_COLUMNS = 4
EVENT_POLL_MS = 50
ACTIVE_COLOR = "#7c3aed"
ACTIVE_TEXT_COLOR = "#ffffff"
IDLE_COLOR = "#e5e7eb"
IDLE_TEXT_COLOR = "#111827"
NOISE_GATE_MIN_DB = -80
NOISE_GATE_MAX_DB = -20
ACTION_NEXT = "__next__"
ACTION_PREVIOUS = "__previous__"


def format_hotkey(hotkey):
    parts = [part.strip("<>") for part in hotkey.split("+")]
    return "+".join(part.capitalize() if len(part) > 2 else part.upper() for part in parts)


def open_in_editor(path):
    if sys.platform.startswith("win"):
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


class VoiceChangerApp:
    def __init__(self, root):
        self.root = root
        self.settings = load_settings()
        self.events = queue.Queue()
        self.engine = audio.VoiceEngine(on_error=self._report_audio_error)
        self.hotkeys = HotkeyListener(on_trigger=self.events.put)
        self.presets = []
        self.preset_buttons = {}
        self.active_preset_name = None
        self._last_audio_error = None
        self._build_window()
        self._reload_presets()
        self._poll_events()

    def _build_window(self):
        self.root.title(APP_TITLE)
        self.root.protocol("WM_DELETE_WINDOW", self._quit)
        self.root.columnconfigure(0, weight=1)
        self._build_header()
        self._build_devices()
        self.presets_frame = ttk.Frame(self.root, padding=(10, 0))
        self.presets_frame.grid(row=2, column=0, sticky="nsew")
        self._build_footer()

    def _build_header(self):
        header = ttk.Frame(self.root, padding=10)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        self.status_var = tk.StringVar(value="Arrêté")
        ttk.Label(header, textvariable=self.status_var, font=("Segoe UI", 12, "bold")).grid(row=0, column=0, sticky="w")
        self.toggle_button = ttk.Button(header, text="Démarrer", command=self._toggle_engine)
        self.toggle_button.grid(row=0, column=1)

    def _build_devices(self):
        frame = ttk.LabelFrame(self.root, text="Audio", padding=10)
        frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        frame.columnconfigure(1, weight=1)
        saved_host_api = self.settings["host_api"]
        if saved_host_api not in audio.host_api_names():
            saved_host_api = audio.preferred_host_api()
        self.host_api_var = tk.StringVar(value=saved_host_api)
        self.input_var = tk.StringVar(value=self.settings["input"])
        self.output_var = tk.StringVar(value=self.settings["output"])
        self.monitor_enabled_var = tk.BooleanVar(value=self.settings["monitor_enabled"])
        self.monitor_var = tk.StringVar(value=self.settings["monitor"])
        self.noise_gate_var = tk.DoubleVar(value=self.settings["noise_gate_db"])
        self.host_api_box = self._add_combobox(frame, 0, "API audio", self.host_api_var, audio.host_api_names())
        self.host_api_box.bind("<<ComboboxSelected>>", lambda event: self._refresh_devices())
        self.input_box = self._add_combobox(frame, 1, "Micro", self.input_var, [])
        self.output_box = self._add_combobox(frame, 2, "Sortie vers Discord", self.output_var, [])
        ttk.Checkbutton(frame, text="Retour casque", variable=self.monitor_enabled_var).grid(row=3, column=0, sticky="w", pady=2)
        self.monitor_box = ttk.Combobox(frame, textvariable=self.monitor_var, state="readonly")
        self.monitor_box.grid(row=3, column=1, sticky="ew", pady=2)
        ttk.Label(frame, text="Noise gate (dB)").grid(row=4, column=0, sticky="w", pady=2)
        ttk.Scale(frame, from_=NOISE_GATE_MIN_DB, to=NOISE_GATE_MAX_DB, variable=self.noise_gate_var,
                  command=lambda value: self._apply_noise_gate()).grid(row=4, column=1, sticky="ew", pady=2)
        self._refresh_devices()

    def _add_combobox(self, frame, row, label, variable, values):
        ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", padx=(0, 10), pady=2)
        box = ttk.Combobox(frame, textvariable=variable, values=values, state="readonly")
        box.grid(row=row, column=1, sticky="ew", pady=2)
        return box

    def _build_footer(self):
        footer = ttk.Frame(self.root, padding=10)
        footer.grid(row=3, column=0, sticky="ew")
        ttk.Button(footer, text="Modifier les presets", command=lambda: open_in_editor(PRESETS_PATH)).pack(side="left")
        ttk.Button(footer, text="Recharger les presets", command=self._reload_presets).pack(side="left", padx=5)
        hint = f"Suivant : {format_hotkey(self.settings['next_hotkey'])}   Précédent : {format_hotkey(self.settings['previous_hotkey'])}"
        ttk.Label(footer, text=hint, foreground="#6b7280").pack(side="right")

    def _refresh_devices(self):
        host_api = self.host_api_var.get()
        inputs = audio.list_devices(host_api, "input")
        outputs = audio.list_devices(host_api, "output")
        self.input_box["values"] = inputs
        self.output_box["values"] = outputs
        self.monitor_box["values"] = outputs
        if self.input_var.get() not in inputs:
            self.input_var.set(inputs[0] if inputs else "")
        if self.output_var.get() not in outputs:
            self.output_var.set(audio.guess_cable_output(outputs))
        if self.monitor_var.get() not in outputs:
            self.monitor_var.set(outputs[0] if outputs else "")

    def _reload_presets(self):
        try:
            self.presets = load_presets(PRESETS_PATH)
        except PresetError as error:
            messagebox.showerror(APP_TITLE, str(error))
            return
        self._render_preset_buttons()
        self._register_hotkeys()
        names = [preset.name for preset in self.presets]
        wanted = self.active_preset_name or self.settings["last_preset"]
        self.select_preset(wanted if wanted in names else names[0])

    def _render_preset_buttons(self):
        for child in self.presets_frame.winfo_children():
            child.destroy()
        self.preset_buttons = {}
        categories = list(dict.fromkeys(preset.category for preset in self.presets))
        for row, category in enumerate(categories):
            group = ttk.LabelFrame(self.presets_frame, text=category, padding=5)
            group.grid(row=row, column=0, sticky="ew", pady=3)
            members = [preset for preset in self.presets if preset.category == category]
            for index, preset in enumerate(members):
                self._add_preset_button(group, index, preset)
        self.presets_frame.columnconfigure(0, weight=1)

    def _add_preset_button(self, group, index, preset):
        label = preset.name if not preset.hotkey else f"{preset.name}\n{format_hotkey(preset.hotkey)}"
        button = tk.Button(group, text=label, width=18, height=2, relief="flat", bg=IDLE_COLOR, fg=IDLE_TEXT_COLOR,
                           command=lambda name=preset.name: self.select_preset(name))
        button.grid(row=index // PRESET_COLUMNS, column=index % PRESET_COLUMNS, padx=3, pady=3, sticky="ew")
        group.columnconfigure(index % PRESET_COLUMNS, weight=1)
        self.preset_buttons[preset.name] = button

    def _register_hotkeys(self):
        bindings = {preset.hotkey: preset.name for preset in self.presets if preset.hotkey}
        bindings[self.settings["next_hotkey"]] = ACTION_NEXT
        bindings[self.settings["previous_hotkey"]] = ACTION_PREVIOUS
        self.hotkeys.register(bindings)
        if self.hotkeys.invalid_hotkeys:
            messagebox.showwarning(APP_TITLE, "Raccourcis invalides ignorés : " + ", ".join(self.hotkeys.invalid_hotkeys))

    def select_preset(self, name):
        preset = next((candidate for candidate in self.presets if candidate.name == name), None)
        if preset is None:
            return
        self.engine.set_preset(preset)
        self.active_preset_name = name
        for button_name, button in self.preset_buttons.items():
            is_active = button_name == name
            button.configure(bg=ACTIVE_COLOR if is_active else IDLE_COLOR, fg=ACTIVE_TEXT_COLOR if is_active else IDLE_TEXT_COLOR)
        self._update_status()

    def _step_preset(self, offset):
        names = [preset.name for preset in self.presets]
        current = names.index(self.active_preset_name) if self.active_preset_name in names else 0
        self.select_preset(names[(current + offset) % len(names)])

    def _toggle_engine(self):
        if self.engine.running:
            self.engine.stop()
        else:
            self._start_engine()
        self._update_status()

    def _start_engine(self):
        monitor = self.monitor_var.get() if self.monitor_enabled_var.get() else None
        self.engine.noise_gate_db = self.noise_gate_var.get()
        try:
            self.engine.start(self.host_api_var.get(), self.input_var.get(), self.output_var.get(), monitor)
        except Exception as error:
            self.engine.stop()
            messagebox.showerror(APP_TITLE, f"Impossible de démarrer l'audio :\n{error}\n\nEssaie une autre API audio (MME) ou d'autres périphériques.")
            return
        self._last_audio_error = None
        self._persist_settings()

    def _apply_noise_gate(self):
        self.engine.set_noise_gate(self.noise_gate_var.get())

    def _update_status(self):
        state = "En direct" if self.engine.running else "Arrêté"
        self.status_var.set(f"{state} — {self.active_preset_name or '—'}")
        self.toggle_button.configure(text="Arrêter" if self.engine.running else "Démarrer")

    def _report_audio_error(self, error):
        if str(error) != self._last_audio_error:
            self._last_audio_error = str(error)
            self.events.put(("error", str(error)))

    def _poll_events(self):
        while not self.events.empty():
            self._handle_event(self.events.get_nowait())
        self.root.after(EVENT_POLL_MS, self._poll_events)

    def _handle_event(self, event):
        if isinstance(event, tuple):
            self.status_var.set(f"Erreur audio : {event[1]}")
        elif event == ACTION_NEXT:
            self._step_preset(1)
        elif event == ACTION_PREVIOUS:
            self._step_preset(-1)
        else:
            self.select_preset(event)

    def _persist_settings(self):
        self.settings.update({
            "host_api": self.host_api_var.get(),
            "input": self.input_var.get(),
            "output": self.output_var.get(),
            "monitor_enabled": self.monitor_enabled_var.get(),
            "monitor": self.monitor_var.get(),
            "noise_gate_db": round(self.noise_gate_var.get(), 1),
            "last_preset": self.active_preset_name or self.settings["last_preset"],
        })
        save_settings(self.settings)

    def _quit(self):
        self._persist_settings()
        self.hotkeys.stop()
        self.engine.stop()
        self.root.destroy()


def report_crash(error_type, error, error_traceback):
    details = "".join(traceback.format_exception(error_type, error, error_traceback))
    log_path = error_log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(details, encoding="utf-8")
    messagebox.showerror(APP_TITLE, f"{error}\n\nDétails dans {log_path}")


def main():
    root = tk.Tk()
    root.report_callback_exception = report_crash
    try:
        VoiceChangerApp(root)
    except Exception:
        report_crash(*sys.exc_info())
        root.destroy()
        return
    root.mainloop()
