"""触发阈值的历史校准设施。

这个包解决的是仓库里原本缺失的一环：所有触发阈值都是人工选定的，
没有任何历史检验手段（``replay_runner`` 重放的是单条 trace，不是历史回测）。

设计上只有一条硬性原则——**信号判定必须复用生产代码**。
``replay.py`` 直接调用 ``trigger_policy.evaluate_trigger_policy``，
不复制任何一条阈值比较逻辑；校准结果因此描述的是线上真实行为，
而不是另一套近似实现的行为。

模块分工::

    history.py   拉取并缓存 Binance 历史数据（K线 / 标记价 / 持仓量 / 资金费率）
    replay.py    把历史数据重建成 feature_snapshot 序列，驱动生产触发策略
    sweep.py     阈值网格扫描 + 前瞻收益评估，产出校准报告
"""

from .history import HistoryBundle, load_history
from .replay import (
    ReplayFrames,
    ReplayResult,
    build_frames,
    evaluate_frames,
    replay_thresholds,
    summarize_window,
)
from .sweep import SweepOutcome, evaluate_replay, recommend, sweep_threshold

__all__ = [
    "HistoryBundle",
    "load_history",
    "ReplayFrames",
    "ReplayResult",
    "build_frames",
    "evaluate_frames",
    "replay_thresholds",
    "summarize_window",
    "SweepOutcome",
    "evaluate_replay",
    "recommend",
    "sweep_threshold",
]
