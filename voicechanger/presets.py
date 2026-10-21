import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pedalboard

from voicechanger.dsp import SpectralProcessor, SpectralVoice

ZERO_LATENCY_EFFECTS = {
    "Bitcrush", "Chorus", "Clipping", "Compressor", "Delay", "Distortion", "Gain",
    "HighpassFilter", "HighShelfFilter", "LadderFilter", "Limiter", "LowpassFilter",
    "LowShelfFilter", "NoiseGate", "PeakFilter", "Phaser", "Reverb",
}
LIMITER_THRESHOLD_DB = -1.0
NOISE_GATE_RATIO = 4.0
VALIDATION_SAMPLE_RATE = 48000
VALIDATION_NOISE_GATE_DB = -50.0


class PresetError(Exception):
    pass


@dataclass
class Preset:
    name: str
    category: str = "Divers"
    hotkey: str = ""
    description: str = ""
    voices: list = field(default_factory=list)
    effects: list = field(default_factory=list)
    output_gain_db: float = 0.0


def load_presets(path):
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PresetError(f"Impossible de lire {path} : {error}") from error
    try:
        presets = [Preset(**entry) for entry in raw.get("presets", [])]
    except TypeError as error:
        raise PresetError(f"Champ de preset invalide : {error}") from error
    if not presets:
        raise PresetError(f"Aucun preset défini dans {path}")
    for preset in presets:
        validate_preset(preset)
    return presets


def validate_preset(preset):
    for effect in preset.effects:
        effect_type = effect.get("type")
        if effect_type not in ZERO_LATENCY_EFFECTS:
            raise PresetError(f"Preset « {preset.name} » : effet inconnu ou non temps réel « {effect_type} »")
    try:
        RenderChain(preset, VALIDATION_SAMPLE_RATE, VALIDATION_NOISE_GATE_DB)
    except (TypeError, ValueError, AttributeError) as error:
        raise PresetError(f"Preset « {preset.name} » : paramètre invalide ({error})") from error


class RenderChain:
    def __init__(self, preset, sample_rate, noise_gate_db):
        self.preset = preset
        self.sample_rate = sample_rate
        self._noise_gate = pedalboard.NoiseGate(threshold_db=noise_gate_db, ratio=NOISE_GATE_RATIO)
        self._gate = pedalboard.Pedalboard([self._noise_gate])
        self._spectral = build_spectral_processor(preset)
        self._board = build_board(preset)

    def set_noise_gate(self, threshold_db):
        self._noise_gate.threshold_db = threshold_db

    def process(self, mono_block):
        gated = self._run_board(self._gate, mono_block)
        voiced = self._spectral.process(gated) if self._spectral else gated
        return self._run_board(self._board, voiced)

    def _run_board(self, board, mono_block):
        stereo_shaped = mono_block.astype(np.float32)[np.newaxis, :]
        return board.process(stereo_shaped, self.sample_rate, reset=False)[0]


def build_spectral_processor(preset):
    if not preset.voices:
        return None
    voices = [SpectralVoice(**voice) for voice in preset.voices]
    return SpectralProcessor(voices)


def build_effect(effect):
    parameters = {key: value for key, value in effect.items() if key != "type"}
    effect_class = getattr(pedalboard, effect["type"])
    if "mode" in parameters:
        parameters["mode"] = getattr(effect_class.Mode, parameters["mode"])
    return effect_class(**parameters)


def build_board(preset):
    plugins = [build_effect(effect) for effect in preset.effects]
    plugins.append(pedalboard.Gain(gain_db=preset.output_gain_db))
    plugins.append(pedalboard.Limiter(threshold_db=LIMITER_THRESHOLD_DB))
    return pedalboard.Pedalboard(plugins)
