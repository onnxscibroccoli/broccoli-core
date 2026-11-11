# Parallax Distortion v2.2 — debug APK integrity and build provenance

**This document describes the existing experimental application on the v2.2 feature branch.** An Android build can pass CI without demonstrating calibrated acoustic sensing, valid spatial mapping, independent therapeutic effect, or physical-device acceptance.

## Artifact contents

The root workflow `.github/workflows/parallax-android-build.yml` produces the named Actions artifact `parallax-distortion-debug-apk` containing:

- `app-debug.apk` — Android debug APK, package `com.parallax.entrainment.v22`;
- `SHA256SUMS.txt` — digest of the APK bytes;
- `DEBUG_BUILD_MANIFEST.json` — digest, bytes, package, version, source checkout SHA, exact Actions run URL, and known unverified claims.

The workflow runs `testDebugUnitTest`, `lintDebug`, `assembleDebug`, `apksigner verify` and independent Python archive/checksum tests. Any failure prevents the artifact-upload step from being treated as successful.

### Reproduce just the verifier tests (no Android SDK)

From the repository root:

```sh
python3 -m unittest discover -s parallax-android/scripts/tests \
  -p 'test_verify_debug_artifact.py' -v
```

The verifier checks Android APK ZIP CRC, DEX and manifest presence, the separately generated `sha256sum` entry, Gradle package/version, a full Git source SHA and the exact first-party workflow URL. The APK signature is checked by a separate `apksigner` step in CI.

### Download and independently check a test build

After a successful PR or manual build, open its **exact Actions run** and download the `parallax-distortion-debug-apk` artifact. Inspect the workflow head SHA and note that `pull_request` builds may check out GitHub's synthetic merge SHA.

From the extracted directory:

```sh
sha256sum -c SHA256SUMS.txt
```

The checksum file may contain its original relative build path; if so, run the command from the matching working directory or compare the reported digest against `sha256sum app-debug.apk`. Check `DEBUG_BUILD_MANIFEST.json` for expected package ID and source run.

**Do not treat an Actions artifact as a GitHub Release.** Artifacts expire. A durable release asset requires independently checked signing, version tags, verification records, security review, and a publication gate.

## Safety and scientific limitations

- No test here demonstrates clinically beneficial “healing” or medical efficacy.
- Real ultrasonic output is codec/phone-speaker dependent; the existing experimental sonar diagnostic does not establish accurate room mapping or EKF localization.
- Real-time speaker-microphone spectral comparison is an approximation sensitive to room response, clipping, acoustic echo cancellation, volume and route.
- The distinct sonar overlay and Parallax audio visualization are independent UI modes. Neither is evidence of room geometry.
- A user's real Android device must pass permission, microphone indicator, speaker-route, battery, headset, interrupt and app stop tests before the relevant capabilities can be promoted to `DEVICE_TESTED`.
- Never upload recorded PCM or private location/device measurements to CI.

**Review lineage:** [v2.2 implementation PR #101](https://github.com/onnxscibroccoli/broccoli-core/pull/101) → child provenance PR. [Tracking issue #110](https://github.com/onnxscibroccoli/broccoli-core/issues/110).

**Verification status:** Source implementation and CI workflow are proposed on the child PR. Only exact new run results can establish passed build/package verification.
