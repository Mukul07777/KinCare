// Live vital-sign sources that run in the browser, no app install:
// - Bluetooth heart-rate (standard GATT 0x180D): chest straps, and watches that "broadcast heart rate"
// - Bluetooth pulse oximeter: standard PLX (0x1822) or the common BerryMed fingertip protocol
// - Phone camera: fingertip over lens + flash, pulse from the colour change of blood (PPG)
// - Recorded ICU patient: real PhysioNet BIDMC monitor data, replayed for demos without a device
import type { LiveSource, ReferenceRecord } from "./api";

export type Reading = { pulse?: number; spo2?: number };
export type Handlers = {
  onReading: (r: Reading) => void;
  onWave?: (v: number) => void;
  onStatus: (s: string) => void;
};
export type Stop = () => void;

/* eslint-disable @typescript-eslint/no-explicit-any */
const bt = () => (typeof navigator !== "undefined" ? (navigator as any).bluetooth : undefined);
export const bluetoothSupported = () => !!bt();
export const cameraSupported = () => typeof navigator !== "undefined" && !!navigator.mediaDevices?.getUserMedia;

// IEEE-11073 16-bit SFLOAT used by the PLX profile.
function sfloat(raw: number) {
  let m = raw & 0x0fff;
  let e = raw >> 12;
  if (m >= 0x0800) m -= 0x1000;
  if (e >= 0x08) e -= 0x10;
  if (m === 0x07ff || m === 0x0800 || m === 0x07fe) return NaN;
  return m * 10 ** e;
}

async function connect(device: any, onStatus: Handlers["onStatus"]) {
  onStatus(`Connecting to ${device.name ?? "device"}…`);
  return device.gatt.connect();
}

async function heartRate(h: Handlers): Promise<Stop> {
  const device = await bt().requestDevice({ filters: [{ services: ["heart_rate"] }] });
  const server = await connect(device, h.onStatus);
  const ch = await (await server.getPrimaryService("heart_rate")).getCharacteristic("heart_rate_measurement");
  const listen = (e: any) => {
    const v: DataView = e.target.value;
    const pulse = v.getUint8(0) & 1 ? v.getUint16(1, true) : v.getUint8(1);
    if (pulse > 0) h.onReading({ pulse });
  };
  ch.addEventListener("characteristicvaluechanged", listen);
  await ch.startNotifications();
  h.onStatus(`Live from ${device.name ?? "heart-rate sensor"}`);
  device.addEventListener("gattserverdisconnected", () => h.onStatus("Device disconnected"));
  return () => { ch.removeEventListener("characteristicvaluechanged", listen); device.gatt.disconnect(); };
}

const BERRY_SVC = "49535343-fe7d-4ae5-8fa9-9fafd205e455";
const BERRY_CHR = "49535343-1e4d-4bd9-ba61-23c647249616";

async function oximeter(h: Handlers): Promise<Stop> {
  const device = await bt().requestDevice({
    filters: [{ services: ["pulse_oximeter"] }, { services: [BERRY_SVC] }, { namePrefix: "BerryMed" }, { namePrefix: "Oxi" }],
    optionalServices: ["pulse_oximeter", BERRY_SVC],
  });
  const server = await connect(device, h.onStatus);
  let ch: any;
  let parse: (v: DataView) => void;
  try {
    ch = await (await server.getPrimaryService("pulse_oximeter")).getCharacteristic(0x2a5f); // PLX continuous measurement
    parse = (v) => {
      const spo2 = sfloat(v.getUint16(1, true));
      const pulse = sfloat(v.getUint16(3, true));
      h.onReading({ spo2: isNaN(spo2) ? undefined : Math.round(spo2), pulse: isNaN(pulse) ? undefined : Math.round(pulse) });
    };
  } catch {
    ch = await (await server.getPrimaryService(BERRY_SVC)).getCharacteristic(BERRY_CHR);
    parse = (v) => {
      // 5-byte frames, first byte has the sync bit set.
      for (let i = 0; i + 4 < v.byteLength; i++) {
        if (!(v.getUint8(i) & 0x80)) continue;
        h.onWave?.(v.getUint8(i + 1) & 0x7f);
        const pulse = (v.getUint8(i + 3) & 0x7f) | ((v.getUint8(i + 2) & 0x40) << 1);
        const spo2 = v.getUint8(i + 4);
        if (spo2 !== 127 && pulse !== 255) h.onReading({ pulse, spo2 });
        i += 4;
      }
    };
  }
  const listen = (e: any) => parse(e.target.value);
  ch.addEventListener("characteristicvaluechanged", listen);
  await ch.startNotifications();
  h.onStatus(`Live from ${device.name ?? "pulse oximeter"}`);
  device.addEventListener("gattserverdisconnected", () => h.onStatus("Device disconnected"));
  return () => { ch.removeEventListener("characteristicvaluechanged", listen); device.gatt.disconnect(); };
}

