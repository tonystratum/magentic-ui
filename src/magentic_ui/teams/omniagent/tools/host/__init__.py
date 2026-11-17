"""Host-side tool implementations — orchestration, state, formatting."""

from ._bash import BashOutput
from ._create import CreateOutput
from ._edit import EditOutput
from ._insert import InsertOutput
from ._open import OpenOutput
from ._output import ToolOutput
from ._scroll import ScrollOutput
from ._search import FindFileOutput, SearchDirOutput, SearchFileOutput
from ._state import (
    ViewportState,
    compute_open_line,
    compute_scroll_down,
    compute_scroll_up,
    constrain_line,
    format_viewport,
    increment_scroll,
    reset_scroll,
)

__all__ = [
    "BashOutput",
    "CreateOutput",
    "EditOutput",
    "FindFileOutput",
    "InsertOutput",
    "OpenOutput",
    "ScrollOutput",
    "SearchDirOutput",
    "SearchFileOutput",
    "ToolOutput",
    "ViewportState",
    "compute_open_line",
    "compute_scroll_down",
    "compute_scroll_up",
    "constrain_line",
    "format_viewport",
    "increment_scroll",
    "reset_scroll",
]
