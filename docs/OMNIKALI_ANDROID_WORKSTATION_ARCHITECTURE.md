# OmniKali Android Workstation: Architecture and Delivery Contract

Status: implementation plan and CI bootstrap
Target: Android 15 / API 35; debug APK produced by GitHub Actions
Reference lineage: broccoli-core branch feat/parallax-distortion-apk and Parallax Distortion Android build conventions.

## Product contract

One Android app provides a local control surface for persistent remote workspaces. It is not a container runtime pretending to run Linux locally: Android is the client and orchestration UI, while Linux and Android guests execute on remote infrastructure.

### Main navigation
- Workspaces: persistent Kali/Linux desktop, cloud Android, and any additional authorized remote sessions.
- Terminal: interactive terminal over an authenticated SSH/WebSocket/PTY transport; session state remains server-side.
- Browser: Android WebView for trusted embedded apps, plus a full remote-browser mode (Playwright runs beside the browser in the remote workspace).
- Automation: Playwright jobs, accessibility/UI actions, screenshots, DOM snapshots, logs, and explicit human-intervention gates.
- Containers: list/create/stop/restart remote containers through a narrow control-plane API. Android itself does not promise Docker privileges.
- Connections: Helix/OmniKali endpoints, status, reconnect, session health and audit trail.

## Architecture boundaries

1. Android shell (Kotlin, AndroidX, Material components): navigation, workspace picker, secure credential storage, terminal/browser panes, notifications, download handling and deep links.
2. Session API client: typed DTOs, timeouts, retry/backoff, request IDs, explicit error taxonomy. No cloud credentials baked into APK.
3. Control plane: Helix owns protected desktop lifecycle, authentication, session leases and guest provisioning. Grasshopper defines the cross-project contract and evidence/reconstruction rules. Broccoli Core supplies Android/Termux automation lineage and proven APK CI patterns.
4. Workspace runtime: Linux/Kali and Android guests are persistent remote workloads. Browser automation runs in the same remote environment as the browser when full desktop/browser fidelity is required.
5. Automation broker: Playwright, optional Appium/UIAutomator adapters, bounded job queues, artifacts and human gates. Browser credentials remain in isolated session profiles.
6. Persistence: server-side PostgreSQL for users, workspaces, leases, jobs and audit records; object storage for screenshots and job artifacts. Client caches only non-secret UI state.
7. Transport: HTTPS for control APIs, WSS for terminal/streaming, short-lived scoped tickets, reconnectable sessions. Do not expose raw VNC or container sockets publicly.

## Key user journeys

- Launch app -> authenticate -> select existing Kali workspace -> attach terminal/browser -> disconnect and reconnect without killing the guest.
- Switch to cloud Android -> open remote display/browser -> request automation -> inspect run output and screenshots.
- Open external web application: use embedded WebView only when its login, cookies, OAuth redirects, downloads, file upload and payment/security policies work correctly; otherwise open a dedicated remote-browser tab. Never frame-proxy arbitrary third-party sites or bypass their security controls.
- Start automation -> show scope and target -> run in isolated remote profile -> pause on CAPTCHA/OAuth/consent -> notify user for manual action -> resume after confirmation.
- Recover from network or app process death -> reattach to server-side session by workspace/session ID; no reliance on a live Android activity for job lifetime.

## Android implementation requirements

- Minimum supported API to be selected after inspecting existing app module; target/compile SDK 35 initially, consistent with Android 15 reference.
- Foreground service only for user-visible ongoing sessions; WorkManager for deferrable sync/recovery, not interactive PTY ownership.
- WebView JavaScript bridge disabled by default; allowlist origins and expose only narrow typed methods. External intents and OAuth callbacks must be validated.
- Store refresh tokens in Android Keystore-backed storage; never commit credentials or emit them to logs.
- Terminal input/output uses a streaming protocol and bounded buffers. Do not run arbitrary shell commands on the Android host without explicit local capability and user consent.
- Accessibility/Shizuku/Rish adapters are optional, separately permissioned capabilities. Cloud terminal does not require Shizuku.
- WebView and remote desktop must coexist without keeping a fragile Activity alive as the source of truth.
- Accessibility labels, keyboard/IME handling, landscape/resizing, screen-reader navigation and reconnect states are first-class.

## API contracts (v1 proposal)

- GET /api/v1/workspaces
- POST /api/v1/workspaces (kind: linux | android; validated template ID)
- POST /api/v1/workspaces/{id}/start | stop | restart
- POST /api/v1/workspaces/{id}/sessions (kind: terminal | browser | desktop)
- POST /api/v1/automation/jobs (workspaceId, browserSessionId, approvedTask, policy)
- GET /api/v1/automation/jobs/{id}; GET .../{id}/events; GET .../{id}/artifacts
- POST /api/v1/automation/jobs/{id}/resume (human gate confirmation)
- POST /api/v1/sessions/{id}/ticket (short-lived scoped WSS ticket)

All mutations require authenticated authorization, idempotency key, server-side validation, audit events and rate limits. Exact paths are proposals until reconciled with Helix's live API.

## Delivery sequence

P0: establish Android project/build artifact, workspace shell, API contract, CI and security baseline.
P1: authentication + workspace listing + reconnectable terminal transport.
P2: remote desktop and browser sessions, preserving server-side session lifecycle.
P3: Playwright job runner, screenshots/DOM results, cancellation, human gates.
P4: container controls, optional local Termux/Rish integration, telemetry and fault recovery.
P5: physical-device validation on Android 15; report PASS/FAIL/NOT_PROVEN separately.

## Acceptance gates

- GitHub Actions produces an installable debug APK and uploads it as an artifact.
- Unit tests and lint run when available; build errors are surfaced, not hidden.
- API endpoint behavior is verified against Helix before claiming live integration.
- Reconnect works after Activity recreation and Android process death.
- No secrets in APK, repository, logs or CI artifacts.
- Third-party app support is tested per origin; WebView is not claimed to be universally equivalent to a full browser.
- Cloud Android/Linux lifecycle survives client disconnects.
- Physical-device behavior remains NOT_PROVEN until tested on device.

## Repository roles

Use broccoli-core as the Android/Termux and generic APK build reference, not as the canonical production control plane. Before production integration, verify the current contracts and evidence in Helix, Grasshopper, and grasshopper-kubernetes. Preserve historical evidence; do not mass-clean or overwrite unrelated runtime state.
