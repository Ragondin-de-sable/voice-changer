from pynput import keyboard


class HotkeyListener:
    def __init__(self, on_trigger):
        self._on_trigger = on_trigger
        self._listener = None
        self.invalid_hotkeys = []

    def register(self, bindings):
        self.stop()
        self.invalid_hotkeys = []
        mapping = {}
        for hotkey, action in bindings.items():
            if not hotkey:
                continue
            try:
                keyboard.HotKey.parse(hotkey)
            except ValueError:
                self.invalid_hotkeys.append(hotkey)
                continue
            mapping[hotkey] = self._make_callback(action)
        if mapping:
            self._listener = keyboard.GlobalHotKeys(mapping)
            self._listener.start()

    def _make_callback(self, action):
        def callback():
            self._on_trigger(action)
        return callback

    def stop(self):
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
