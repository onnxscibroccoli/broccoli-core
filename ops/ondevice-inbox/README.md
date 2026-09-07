# OnDevice instruction inbox

The sync daemon only applies `*.json` files in this directory after a git fetch.

Allowed `action` values:

- `health` — record HEAD
- `chmod_bins` — `chmod +x bin/*`
- `brocc` — run `bin/brocc` with allowlisted args only: status, ping, probe, smoke, help, user-done, log, report
- `python_module` — `python3 -m <module>` where module matches `[A-Za-z_][A-Za-z0-9_.]*`

Example:

```json
{"action":"health","note":"noop heartbeat"}
```

```json
{"action":"brocc","args":["status"]}
```

Rejected: shell strings, login, ask, harvest send, arbitrary paths, curl.
After attempt, the file is moved to `ops/ondevice-done/`.
