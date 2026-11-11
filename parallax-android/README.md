# Parallax Distortion 2.0 — Acoustic & Healing Profiles

Development update based on `fix/parallax-overlay-nav-bar-insets` at
`592fbda1830276dea39c4286b4a73da8c4f6f6c8`, preserving the 1.10 overlay and ducking fixes.

Open **Settings menu → Acoustic & Healing Profiles**. Enable session audio in the
main settings, then enable bells or adjust EQ. The nine bundled bell fundamentals
are **174, 285, 396, 417, 528, 639, 741, 852 and 963 Hz**. These are conventional
solfeggio-style listening choices, not validated treatment prescriptions. No runtime
network access, YouTube integration, accounts, recording uploads or saved PCM.

## Calibration and control

- **Calibrate Room & Speakers:** 40 seconds, comprising 5 seconds of ambient
  measurement and seven 5-second reference tones at 125–8000 Hz. Hold the phone
  still in a quiet room at a comfortable media volume. Session tones fade down
  during measurement and resume afterward.
- The result is a **combined speaker/room/microphone response estimate** at the
  phone's position. It cannot independently identify those three responses or
  establish flat sound at a distant listener. Unprocessed input is preferred;
  devices without it use voice-recognition input and report the approximation.
- Hann-windowed spectral power measurements subtract the ambient floor. Every
  band must exceed 10 dB SNR, have sufficient samples and avoid clipping. Route
  and volume changes, calls, permission loss and audio errors reject the run.
  Previous EQ is preserved on failure. High bands are reduced relative to the
  median by at most 6 dB; deep nulls are never boosted. Broad measurements do not
  identify every narrow room resonance. Calibration is bypassed on other routes.
- **Continuous Auto-Polling Correction:** explicit user opt-in, with an ongoing
  notification and Stop action. After the first calibration it waits 10 minutes
  between 40-second audible probes, then moves each base band by at most 0.5 dB.
  Microphone and probe track are released during the wait. No boot restart,
  sticky restart, wake lock or exact alarm. Android may defer checks while asleep.
  Battery saver or ≤15% battery stops subsequent polling; re-enable manually.
- **Manual EQ:** seven bands, −12 to +6 dB in 0.5 dB increments. Moving a slider
  locks that band's absolute gain, overriding automatic results even if a
  calibration finishes concurrently. The base correction remains visible.
  “Return all bands to automatic” unlocks them. Configuration persists locally.
  Changes reach the audio worker at the next buffer and settle smoothly over
  roughly 200 ms. Fixed headroom and a final sample clamp bound the output.
- Bell synthesis uses hum/prime/tierce/quint/nominal partials at ratios
  0.5/1/1.2/1.5/2, with distinct exponential decays and softened attacks/releases.
  Preset frequency changes preserve phase; enable/disable crossfades with the
  original binaural generator. Bells repeat every four seconds.

## Architecture

`AcousticBus` publishes immutable configuration events. UI and measurement workers
publish changes; the existing audio worker consumes snapshots once per buffer.
`AcousticDsp` is Android-independent analysis, bell synthesis and stereo peaking EQ.
`AcousticService` owns all microphone/probe resources on a separate worker and uses
nonblocking device I/O. `AcousticSettingsActivity` owns permission requests and
accessible native controls. No root, hidden API, telemetry or external service.

The microphone foreground service is started only from a visible activity after
permission is granted, with `microphone|mediaPlayback` types. It is separate from
the existing overlay service so scheduled overlays cannot accidentally activate
the microphone. Stopping an overlay does not stop an explicitly enabled acoustic
polling session; use the acoustic notification or settings Stop control.

## Build and tests

JDK 17, Android SDK 35 and Gradle 8.11.1:

```sh
cd parallax-android
gradle --no-daemon testDebugUnitTest lintDebug assembleDebug
```

The root workflow `.github/workflows/parallax-android-build.yml` runs these checks
and uploads `parallax-distortion-debug-apk`. The nested `.github` workflow is not
used by GitHub Actions. Tests exercise spectral estimation, rejection, peak-only
correction, micro-step limits, manual precedence, stereo isolation, measured EQ
attenuation, bell continuity and rapid EQ changes.

### Physical-device release checklist (not replaced by JVM tests)

1. Deny/revoke microphone permission: bells/manual EQ still work; no crash or new correction.
2. Complete a 40-second calibration on a quiet built-in-speaker route; inspect base gains.
3. Repeat with silence, noise, clipping, a call, media-volume changes and route changes;
   confirm old correction survives and the microphone indicator clears.
4. Cancel during each phase, background/rotate the screen, stop from notification,
   and start again; ensure only one worker owns the microphone.
