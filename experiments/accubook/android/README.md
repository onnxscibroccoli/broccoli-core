# Accubook: experimental offline Android field-service MVP

**Maturity:** Experimental / not production verified. **Owner:** Broccoli Core development branch.
This is an isolated Android client under `experiments/`; it is not a privileged Broccoli
Core agent, does not use Shizuku/rish, and does not change the governor or event bus.

## Why Android native first?

The immediate acceptance target is an **installable debug APK** on Android 15. A small,
documented-API-only Java app avoids requiring a Tauri/Rust mobile cross-toolchain
before the core file schema is proven. This is a delivery adapter, **not** a claim that
the final desktop/iOS implementation has been completed. Broccoli Core remains
separate from the Accubook customer-data domain.

## Data and security boundary

- Local app-private files in `getFilesDir()/Accubook Workspace/`.
- Portable UTF-8 CSVs and per-client/per-job directories.
- Writes use the Android framework `AtomicFile` API with serialized mutations.
- No INTERNET permission, runtime AI, remote database, broad shared-storage permission,
  privileged shell, background synchronization, or telemetry.
- Android's Storage Access Framework (SAF) is used only when the user explicitly exports
  an HTML invoice or ZIP backup; the export destination is user-selected.
- App-private files are **deleted on uninstall**. Export a ZIP before uninstalling.
- Multi-file writes are **not a transaction**. The job index total is a denormalized
  cache recalculated from canonical item files on reads; future work must implement
  journaled recovery for other dependent fields.

## Build

Use the GitHub Actions **Accubook Android Debug APK** workflow, then download the
`accubook-debug-universal` build artifact. No Play Store signing secrets or WIF needed.
A debug APK is automatically **debug signed**, not production signed.

Local (Android SDK + Gradle 8.11.1 + JDK 17):
```sh
cd experiments/accubook/android
gradle :app:assembleDebug --no-daemon
# app/build/outputs/apk/debug/app-debug.apk
```

Standalone CSV test:
```sh
cd experiments/accubook/android
mkdir -p build/csv-test
javac -d build/csv-test app/src/main/java/com/accubook/crm/CsvCodec.java app/src/test/java/com/accubook/crm/CsvCodecSmoke.java
java -cp build/csv-test com.accubook.crm.CsvCodecSmoke
```

## Release blockers (do not relabel as ready)

1. Verified GitHub Actions APK compilation + SHA-256 and manual Android installation.
2. Device smoke test: create customer, schedule job, add item, export invoice and backup.
3. Crash/power-loss and schema migration/fail-safe restoration tests.
4. Backup **restore**, attachment import/photographic evidence, payment accounting,
   mobile/desktop parity, localization, operational testing, and accessibility audit.
5. Before any Play submission: reproducible release checks, independent review, signing
   key custody, and correct store listing/privacy disclosures.

**Not implemented:** Tauri desktop/iOS renderer, PDF conversion, multi-device sync,
runtime AI, payment processing, durable cross-file transaction journal.

## CI build evidence (2026-11-05, Eastern)

The first successful source build is GitHub Actions
[run 42157304551](https://github.com/onnxscibroccoli/broccoli-core/actions/runs/42157304551),
source commit `e6de86bbf2d1390158590d55e5c16711d75da679`.
The standalone CSV codec test passed and Gradle `:app:assembleDebug` succeeded.
SHA-256 of its debug APK:
`0cf88d42108a4dfc8bb6230e4b4f92044084dbd880f8af067d1a97cbd9b5c451`.
This evidence does **not** establish device installation or production quality.