/** Pulse from the phone camera: average red of each frame rises and falls with every heartbeat. */
async function camera(h: Handlers, video: HTMLVideoElement): Promise<Stop> {
  const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment", width: 320, height: 240 }, audio: false });
  const track = stream.getVideoTracks()[0];
  try { await track.applyConstraints({ advanced: [{ torch: true } as any] }); } catch { /* no torch: daylight still works */ }
  video.srcObject = stream;
  video.muted = true;
  video.playsInline = true;
  await video.play();

  const canvas = document.createElement("canvas");
  canvas.width = 40; canvas.height = 30;
  const ctx = canvas.getContext("2d", { willReadFrequently: true })!;
  const buf: { t: number; v: number }[] = [];
  let raf = 0, lastEmit = 0, stopped = false;
  h.onStatus("Cover the back camera and flash fully with a fingertip. Hold still.");

  const frame = () => {
    if (stopped) return;
    ctx.drawImage(video, 0, 0, 40, 30);
    const d = ctx.getImageData(0, 0, 40, 30).data;
    let r = 0, g = 0;
    for (let i = 0; i < d.length; i += 4) { r += d[i]; g += d[i + 1]; }
    r /= d.length / 4; g /= d.length / 4;
    const t = performance.now();
    const covered = r > 90 && r > g * 1.6;
    if (!covered) {
      buf.length = 0;
      h.onStatus("No finger detected. Cover the camera and flash completely.");
    } else {
      buf.push({ t, v: r });
      while (buf.length && t - buf[0].t > 12000) buf.shift();
      // Detrend with a 1 s moving average, then invert (more blood = darker).
      const sig = buf.map((p, i) => {
        let s = 0, n = 0;
        for (let j = i; j >= 0 && p.t - buf[j].t < 1000; j--) { s += buf[j].v; n++; }
        return { t: p.t, v: s / n - p.v };
      });
      h.onWave?.(sig[sig.length - 1].v);
      if (t - lastEmit > 1000 && buf.length > 0 && t - buf[0].t > 6000) {
        lastEmit = t;
        // Same steps as api/ppg.py, which is scored on real ICU pleth (BIDMC). A beat must reach 30% of the tallest peak.
        const floor = 0.3 * Math.max(...sig.map((p) => p.v));
        const peaks: number[] = [];
        for (let i = 2; i < sig.length - 2; i++) {
          const v = sig[i].v;
          if (v > floor && v >= sig[i - 1].v && v >= sig[i - 2].v && v > sig[i + 1].v && v > sig[i + 2].v &&
              (!peaks.length || sig[i].t - peaks[peaks.length - 1] > 330)) peaks.push(sig[i].t);
        }
        const iv = peaks.slice(1).map((p, i) => p - peaks[i]).sort((a, b) => a - b);
        if (iv.length >= 5) {
          const med = iv[Math.floor(iv.length / 2)];
          const spread = (iv[Math.floor(iv.length * 0.75)] - iv[Math.floor(iv.length * 0.25)]) / med;
          // A real pulse repeats itself one beat later; noise doesn't.
          const lag = Math.round(med / ((sig[sig.length - 1].t - sig[0].t) / (sig.length - 1)));
          let energy = 0, corr = 0;
          for (let i = 0; i < sig.length; i++) {
            energy += sig[i].v ** 2;
            if (i + lag < sig.length) corr += sig[i].v * sig[i + lag].v;
          }
          if (spread < 0.3 && corr / (energy || 1) > 0.4) {
            h.onReading({ pulse: Math.round(60000 / med) });
            h.onStatus("Reading pulse from camera. Keep still.");
          } else h.onStatus("Signal is noisy. Press lighter and hold still.");
        }
      } else if (t - buf[0].t <= 6000) h.onStatus("Finger detected. Measuring…");
    }
    raf = requestAnimationFrame(frame);
  };
  raf = requestAnimationFrame(frame);
  return () => { stopped = true; cancelAnimationFrame(raf); stream.getTracks().forEach((x) => x.stop()); video.srcObject = null; };
}

/** Replays a real ICU patient (PhysioNet BIDMC): monitor pulse + SpO2 every second, pleth wave at its own rate.
 *  `seek(second)` jumps, e.g. to the minute with the worst oxygen. */
export function replay(h: Handlers, rec: ReferenceRecord, from = 0): Stop & { seek: (s: number) => void; position: () => number } {
  let sec = from;
  let w = Math.floor(from * rec.hz);
  h.onStatus(`Replaying ICU patient ${rec.id} (${rec.age ?? "?"} ${rec.gender ?? ""}, ${rec.location ?? "ICU"}). Real recorded data, PhysioNet BIDMC.`);
  // Records ingested with numerics only have no waveform; then only the numbers are replayed.
  const wave = setInterval(() => {
    if (rec.pleth.length) for (let i = 0; i < rec.hz / 25; i++) h.onWave?.(rec.pleth[w++ % rec.pleth.length]);
  }, 40);
  const tick = setInterval(() => {
    const n = rec.numerics[sec % rec.numerics.length];
    h.onReading({ pulse: n.pulse ?? n.hr ?? undefined, spo2: n.spo2 ?? undefined });
    sec++;
  }, 1000);
  const stop = (() => { clearInterval(wave); clearInterval(tick); }) as Stop & { seek: (s: number) => void; position: () => number };
  stop.seek = (s) => { sec = s; w = Math.floor(s * rec.hz); };
  stop.position = () => sec % rec.numerics.length;
  return stop;
}

export async function startSource(id: LiveSource, h: Handlers, opts: { video?: HTMLVideoElement; record?: ReferenceRecord; from?: number } = {}): Promise<Stop> {
  if (id === "ble_hr") return heartRate(h);
  if (id === "ble_oximeter") return oximeter(h);
  if (id === "camera") return camera(h, opts.video!);
  return replay(h, opts.record!, opts.from);
}
