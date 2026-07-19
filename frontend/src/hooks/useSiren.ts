/**
 * useSiren.ts — Web Audio API emergency siren hook.
 *
 * Generates a realistic two-tone sweeping industrial siren
 * using oscillators + LFO frequency modulation, with no
 * external audio files required.
 *
 * Usage:
 *   const { play, stop, mute, unmute, muted } = useSiren()
 *   play()      // start siren
 *   stop()      // fade out immediately
 *   mute()      // silence + prevent future plays
 *   unmute()    // re-enable
 */
import { useRef, useCallback, useEffect, useState } from 'react'

function makeDistortionCurve(amount: number): Float32Array<ArrayBuffer> {
  const n = 256
  const curve = new Float32Array(new ArrayBuffer(n * 4))
  for (let i = 0; i < n; i++) {
    const x = (i * 2) / n - 1
    curve[i] = ((Math.PI + amount) * x) / (Math.PI + amount * Math.abs(x))
  }
  return curve
}

interface SirenNodes {
  osc: OscillatorNode
  lfo: OscillatorNode
  gain: GainNode
  ctx: AudioContext
}

export function useSiren() {
  const nodesRef  = useRef<SirenNodes | null>(null)
  const timerRef  = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [muted, setMuted] = useState(false)
  const mutedRef  = useRef(false)

  // Keep mutedRef in sync with state
  useEffect(() => { mutedRef.current = muted }, [muted])

  const stop = useCallback(() => {
    if (timerRef.current) { clearTimeout(timerRef.current); timerRef.current = null }
    if (!nodesRef.current) return
    const { osc, lfo, gain, ctx } = nodesRef.current
    const t = ctx.currentTime
    gain.gain.setTargetAtTime(0, t, 0.15)          // soft fade-out 150 ms
    setTimeout(() => {
      try { osc.stop(); lfo.stop() } catch { /* already stopped */ }
      nodesRef.current = null
    }, 600)
  }, [])

  const play = useCallback((durationMs = 10_000) => {
    if (mutedRef.current)  return
    if (nodesRef.current)  return   // already playing

    try {
      const ctx = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)()

      // ── Carrier oscillator ──────────────────────────────────────────────────
      const osc = ctx.createOscillator()
      osc.type = 'sawtooth'
      osc.frequency.value = 960           // base freq Hz

      // ── LFO for "wee-woo" sweep ─────────────────────────────────────────────
      const lfo = ctx.createOscillator()
      lfo.type = 'sine'
      lfo.frequency.value = 0.75          // sweeps per second

      const lfoGain = ctx.createGain()
      lfoGain.gain.value = 200            // ±200 Hz frequency deviation

      // ── Second harmonic (makes it harsher / more urgent) ───────────────────
      const osc2 = ctx.createOscillator()
      osc2.type = 'square'
      osc2.frequency.value = 1440         // 1.5× carrier
      const gain2 = ctx.createGain()
      gain2.gain.value = 0.04

      // ── Distortion (industrial crunch) ─────────────────────────────────────
      const wave = ctx.createWaveShaper()
      wave.curve = makeDistortionCurve(30)
      wave.oversample = '2x'

      // ── Master gain with fade-in ────────────────────────────────────────────
      const gain = ctx.createGain()
      gain.gain.setValueAtTime(0, ctx.currentTime)
      gain.gain.linearRampToValueAtTime(0.28, ctx.currentTime + 0.3)

      // ── Stereo panner oscillation (subtle movement) ─────────────────────────
      const panner = ctx.createStereoPanner()
      panner.pan.value = 0

      // Connections
      lfo.connect(lfoGain)
      lfoGain.connect(osc.frequency)
      osc.connect(wave)
      osc2.connect(gain2)
      gain2.connect(wave)
      wave.connect(gain)
      gain.connect(panner)
      panner.connect(ctx.destination)

      osc.start(ctx.currentTime)
      osc2.start(ctx.currentTime)
      lfo.start(ctx.currentTime)

      nodesRef.current = { osc, lfo, gain, ctx }

      timerRef.current = setTimeout(stop, durationMs)
    } catch (err) {
      console.warn('[Siren] Web Audio failed:', err)
    }
  }, [stop])

  const mute = useCallback(() => {
    setMuted(true)
    stop()
  }, [stop])

  const unmute = useCallback(() => {
    setMuted(false)
  }, [])

  // Cleanup on unmount
  useEffect(() => () => stop(), [stop])

  return { play, stop, mute, unmute, muted }
}
