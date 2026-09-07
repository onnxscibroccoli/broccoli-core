# Watch Me Do

Record a task once, catalog it, search it, replay it.
Saving with authorize (default) is the prior authorization.
Later `run <id>` does not ask again.

Catalog file: `~/.broccoli/watchme/catalog.jsonl` (not git).

```bash
cd "$HOME/broccoli-core"
python -m runtime.watchme start "toggle flashlight"
python -m runtime.watchme step tap Flashlight --role quick-settings
python -m runtime.watchme stop
python -m runtime.watchme search flashlight
python -m runtime.watchme run watch-........
```

Password / OTP / token fields are stored as `[REDACTED]` and are not replayed as typed secrets.

Live accessibility scrape still needs the OnDevice observer wired into `WatchSession.ingest_accessibility`.
Replay currently drives `MemorySurface` so the library and search work offline; a later adapter can map the same steps onto rish/a11y.
