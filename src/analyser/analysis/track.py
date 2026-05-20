import essentia
import essentia.standard
import math
import numpy as np

from pydantic import BaseModel

class TrackAnalysisResults(BaseModel):
    bpm: int
    key: str
    key_scale: str
    key_confidence: float
    loudness: int
    energy: float
    danceability: float
    mood_happy: float
    mood_sad: float
    mood_aggresive: float
    mood_calm: float


def run(filename: str) -> TrackAnalysisResults:
    audio = essentia.standard.MonoLoader(filename=filename)()

    # -------------------------
    # Core analysis
    # -------------------------

    rhythm = essentia.standard.RhythmExtractor2013(method="multifeature")
    bpm, beats, beat_confidence, _, _ = rhythm(audio)

    key, scale, key_strength = essentia.standard.KeyExtractor()(audio)

    loudness = essentia.standard.Loudness()(audio)

    rms = math.sqrt(sum(x * x for x in audio) / len(audio))

    # -------------------------
    # Spectral analysis
    # -------------------------
    spectrum = essentia.standard.Spectrum()
    window = essentia.standard.Windowing(type="hann")
    centroid = essentia.standard.Centroid(range=22050)
    rolloff = essentia.standard.RollOff()
    flatness = essentia.standard.Flatness()

    frame_size = 2048
    hop = 1024

    centroids = []
    rolloffs = []
    flatnesses = []

    for frame in essentia.standard.FrameGenerator(audio, frameSize=frame_size, hopSize=hop, startFromZero=True):
        spec = spectrum(window(frame))

        centroids.append(centroid(spec))
        rolloffs.append(rolloff(spec))
        flatnesses.append(flatness(spec))

    avg_centroid = np.mean(centroids)
    avg_flatness = np.mean(flatnesses)

    brightness = min(avg_centroid / 5000.0, 1.0)
    danceability = min((bpm / 140.0) * (0.6 + 0.4 * min(beat_confidence, 1.0)), 1.0)

    # -------------------------
    # Mood heuristics
    # -------------------------

    # Happy = major key + brighter + faster
    happy = (
        (0.45 if scale == "major" else 0.15)
        + (brightness * 0.30)
        + min(bpm / 160.0, 1.0) * 0.25
    )

    # Sad = minor + lower tempo + darker
    sad = (
        (0.45 if scale == "minor" else 0.10)
        + (1.0 - brightness) * 0.30
        + (1.0 - min(bpm / 160.0, 1.0)) * 0.25
    )

    # Aggressive = loud + bright + noisy + fast
    aggressive = (
        min(loudness / 35.0, 1.0) * 0.35
        + brightness * 0.25
        + avg_flatness * 0.20
        + min(bpm / 180.0, 1.0) * 0.20
    )

    # Calm = low tempo + darker + lower loudness
    calm = (
        (1.0 - min(bpm / 160.0, 1.0)) * 0.40
        + (1.0 - brightness) * 0.30
        + (1.0 - min(loudness / 35.0, 1.0)) * 0.30
    )

    # Clamp
    happy = min(max(happy, 0), 1)
    sad = min(max(sad, 0), 1)
    aggressive = min(max(aggressive, 0), 1)
    calm = min(max(calm, 0), 1)

    return TrackAnalysisResults(
        bpm=int(round(bpm)),
        key=key,
        key_scale=scale,
        key_confidence=key_strength,
        loudness=int(round(loudness)),
        energy=min(rms * 3,1),
        danceability=danceability,
        mood_happy=float(happy),
        mood_sad=float(sad),
        mood_aggresive=float(aggressive),
        mood_calm=float(calm),
    )
