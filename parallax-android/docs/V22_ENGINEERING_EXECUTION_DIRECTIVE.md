# Parallax Distortion v2.2 — Engineering execution directive

**Role:** Principal Android audio engineer, acoustic-sensing researcher, DSP specialist, sensor-fusion architect, accessibility engineer, and CI release owner.

**Primary objective:** Ship a reliable, reproducible, local-first single-smartphone Android app that retains visual entrainment, provides genuine stereo binaural bell/bowl playback, makes essential controls accessible on the home screen, performs safe calibration under ordinary weak-microphone conditions, and optionally measures real acoustic echoes using the built-in speaker and microphone. Do not claim room mapping, neurotherapy efficacy, latency or sensing precision without physical verification.

## Hard constraints

- Compatible with common Android 8–15 non-root devices, specifically Samsung A14 Android 15. No dependency on a second phone, external speaker, PC, server, private mic recording archive, telemetry, or network.
- Multi-device cooperative sonar is OPTIONAL and deferred: no test, build, or release gate may depend on it.
- Microphone never starts via overlay toggle, boot, hour chime, background scheduler, Quick Settings tile, or unrelated activity. Require explicit visible consent and permission. Route change/permission loss/call cancels safely.
- Persist user-selected audio mode; **never silently reset to Audio off**. Enabling a bell while Audio off must visibly make playback actionable, while honoring user intent.
- Binaural interaural difference requires independent left and right channels and stereo headphones. A single mono bell fed to both channels is a functional regression.
- Synthesis sample amplitude/headroom must avoid clipping and clicks. Never claim medical efficacy, sleep treatment, or neurological improvement from chosen hertz values.
- Sensor outputs must be labeled as estimated radial echo, signal confidence, relative orientation, or unsupported; never advertise object identity or full positioning from one mic.
- Event-driven explicit state snapshots, no hidden APIs, root, unbounded buffers, audio-thread blocking I/O, or network runtime.
- No licensed code copied from third-party research projects without explicit license/legal review.

## Baseline and implementation record

- v2.0 PR #99: `feat/parallax-v2-distinct-package` / package `com.parallax.entrainment.v2`.
- v2.1 PR #100: `feat/parallax-v21-sonar-overlay` / package `com.parallax.entrainment.v21`, spectral visualizer.
- v2.2 PR #101: `feat/parallax-v22-sensing-bells-20261110`, based on v2.1 / package `com.parallax.entrainment.v22`.
- The v2.2 branch already includes home quick controls, independent bell carriers, 16 fundamentals, modal bowl, repeat/sustain tuning, session-only hourly chimes, adaptive calibration, and the explicit one-shot FMCW+IMU experiment.
- Research references, capability limits, measurement requirements: `docs/v2.2-single-device-acoustic-research.md`.

## Implementation / test gates

### Phase 1: Binaural and controls (implemented, physical QA pending)

A1. Home and advanced controls must both expose bells, bowl/carrier modes, fundamental, chime and calibration without navigating hidden menus. Honor TalkBack and large fonts.

A2. Set target=6.0Hz and bell fundamental=528Hz, verify headphone L/R fundamentals are 528/534Hz (subject to instrument partials). Frequency switching is phase-continuous. Optional `Layer` keeps underlying binaural carrier audible.

A3. Sustain 2–60s, repeat 4–300s, optional hourly at the top of hour during an active audible session. A stopped/paused audio service must not sound. For out-of-session chimes, design a **separate** user-visible Android scheduling module; do not silently start mic service or promise exact delivery under Doze.

A4. Do not unexpectedly turn off sound when acoustic settings change. Preserve explicit Audio off choice unless the user enables bell playback from a visible control.

### Phase 2: Calibration (implemented adaptive logic, physical QA pending)

B1. Measure 7 bands using a known, low-level test excitation. Count valid samples, clipping, ambient floor and SNR per band. Process locally, release microphone reliably.

B2. With >=4 reliable bands apply max 6dB attenuation and preserve prior gains in unreliable bands; otherwise reject run and retain prior curve. No boosts into nulls, no forced flattening.

B3. Show actionable reasons: clipping (reduce volume), weak speaker/mic SNR (quiet, reposition, careful volume increase), processing fallback, route change, permission revoked, call active.

B4. Independent test on real device: 125Hz–8kHz bands; before/after; route/volume; lifecycle. Never infer ±1dB accuracy from simulated DSP tests.

### Phase 3: Single-device sonar (experimental, deterministic tests implemented)

C1. Verify built-in 48kHz record/playback paths and availability of raw vs processed mic; calibrate direct speaker-to-mic leakage timing before inferring echoes.

C2. Emit 20ms low-volume 17.5–21.5kHz chirp on explicit consent; correlate with capture. Detect candidate delayed energy, reject weak direct anchor, report approximate range+confidence. Raw PCM ephemeral only.

C3. Characterize 0.5m, 1m, 2m flat reflector and baseline room. Store only user-approved derived numerical diagnostics. Test one phone only.

