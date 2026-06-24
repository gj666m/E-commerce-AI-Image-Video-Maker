# 质检状态事件总线 - 模块级注册表，按 run_id 隔离
# 解决 astream_events 下 config 可能不能在节点与 runner 间共享同一可变对象的问题：
# 节点写 _QC_BUS[run_id]，runner 读 _QC_BUS[run_id]，run_id 通过 config 传递
from collections import defaultdict

# run_id → list[dict] 质检状态条目（按时间顺序追加）
_QC_BUS: dict[str, list[dict]] = defaultdict(list)


def get_bus(run_id: str) -> list[dict]:
    """获取某个 run 的质检状态列表（可变引用，直接 append）"""
    return _QC_BUS[run_id]


def reset_bus(run_id: str) -> None:
    """清空某个 run 的状态（runner 开始时调用）"""
    if run_id in _QC_BUS:
        del _QC_BUS[run_id]
