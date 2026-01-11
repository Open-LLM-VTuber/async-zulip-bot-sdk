from __future__ import annotations

import json
import inspect
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

from loguru import logger


class I18n:
    """Very small JSON-based i18n helper.

    - Keys are the original English strings used in code.
    - Translations are stored in ``<base_dir>/<lang>.json`` files.
    - Lookups fall back to English, then to the original key.
    - ``str.format(**kwargs)`` is applied if placeholders are present.
    """

    def __init__(
        self,
        language: str,
        search_paths: Sequence[Path],
        default_language: str = "en",
    ) -> None:
        self.language = language or default_language
        self.default_language = default_language
        self._translations: Dict[str, str] = {}
        self._fallback: Dict[str, str] = {}
        self._load_from_paths(search_paths)

    def _load_from_paths(self, paths: Sequence[Path]) -> None:
        primary: Dict[str, str] = {}
        fallback: Dict[str, str] = {}
        for base in paths:
            try:
                base_dir = Path(base)
                if not base_dir.exists():
                    continue
                primary.update(_load_language_file(base_dir, self.language))
                if self.language != self.default_language:
                    fallback.update(_load_language_file(base_dir, self.default_language))
            except Exception as exc:  # pragma: no cover - defensive logging only
                logger.warning(f"Failed to load i18n files from {base}: {exc}")
        self._translations = primary
        self._fallback = fallback

    def translate(self, key: str, **kwargs: Any) -> str:
        """Translate a key and apply optional ``str.format`` placeholders."""

        text = self._translations.get(key) or self._fallback.get(key) or key
        if kwargs:
            try:
                text = text.format(**kwargs)
            except Exception:  # pragma: no cover - formatting should not break bot
                logger.warning("Failed to format i18n string", key=key)
        return text


def _load_language_file(base_dir: Path, language: str) -> Dict[str, str]:
    path = base_dir / f"{language}.json"
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data: Mapping[str, Any] = json.load(f) or {}
        # Only keep string->string mappings; ignore others.
        return {str(k): str(v) for k, v in data.items() if isinstance(v, str)}
    except Exception as exc:  # pragma: no cover - defensive logging only
        logger.warning(f"Failed to load i18n file {path}: {exc}")
        return {}


def build_i18n_for_bot(language: str, bot_module_name: str) -> I18n:
    """Construct an :class:`I18n` instance for a bot.

    Search order for language JSON files:
    1. ``<bot_module_dir>/i18n``
    2. ``bot_sdk/i18n`` (SDK-level defaults)
    """

    search_paths: list[Path] = []

    # Bot-local i18n directory next to the bot module.
    try:
        mod = __import__(bot_module_name, fromlist=["__file__"])
        mod_file = inspect.getfile(mod)
        bot_dir = Path(mod_file).parent
        search_paths.append(bot_dir / "i18n")
    except Exception:  # pragma: no cover - fall back to SDK-only i18n
        logger.debug(f"Could not resolve module path for {bot_module_name}; using SDK i18n only")

    # SDK-level i18n directory.
    sdk_dir = Path(__file__).resolve().parent
    search_paths.append(sdk_dir / "i18n")

    return I18n(language=language, search_paths=search_paths)


__all__ = ["I18n", "build_i18n_for_bot"]
