"""Back-compat CLI shim.

Prefer:
    python -m runtime.providers.xai_oauth login
    python runtime/providers/xai_oauth.py login
    bin/xai-oauth login
"""
from runtime.providers.xai_oauth import main

if __name__ == "__main__":
    raise SystemExit(main())
