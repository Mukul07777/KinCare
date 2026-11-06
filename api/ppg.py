"""Pulse from a PPG waveform: the same steps as the phone-camera reader in web/lib/live.ts
(estimatePulse), kept in Python so it can be scored against real ICU monitor data (BIDMC)."""


def estimate(t_ms: list[float], raw: list[float]) -> int | None:
    """`raw` is camera-style brightness (darker = more blood). Returns bpm, or None if the window is too noisy."""
    if len(raw) < 10 or t_ms[-1] - t_ms[0] < 6000:
        return None
    # Detrend with a trailing 1 s moving average, then invert so each heartbeat is a peak.
    sig, j, run = [], 0, 0.0
    for i, v in enumerate(raw):
        run += v
        while t_ms[i] - t_ms[j] >= 1000:
            run -= raw[j]
            j += 1
        sig.append(run / (i - j + 1) - v)
    # A beat must reach 30% of the window's tallest peak, so dicrotic notches and ripples don't count.
    floor = 0.3 * max(sig)
    peaks: list[float] = []
    for i in range(2, len(sig) - 2):
        v = sig[i]
        if v > floor and v >= sig[i - 1] and v >= sig[i - 2] and v > sig[i + 1] and v > sig[i + 2] and (not peaks or t_ms[i] - peaks[-1] > 330):
            peaks.append(t_ms[i])
    iv = sorted(b - a for a, b in zip(peaks, peaks[1:]))
    if len(iv) < 5:
        return None
    med = iv[len(iv) // 2]
    spread = (iv[int(len(iv) * 0.75)] - iv[int(len(iv) * 0.25)]) / med
    # A real pulse repeats itself one beat later; noise doesn't.
    lag = round(med / ((t_ms[-1] - t_ms[0]) / (len(t_ms) - 1)))
    energy = sum(x * x for x in sig) or 1.0
    rhythm = sum(sig[i] * sig[i + lag] for i in range(len(sig) - lag)) / energy
    return round(60000 / med) if spread < 0.3 and rhythm > 0.4 else None


def validate(pleth: list[float], hz: float, truth: list[int | None], window_s: int = 12, step_s: int = 5) -> dict:
    """Score `estimate` on one recording against the monitor's 1 Hz pulse."""
    t = [i * 1000 / hz for i in range(len(pleth))]
    raw = [-p for p in pleth]  # monitor pleth rises with blood volume; camera brightness falls
    errs, tried = [], 0
    for end in range(window_s, len(truth), step_s):
        a, b = int((end - window_s) * hz), int(end * hz)
        if b > len(raw) or not truth[end]:
            continue
        tried += 1
        est = estimate(t[a:b], raw[a:b])
        if est is not None:
            errs.append(abs(est - truth[end]))
    return {"windows": tried, "estimated": len(errs), "errors": errs}
