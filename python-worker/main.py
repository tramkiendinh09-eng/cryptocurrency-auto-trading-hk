#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目主入口文件

负责解析工作配置并启动相应的运行时环境。

启动流程:
```
main()
    │
    ▼
resolve_worker_profile() ──► 解析WORKER_PROFILE环境变量
    │
    ├─► "legacy"系列 ──► 已废弃，回退到trade_runtime
    │
    └─► "trade_runtime" ──► run_trade_runtime()
                                    │
                                    ▼
                            trade_runtime.app.main()
                                    │
                                    ▼
                            TradeRuntimeApp.run_once()
```

环境变量:
- WORKER_PROFILE: 工作配置类型(默认为trade_runtime)
- TRADE_RUNTIME_LOG_LEVEL: 日志级别(默认INFO)

使用方式:
    # 直接运行
    python -m python-worker.main

    # 或通过环境变量配置
    WORKER_PROFILE=trade_runtime python -m python-worker.main
"""

import logging
import os


# 日志配置
logging.basicConfig(
    level=os.getenv("TRADE_RUNTIME_LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)


# 遗留的工作配置文件集合(已废弃)
LEGACY_WORKER_PROFILES = {"legacy", "legacy_dca", "dca", "classic"}

# 遗留工作配置已停用的提示信息
LEGACY_WORKER_RETIRED_MESSAGE = (
    "Legacy worker profiles are retired after the runtime cutover. Falling back to trade_runtime."
)


def resolve_worker_profile() -> str:
    """解析工作配置文件类型

    从环境变量WORKER_PROFILE中读取工作配置类型。

    Returns:
        str: 工作配置文件类型，"legacy_retired" 或 "trade_runtime"
    """
    profile = os.getenv("WORKER_PROFILE", "").strip().lower()
    if profile in LEGACY_WORKER_PROFILES:
        return "legacy_retired"
    return "trade_runtime"


def run_trade_runtime():
    """运行交易运行时

    导入并运行trade_runtime模块的主函数。

    Returns:
        Any: 运行时主函数的返回值
    """
    from trade_runtime.app import main as runtime_main

    return runtime_main()


def run_legacy_worker():
    """运行遗留工作器（已停用）

    Raises:
        RuntimeError: 遗留工作配置已停用
    """
    raise RuntimeError("Legacy worker profile is retired. Use trade_runtime.")


def main():
    """主函数

    解析工作配置并启动相应的运行时。

    Returns:
        Any: 运行时主函数的返回值
    """
    if resolve_worker_profile() == "legacy_retired":
        print(LEGACY_WORKER_RETIRED_MESSAGE)
    return run_trade_runtime()


if __name__ == "__main__":
    """程序入口点"""
    main()