C4. If 17.5–21.5kHz is not supported, present “hardware/route unsupported” and offer *optional passive audible-band sound/IMU monitoring* rather than silently increasing or lowering high-frequency output into a perceptible range.

C5. Estimate relative device yaw from rotation sensor and flag movement using accelerometer. Do not integrate accelerometer into alleged absolute position before geometric-anchor association.

### Phase 4: Observation geometry and robust spatial sensing (pending)

D1. Add hardware-direct latency-offset measurements and chirp/echo SNR calibration, repeated ping timing, background subtraction, direct-leak cancellation and conservative CFAR peaks. Quantify false detections.

D2. Optional target movement via phase-tracking cross-frame associations; mark static vs moving **only** after repeated calibrated returns. No identity inference or covert occupancy surveillance.

D3. Resolve only radial-range arcs until dual independent microphone channels and their geometry are confirmed. Add directional estimates only with validated microphone TDoA.

D4. Add optional bounded 15-error-state ES-EKF ONLY when an independently observed mapped plane and correct observation Jacobian exist. Check time-base alignment, noise calibration, χ² gate at 3.841 for scalar observations, covariance SPD, initialization and reset consistency. Synthetic motion and physical reflector benchmarks mandatory.

D5. Map planar room boundaries only from repeated valid observations with orientation/translation anchors and confidence; render uncertainty bands and unknown areas. Never hallucinate walls or humans.

### Phase 5: Native optimized path (pending)

E1. Validate pure reference DSP first. Then migrate bounded I/O and signal processing to C++17 Oboe AAudio/OpenSL ES. Favor actual native device sample rates and offered sharing/performance modes; no hard-coded “<8ms” guarantee.

E2. Oboe callbacks: no allocation, mutex, file I/O, log, JNI, sleep or network. SPSC ring buffer with bounded overflow, timestamp alignment, rate conversion in worker when needed.

E3. For optional ESS/Kirkeby: measure device IR and noise; regularize inverse with constrained boosts/maximum gain and time windows; route-specific corrections never applied blindly. Compare to v2.1 peaking EQ on measured audio before changing default.

E4. Later experimentation with offline physics-informed neural models and conventional mic-array beamforming is optional and requires a dataset and measured improvement. No hardware-less “ultrasonic metasurface” claim.

## Build and acceptance

- GitHub Actions must run `gradle --no-daemon testDebugUnitTest lintDebug assembleDebug` with full failure diagnostics and downloadable versioned APK.
- Publish PR review evidence: branch SHA, full unit/lint/assembly result, artifact ID, SHA256, package identifier, and physical device QA status.
- Never merge draft until single-phone hardware test reproduces the critical audio issues and identifies real limits of sonar. If a device cannot sense high-band echoes reliably, **report unsupported**, do not fabricate pass.
- Keep README and linked evidence updated with every module; coordinate changes with Grok's governor, semantic accessibility, adaptive planner and knowledge-graph components through explicit documented interfaces only.
- Document unknowns and next measurable experiments rather than inventing functionality.

**Definition of done:** The binaural and calibration features are usable and regression-tested, the experimental sonar returns real measured candidate echoes or an honest failure, the user can access controls from home, permissions and audio state are safe, and the independently installable APK passes CI. Verified mapping, a full ES-EKF, background chimes and native C++ remain separate explicitly gated work until implemented and tested.

## v2.2.1 continuous audio supervision and visualization corrective directive

- Replace the visible legacy 10-minute polling control with a separate **true continuous microphone-to-playback comparator**. Do not mistake periodic audible test-tone sweeps for continuous measurement.
- Read the **real PCM output** of the active bell/binaural generator *after* synthesis, EQ and volume. Compare its spectral shape against the user-consented microphone's captured output at approximately 300 ms intervals; report a confidence qualifier and inadequate-input conditions.
- The speaker/microphone transfer function and gain are uncalibrated. Do not advertise precise reproduction, phase lock, actual brain/ear stimulation, room maps or stereo-headphone monitoring. Continuous microphone comparison requires the **built-in speaker route**.
- Keep manual EQ precedence. Default monitoring never modifies sound; optional live Auto EQ is strictly cut-only, broadband-evidence-gated and rate-limited. No gain boost after weak, noisy, clipped or missing evidence.
- Make **audio-reactive Parallax visuals** a persisted optional mode independent from the **existing room-test sonar-ring overlay**. Use the native original parallax radial gradients: increase displacement from center and glow/radius by smoothed playback amplitude. Do not add a new sonar style or require microphone permission for visual animation.
- Prevent microphone sharing races with the existing 40-second room calibration, stop/release on audio pauses and route changes, keep explicit notification controls, and avoid background auto-start.
- CI regression gates: phase-independent FFT similarity on simulated matching/discordant sounds, low-input rejection, muted/zero amplitude mapping, Android Lint, and compilation. Hardware acceptance: Samsung A14 Android 15 as in README; single phone only.
