from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class RouteSchedulerConfig:
    """
    璺敱璋冨害閰嶇疆
    """

    mode: str = "SERIAL"
    max_concurrency: int = 1


@dataclass(frozen=True)
class RouteTask:
    """
    璺敱鎵ц浠诲姟
    """

    index: int
    symbol: str
    exchange: str
    trace_id: str
    execute: Callable[[], Any]


class RouteScheduler:
    """
    route璋冨害鍣?
    """

    def __init__(self, config: RouteSchedulerConfig | None = None):
        self.config = config or RouteSchedulerConfig()

    def run(self, tasks: list[RouteTask]) -> list[Any]:
        if not tasks:
            return []
        ordered_results: list[Any] = [None] * len(tasks)
        if self._is_serial():
            for task in tasks:
                ordered_results[task.index] = self._run_task(task)
            return ordered_results
        with ThreadPoolExecutor(max_workers=self.config.max_concurrency) as executor:
            future_to_task = {executor.submit(self._run_task, task): task for task in tasks}
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                ordered_results[task.index] = future.result()
        return ordered_results

    def _is_serial(self) -> bool:
        return str(self.config.mode or "SERIAL").strip().upper() != "THREAD_POOL" or self.config.max_concurrency <= 1

    def _run_task(self, task: RouteTask) -> Any:
        try:
            return task.execute()
        except Exception as exc:
            return {
                "status": "error",
                "symbol": task.symbol,
                "exchange": task.exchange,
                "trace_id": task.trace_id,
                "error": str(exc),
            }
