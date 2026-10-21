import numpy as np

FRAME_SIZE = 1024
HOP_SIZE = 256
CEPSTRUM_LIFTER = 40
ENVELOPE_FLOOR = 1e-9
SEMITONES_PER_OCTAVE = 12.0


def semitones_to_ratio(semitones):
    return 2.0 ** (semitones / SEMITONES_PER_OCTAVE)


class SpectralVoice:
    MODE_NORMAL = "normal"
    MODE_ROBOT = "robot"
    MODE_WHISPER = "whisper"

    def __init__(self, pitch=0.0, formant=0.0, gain=1.0, mode=MODE_NORMAL):
        self.pitch_ratio = semitones_to_ratio(pitch)
        self.formant_ratio = semitones_to_ratio(formant)
        self.gain = gain
        self.mode = mode
        self._bins = FRAME_SIZE // 2 + 1
        self._bin_indices = np.arange(self._bins)
        self._expected_phase_step = 2.0 * np.pi * HOP_SIZE * self._bin_indices / FRAME_SIZE
        self._last_phase = np.zeros(self._bins)
        self._phase_accumulator = np.zeros(self._bins)
        self._random = np.random.default_rng()

    def process_spectrum(self, spectrum):
        magnitude = np.abs(spectrum)
        true_bins = self._estimate_true_bins(np.angle(spectrum))
        envelope = spectral_envelope(magnitude)
        flat_magnitude = magnitude / envelope
        shifted_magnitude, shifted_bins = self._shift_bins(flat_magnitude, true_bins)
        warped_envelope = np.interp(self._bin_indices / self.formant_ratio, self._bin_indices, envelope, right=ENVELOPE_FLOOR)
        output_magnitude = shifted_magnitude * warped_envelope * self.gain
        return output_magnitude * np.exp(1j * self._synthesis_phase(shifted_bins))

    def _estimate_true_bins(self, phase):
        phase_delta = phase - self._last_phase - self._expected_phase_step
        self._last_phase = phase
        wrapped_delta = np.mod(phase_delta + np.pi, 2.0 * np.pi) - np.pi
        return self._bin_indices + wrapped_delta * FRAME_SIZE / (2.0 * np.pi * HOP_SIZE)

    def _shift_bins(self, magnitude, true_bins):
        target = np.round(self._bin_indices * self.pitch_ratio).astype(int)
        valid = target < self._bins
        shifted_magnitude = np.zeros(self._bins)
        shifted_bins = np.zeros(self._bins)
        np.add.at(shifted_magnitude, target[valid], magnitude[valid])
        shifted_bins[target[valid]] = true_bins[valid] * self.pitch_ratio
        return shifted_magnitude, shifted_bins

    def _synthesis_phase(self, shifted_bins):
        if self.mode == self.MODE_ROBOT:
            return np.zeros(self._bins)
        if self.mode == self.MODE_WHISPER:
            return self._random.uniform(-np.pi, np.pi, self._bins)
        self._phase_accumulator += 2.0 * np.pi * HOP_SIZE * shifted_bins / FRAME_SIZE
        return self._phase_accumulator


def spectral_envelope(magnitude):
    log_magnitude = np.log(magnitude + ENVELOPE_FLOOR)
    cepstrum = np.fft.irfft(log_magnitude)
    cepstrum[CEPSTRUM_LIFTER:-CEPSTRUM_LIFTER] = 0.0
    return np.exp(np.fft.rfft(cepstrum).real) + ENVELOPE_FLOOR


class VoiceMixer:
    def __init__(self, voices):
        self.voices = voices
        self._window = np.hanning(FRAME_SIZE)
        self._input_frame = np.zeros(FRAME_SIZE)
        self._output_frame = np.zeros(FRAME_SIZE)
        self._normalization = HOP_SIZE / np.sum(self._window ** 2)

    def process_hop(self, hop):
        self._input_frame = np.concatenate((self._input_frame[HOP_SIZE:], hop))
        spectrum = np.fft.rfft(self._input_frame * self._window)
        mixed_spectrum = np.zeros_like(spectrum)
        for voice in self.voices:
            mixed_spectrum += voice.process_spectrum(spectrum)
        synthesized = np.fft.irfft(mixed_spectrum, FRAME_SIZE) * self._window * self._normalization
        self._output_frame += synthesized
        output = self._output_frame[:HOP_SIZE].copy()
        self._output_frame = np.concatenate((self._output_frame[HOP_SIZE:], np.zeros(HOP_SIZE)))
        return output


class SpectralProcessor:
    def __init__(self, voices):
        self._mixer = VoiceMixer(voices)
        self._pending_input = np.zeros(0)
        self._pending_output = np.zeros(HOP_SIZE)

    def process(self, block):
        self._pending_input = np.concatenate((self._pending_input, block))
        produced = [self._pending_output]
        while len(self._pending_input) >= HOP_SIZE:
            produced.append(self._mixer.process_hop(self._pending_input[:HOP_SIZE]))
            self._pending_input = self._pending_input[HOP_SIZE:]
        available = np.concatenate(produced)
        self._pending_output = available[len(block):]
        return available[:len(block)]
