from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RouteSession:
    """
    璺敱浼氳瘽涓婁笅鏂?

    鍖呰鍗曚釜route鐨勬墽琛屽弬鏁帮紝渚夸簬璋冨害鍣ㄥ拰App涔嬮棿浼犻€?
    """

    index: int
    runtime_context: Any
    trace_id: str

    @property
    def symbol(self) -> str:
        return str(getattr(self.runtime_context, "symbol", "") or "")

    @property
    def exchange(self) -> str:
        return str(getattr(self.runtime_context, "exchange", "") or "")