5. Lock a band during calibration and during polling; its audible gain must stay manual.
6. Play all nine profiles, change presets live and toggle bells; check clicks and clipping.
7. Verify ten-minute polling, battery saver and low-battery exit on Android 15;
   measure battery consumption and AudioTrack underruns with a real device.
8. Check TalkBack, large fonts, dark/light themes and system-bar insets.
9. Compare before/after response using an independent calibrated microphone at the
   intended listening position. Do not claim acoustic accuracy from synthetic tests.

## Design references

- [Android foreground-service restrictions](https://developer.android.com/develop/background-work/services/fgs/restrictions-bg-start)
- [Android AudioRecord](https://developer.android.com/reference/android/media/AudioRecord)
- [Bill Hibbert: basic principles of bell tuning](https://www.hibberts.co.uk/basic-principles-of-bell-tuning/)
- [Bill Hibbert: identifying bell partials](https://www.hibberts.co.uk/identifying-bell-partials/)

Bell partials inform the timbre; the nine chosen fundamentals are curated product
presets. Neither these references nor this implementation establishes healing efficacy.

## Termux: fetch the tested APK

With the GitHub CLI installed and authenticated, this creates a reusable downloader.
It selects the latest successful build on this feature branch and prints integrity
information immediately after download. It does not build Android binaries in Termux.

```sh
cat > "$HOME/get-parallax-v2.sh" <<'SH'
#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
repo=onnxscibroccoli/broccoli-core
run_id=$(gh run list --repo "$repo" --branch feat/parallax-acoustic-v2 \
  --workflow parallax-android-build.yml --status success --limit 1 --json databaseId \
  --jq '.[0].databaseId // empty')
[ -n "$run_id" ] || { echo 'No successful v2 build is available yet.'; exit 1; }
artifact_dir=$(mktemp -d "$HOME/parallax-v2.XXXXXX")
gh run download "$run_id" --repo "$repo" --name parallax-distortion-debug-apk --dir "$artifact_dir"
test -s "$artifact_dir/app-debug.apk"
sha256sum "$artifact_dir/app-debug.apk"
printf 'APK: %s\n' "$artifact_dir/app-debug.apk"
SH
chmod +x "$HOME/get-parallax-v2.sh"
"$HOME/get-parallax-v2.sh"
```

## v2.1 sonar-style spectral overlay

Version 2.1 installs separately as `com.parallax.entrainment.v21`. Enable **Acoustic Sonar Overlay**, select the ring intensity, then complete a successful **Calibrate Room & Speakers** run. The screen overlay visualizes seven calibrated frequency-band energy levels as concentric rings. The bands are normalized relative to the strongest measured band; the summary survives app restarts but no PCM recordings are retained. Repeat calibration to refresh it.

This is a **sonar-inspired frequency-response visualizer**. It does not transmit ultrasonic chirps, estimate echo time-of-flight, localize reflections, measure distance, or form a spatial map. The microphone is never activated by the visualization toggle alone. Check the rings on the physical device after a calibration, then disable the toggle and verify they disappear. Device measurements remain required before any acoustic accuracy claim.


## v2.2 — Binaural bowl upgrade and single-phone acoustic probe

Draft PR #101 builds on the v2.1 branch with a separately installable Android package:
`com.parallax.entrainment.v22`.

Home-screen controls now include bell and ringing bowl toggles, binaural-carrier mode,
16 fundamental frequencies, an optional within-session hourly chime, and a direct
Auto EQ calibration control. The advanced acoustic screen provides ringing sustain
and repeat interval controls. Bells use independent stereo synthesis voices so the
selected binaural target is preserved when bell carriers are enabled. **Use headphones**
for binaural perception.

Calibration preserves prior EQ on weak-band failures and reports valid band counts.
A user-triggered 48 kHz single-phone near-ultrasound diagnostic captures a short
microphone burst, estimates candidate echo delay relative to direct speaker leakage,
and discards the PCM. IMU input reports orientation change and motion flags.
This is an experiment, **not** a verified room scanner, human detector, acoustic
positioning system, EKF or medical treatment. It does not require another device.

See [v2.2 single-device research and validation gates](docs/v2.2-single-device-acoustic-research.md).

For the gated integration and AI-agent handoff see [v2.2 engineering directive](docs/V22_ENGINEERING_EXECUTION_DIRECTIVE.md).

## v2.2.1 development correction — continuous mic feedback and themed audio visuals

**Overrides the older “10-minute auto-polling correction” description for these two new controls.** The earlier 40-second room probe remains available as a separate, explicitly triggered calibration test; it does not run repeatedly while continuous monitoring is enabled.

### Continuous microphone comparison (explicit opt-in)

- Start **an audible Parallax session using the phone's built-in speaker**, then enable **Compare speaker audio to microphone continuously** on the home screen or under Advanced Acoustics.
- With the microphone permission granted, a **user-started microphone foreground service** continuously captures 4096-sample windows at 44.1 kHz. It evaluates a new capture approximately every 300 ms.
- The expected signal comes from Parallax's **actual stereo audio PCM written to AudioTrack**, after binaural bell/bowl synthesis, equalizer, current volume, fades and audio ducking; the speaker comparison reference is the channel-downmixed PCM. No unrelated app audio is used as the reference.
- FFT-based energy comparison computes frequency-band similarity on independently captured microphone audio. The result is a **spectral resemblance estimate**, not raw waveform phase cancellation, spatial localization, human hearing verification or calibrated SPL. Stereo headphones, wired headsets, USB or Bluetooth audio **cannot be evaluated** through the phone's internal microphone; the service refuses non-built-in-speaker routes.
- Similarity, confidence, valid spectral bands and an **uncalibrated mic/reference gain ratio** are visible in the home/advanced status. Low input, clipping, absent signal, processing effects, route changes and background noise may make comparisons unreliable. The comparison handles unsynchronized Android playback and capture clocks by comparing spectra rather than claiming exact sample-by-sample alignment.
- Default mode is **monitor-only**. The separate optional **conservative live Auto EQ** toggle permits peak cuts with max **0.2 dB per eligible band per 15 seconds**, only after repeated confident, broadband matches. At least four correction bands must be supported. No boosts, no modification of manual-locked EQ, and no change to weak/noisy measurements.
- Microphone capture never starts from boot, background scheduling, audio visualization, the sonar-ring switch, or the separate one-shot FMCW room test. The ongoing notification provides Stop. Capture stops when the audio session ends/pauses, route changes, a call begins, permission disappears, battery saver starts or battery is low. It does not restart by itself.
- The app does not save PCM recordings, upload microphone data, store acoustic fingerprints or use the internet for this feature. The real-time PCM snapshot exists only transiently in memory while live monitoring is enabled.

### Two independent visual systems

1. **Audio-reactive Parallax Distortion** (new, off by default): reads a smoothed output amplitude level directly from Parallax's post-EQ playback. It moves the **original Parallax radial-gradient entities** farther from the visual origin, increases their radius and brightens their existing glow according to actual audio amplitude. It maintains the original seeded colors, border/full-screen masking, visual theme, overlay touch safety and 30-fps cap; it introduces no rings or flashing. The user can adjust response strength under Advanced Acoustics. It needs **no microphone permission**.
2. **Room-test sonar rings** (existing, separate, off by default): displays measured spectral-band/range-candidate indicators from explicit acoustic room tests. Sonar rings and audio-reactive Parallax shapes have independent toggles and states. Turning on either visual does **not** start a microphone recording or a sensing probe.

### Hardware QA on one Samsung A14 / Android 15

- With bells playing through the **built-in speaker**, start live comparison from the home screen. Ensure the notification/microphone indicator remains visible, score changes repeatedly, and no 10-minute calibration tones interrupt the music.
- Compare the result with matching bell audio, ambient speech/noise, volume changes and silence. A high number is not a controlled calibration claim. Note any invalid statuses, microphone gain processing, loss of speaker route or muted capture.
- Enable conservative Auto EQ separately and verify that only qualified automatic bands change downward slowly, **manual locks remain untouched**, and no change occurs for silence, clipping, headphones or insufficient spectral coverage.
- Pause/stop playback and stop from the notification. Check the mic indicator clears. Try permission denial/revocation, calibration conflict, calls, battery saver, and route to wired/Bluetooth headphones.
- Toggle audio-reactive visual with microphone **denied**. Confirm original Parallax blobs expand outward/brighten only as playback amplitude increases and return to baseline after silence. Check both theme modes, border/full overlay, TalkBack and navigation-bar touch passthrough.
- Toggle sonar rings independently. Do not show sonar rings unless room-test data exists; do not interpret the audio-reactive blobs as actual room geometry.

### DSP/implementation files

- `PlaybackReferenceBus.kt`: transient playback reference snapshots, visual amplitude and monitor status.
- `LiveAudioMatcher.kt`: pure FFT spectral similarity, conservative EQ advice and radial/intensity mapping.
- `LiveAudioMonitorService.kt`: user-started microphone FGS, periodic ~300 ms analysis and conservative optional EQ.
- `LiveMonitorUi.kt`: shared permission/consent controls for home and Advanced Acoustics.
- `LiveAudioMatcherTest.kt`: deterministic phase-shift, unrelated spectrum, clipping/silence and visual mapping tests.

This is a testable **single-device development implementation**. Real-world speaker/microphone transfer characterization, synchronized audio clocks and listener-perceived binaural effects remain outside the claims of this monitoring module.
