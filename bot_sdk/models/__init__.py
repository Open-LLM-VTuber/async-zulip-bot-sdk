"""Model package.

api/ contains Zulip API-facing models.
data/ holds SDK-side generic data models; bot-specific models live in bot dirs.
"""

from .api import *  # noqa: F401,F403
from .data import *  # noqa: F401,F403
from .api import __all__ as _api_all
from .data import __all__ as _data_all

__all__ = list(_api_all) + list(_data_all)
