"""xAI OAuth device-code login package.

`python -m runtime.providers.xai_oauth login` resolves here via __main__.py.
"""

from . import xai_oauth as _xo

DEFAULT_TOKEN_PATH = _xo.DEFAULT_TOKEN_PATH
device_login = _xo.device_login
load_tokens = _xo.load_tokens
save_tokens = _xo.save_tokens
clear_tokens = _xo.clear_tokens
get_access_token = _xo.get_access_token
TokenSet = _xo.TokenSet

__all__ = [
    "DEFAULT_TOKEN_PATH",
    "TokenSet",
    "clear_tokens",
    "device_login",
    "get_access_token",
    "load_tokens",
    "save_tokens",
]
