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

# def bar(value, width=24):
#     value = max(0.0, min(1.0, float(value)))
#     filled = int(round(value * width))
#     return "█" * filled + "░" * (width - filled)

def run(filename: str) -> TrackAnalysisResults:
    # filename = "/home/lucas/dev/brage/data/music/4b82cca3-8c6a-4071-8042-fc6df2dcca52.flac"
    # # filename = "/home/lucas/dev/brage/data/music/436ad421-e439-41be-b98b-b6f30a0b256c.flac"
    # filename = "/home/lucas/dev/brage/data/music/76ff658f-6c13-4157-906f-780cc8759048.flac"

    audio = essentia.standard.MonoLoader(filename=filename)()

    # -------------------------
    # Core analysis
    # -------------------------
    # duration = len(audio) / 44100.0

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
    # avg_rolloff = np.mean(rolloffs)
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

    # # -------------------------
    # # Output
    # # -------------------------
    # print()
    # print("🎵 TRACK ANALYSIS")
    # print("=" * 56)
    # print(f"File         : {filename}")
    # print(f"Duration     : {duration:6.1f} sec")
    # print(f"BPM          : {bpm:6.2f}")
    # print(f"Key          : {key} {scale} (confidence {key_strength:.2f})")
    # print(f"Loudness     : {loudness:6.2f}")
    # print()

    # print("📊 CORE METRICS")
    # print("-" * 56)
    # print(f"Energy       [{bar(min(rms * 3,1))}] {min(rms * 3,1):.2f}")
    # print(f"Danceability [{bar(danceability)}] {danceability:.2f}")
    # print(f"Brightness   [{bar(brightness)}] {brightness:.2f}")
    # print(f"Beat Conf    [{bar(min(beat_confidence,1))}] {beat_confidence:.2f}")
    # print()

    # print("😊 MOOD ESTIMATE")
    # print("-" * 56)
    # print(f"Happy        [{bar(happy)}] {happy:.2f}")
    # print(f"Sad          [{bar(sad)}] {sad:.2f}")
    # print(f"Aggressive   [{bar(aggressive)}] {aggressive:.2f}")
    # print(f"Calm         [{bar(calm)}] {calm:.2f}")

    # moods = {
    #     "Happy": happy,
    #     "Sad": sad,
    #     "Aggressive": aggressive,
    #     "Calm": calm
    # }

    # primary = max(moods, key=moods.get)

    # print()
    # print(f"🎭 Primary Mood: {primary}")
    # print()

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
