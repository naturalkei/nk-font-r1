"""NK Studio: local web UI for rule-based Hangul tuning (roadmap tool T2).

The Python core builds small preview fonts (only the characters on screen) with the same
`build_master` code path as release builds, so what you see is what `nkfont build` produces.
"""

from .core import Studio, update_hangul_config

__all__ = ["Studio", "update_hangul_config"]
