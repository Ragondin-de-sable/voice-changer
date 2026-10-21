import threading
from collections import deque

import numpy as np
import sounddevice as sd

from voicechanger.presets import RenderChain

BLOCK_SIZE = 256
DEFAULT_NOISE_GATE_DB = -50.0
MONITOR_QUEUE_BLOCKS = 16
WASAPI_HOST_API = "Windows WASAPI"
CABLE_OUTPUT_HINT = "CABLE Input"


def host_api_names():
    return [api["name"] for api in sd.query_hostapis()]


def preferred_host_api():
    names = host_api_names()
    if WASAPI_HOST_API in names:
        return WASAPI_HOST_API
    return names[0]


def list_devices(host_api_name, kind):
    channel_key = "max_input_channels" if kind == "input" else "max_output_channels"
    if host_api_name not in host_api_names():
        return []
    host_api_index = host_api_names().index(host_api_name)
    return [
        device["name"]
        for device in sd.query_devices()
        if device["hostapi"] == host_api_index and device[channel_key] > 0
    ]


def find_device_index(host_api_name, name, kind):
    channel_key = "max_input_channels" if kind == "input" else "max_output_channels"
    host_api_index = host_api_names().index(host_api_name)
    for index, device in enumerate(sd.query_devices()):
        if device["hostapi"] == host_api_index and device["name"] == name and device[channel_key] > 0:
            return index
    raise ValueError(f"Périphérique introuvable : {name}")


def guess_cable_output(outputs):
    for name in outputs:
        if CABLE_OUTPUT_HINT.lower() in name.lower():
            return name
    return outputs[0] if outputs else ""


def extra_settings_for(host_api_name):
    if host_api_name == WASAPI_HOST_API:
        return sd.WasapiSettings(auto_convert=True)
    return None


class MonitorFeed:
    def __init__(self):
        self._blocks = deque(maxlen=MONITOR_QUEUE_BLOCKS)
        self._remainder = np.zeros(0, dtype=np.float32)

    def push(self, block):
        self._blocks.append(block.copy())

    def pull(self, frames):
        collected = [self._remainder]
        available = len(self._remainder)
        while available < frames and self._blocks:
            block = self._blocks.popleft()
            collected.append(block)
            available += len(block)
        audio = np.concatenate(collected)
        if len(audio) < frames:
            audio = np.concatenate((audio, np.zeros(frames - len(audio), dtype=np.float32)))
        self._remainder = audio[frames:]
        return audio[:frames]


class VoiceEngine:
    def __init__(self, on_error):
        self._on_error = on_error
        self._lock = threading.Lock()
        self._chain = None
        self._preset = None
        self._stream = None
        self._monitor_stream = None
        self._monitor_feed = None
        self.noise_gate_db = DEFAULT_NOISE_GATE_DB
        self.sample_rate = None

    @property
    def running(self):
        return self._stream is not None

    def start(self, host_api_name, input_name, output_name, monitor_name=None):
        self.stop()
        input_index = find_device_index(host_api_name, input_name, "input")
        output_index = find_device_index(host_api_name, output_name, "output")
        output_info = sd.query_devices(output_index)
        self.sample_rate = int(output_info["default_samplerate"])
        output_channels = min(2, output_info["max_output_channels"])
        extra = extra_settings_for(host_api_name)
        self._rebuild_chain()
        self._stream = sd.Stream(
            device=(input_index, output_index),
            samplerate=self.sample_rate,
            blocksize=BLOCK_SIZE,
            channels=(1, output_channels),
            dtype="float32",
            latency="low",
            extra_settings=(extra, extra) if extra else None,
            callback=self._process_callback,
        )
        self._stream.start()
        if monitor_name:
            self._start_monitor(host_api_name, monitor_name, extra)

    def _start_monitor(self, host_api_name, monitor_name, extra):
        monitor_index = find_device_index(host_api_name, monitor_name, "output")
        channels = min(2, sd.query_devices(monitor_index)["max_output_channels"])
        self._monitor_feed = MonitorFeed()
        self._monitor_stream = sd.OutputStream(
            device=monitor_index,
            samplerate=self.sample_rate,
            blocksize=BLOCK_SIZE,
            channels=channels,
            dtype="float32",
            latency="low",
            extra_settings=extra,
            callback=self._monitor_callback,
        )
        self._monitor_stream.start()

    def stop(self):
        for stream in (self._stream, self._monitor_stream):
            if stream is not None:
                stream.stop()
                stream.close()
        self._stream = None
        self._monitor_stream = None
        self._monitor_feed = None

    def set_preset(self, preset):
        self._preset = preset
        self._rebuild_chain()

    def set_noise_gate(self, threshold_db):
        self.noise_gate_db = threshold_db
        with self._lock:
            chain = self._chain
        if chain is not None:
            chain.set_noise_gate(threshold_db)

    def _rebuild_chain(self):
        if self._preset is None or self.sample_rate is None:
            return
        chain = RenderChain(self._preset, self.sample_rate, self.noise_gate_db)
        with self._lock:
            self._chain = chain

    def _process_callback(self, indata, outdata, frames, time, status):
        with self._lock:
            chain = self._chain
        try:
            mono = indata[:, 0] if chain is None else chain.process(indata[:, 0])
        except Exception as error:
            outdata.fill(0)
            self._on_error(error)
            return
        outdata[:] = mono[:, np.newaxis]
        feed = self._monitor_feed
        if feed is not None:
            feed.push(mono)

    def _monitor_callback(self, outdata, frames, time, status):
        feed = self._monitor_feed
        if feed is None:
            outdata.fill(0)
            return
        outdata[:] = feed.pull(frames)[:, np.newaxis]
