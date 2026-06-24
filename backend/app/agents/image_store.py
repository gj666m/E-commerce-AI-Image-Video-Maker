# 图片暂存 - 内存 dict，按 thread_id 隔离，TTL 过期清理
# 用户上传图 + Agent 生成图都存这里，State 只存 image_id 引用
import asyncio
import logging
import time
import uuid

from app.config import settings

logger = logging.getLogger(__name__)


class ImageStore:
    """线程安全的图片暂存

    结构：{image_id: {"bytes": b..., "mime": str, "filename": str, "thread_id": str, "ts": float}}
    按 thread_id 隔离，TTL 过期自动清理（惰性 + 后台周期扫描双保险）。
    """

    def __init__(self) -> None:
        self._store: dict[str, dict] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: asyncio.Task | None = None

    def start_cleanup_loop(self) -> None:
        """启动后台周期清理（在 app lifespan 调用一次）"""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())

    async def _periodic_cleanup(self) -> None:
        ttl = settings.agent_image_store_ttl
        while True:
            await asyncio.sleep(300)  # 每 5 分钟扫一次
            try:
                await self._evict_expired()
            except Exception as e:
                logger.error(f"ImageStore 清理失败: {e}")

    async def _evict_expired(self) -> int:
        now = time.time()
        ttl = settings.agent_image_store_ttl
        async with self._lock:
            expired = [k for k, v in self._store.items() if now - v["ts"] > ttl]
            for k in expired:
                del self._store[k]
        if expired:
            logger.info(f"ImageStore 清理 {len(expired)} 条过期图片")
        return len(expired)

    async def put(
        self,
        image_bytes: bytes,
        thread_id: str,
        mime: str = "image/jpeg",
        filename: str = "",
        prefix: str = "img",
    ) -> str:
        """存入一张图片，返回 image_id"""
        image_id = f"{prefix}_{uuid.uuid4().hex[:12]}"
        async with self._lock:
            # 惰性清理同 thread 的过期条目（防止个别条目未被后台扫到）
            now = time.time()
            ttl = settings.agent_image_store_ttl
            for k in [
                k for k, v in self._store.items()
                if v["thread_id"] == thread_id and now - v["ts"] > ttl
            ]:
                del self._store[k]
            self._store[image_id] = {
                "bytes": image_bytes,
                "mime": mime,
                "filename": filename,
                "thread_id": thread_id,
                "ts": now,
            }
        return image_id

    async def get(self, image_id: str) -> bytes | None:
        async with self._lock:
            entry = self._store.get(image_id)
            if entry is None:
                return None
            return entry["bytes"]

    async def get_meta(self, image_id: str) -> dict | None:
        async with self._lock:
            entry = self._store.get(image_id)
            if entry is None:
                return None
            return {"mime": entry["mime"], "filename": entry["filename"], "thread_id": entry["thread_id"]}

    async def get_many(self, image_ids: list[str]) -> list[bytes]:
        """按顺序取多张图片，缺失的跳过"""
        result = []
        for image_id in image_ids:
            b = await self.get(image_id)
            if b is not None:
                result.append(b)
        return result


# 模块级单例
image_store = ImageStore()
