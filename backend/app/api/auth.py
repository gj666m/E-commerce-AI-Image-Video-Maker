# 用户认证 API - 登录 + 管理员用户管理
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.auth import verify_password, hash_password, create_access_token, decode_token
from app.database import get_db
from app.deps import get_current_user, require_admin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])


# ====== 请求模型 ======

class LoginRequest(BaseModel):
    username: str
    password: str

class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str = "user"
    display_name: Optional[str] = None

class UpdateUserRequest(BaseModel):
    password: Optional[str] = None
    role: Optional[str] = None
    display_name: Optional[str] = None


# ====== 登录 ======

@router.post("/login")
async def login(req: LoginRequest):
    """用户登录，返回 JWT token"""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT id, username, password_hash, role, display_name FROM users WHERE username = ?",
            (req.username,),
        )
        user = await cursor.fetchone()
        if not user or not verify_password(req.password, user["password_hash"]):
            raise HTTPException(401, "用户名或密码错误")

        token = create_access_token(user["id"], user["username"], user["role"])
        return {
            "success": True,
            "token": token,
            "user": {
                "id": user["id"],
                "username": user["username"],
                "role": user["role"],
                "display_name": user["display_name"],
            },
        }
    finally:
        await db.close()


@router.get("/me")
async def get_me(current_user=Depends(get_current_user)):
    """获取当前用户信息（查 DB 拿最新 display_name）"""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT display_name FROM users WHERE id = ?",
            (current_user["id"],),
        )
        row = await cursor.fetchone()
        display_name = row["display_name"] if row else None
        return {
            "success": True,
            "user": {
                "id": current_user["id"],
                "username": current_user["username"],
                "role": current_user["role"],
                "display_name": display_name,
            },
        }
    finally:
        await db.close()


# ====== 管理员：用户管理 ======

@router.get("/users")
async def list_users(_admin=Depends(require_admin)):
    """管理员获取所有用户列表"""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT id, username, role, display_name, created_at FROM users ORDER BY id"
        )
        rows = await cursor.fetchall()
        return {
            "success": True,
            "users": [dict(r) for r in rows],
        }
    finally:
        await db.close()


@router.post("/users")
async def create_user(req: CreateUserRequest, _admin=Depends(require_admin)):
    """管理员创建用户"""
    if req.role not in ("admin", "user"):
        raise HTTPException(400, "角色只能是 admin 或 user")
    if len(req.username) < 2 or len(req.username) > 20:
        raise HTTPException(400, "用户名长度 2-20 字符")
    if len(req.password) < 4:
        raise HTTPException(400, "密码长度至少 4 位")

    db = await get_db()
    try:
        # 检查用户名是否已存在
        cursor = await db.execute("SELECT id FROM users WHERE username = ?", (req.username,))
        if await cursor.fetchone():
            raise HTTPException(400, "用户名已存在")

        await db.execute(
            "INSERT INTO users (username, password_hash, role, display_name) VALUES (?, ?, ?, ?)",
            (req.username, hash_password(req.password), req.role, req.display_name or None),
        )
        await db.commit()
        logger.info(f"管理员创建用户: {req.username} ({req.role})")
        return {"success": True, "message": f"用户 {req.username} 创建成功"}
    finally:
        await db.close()


@router.delete("/users/{user_id}")
async def delete_user(user_id: int, _admin=Depends(require_admin)):
    """管理员删除用户（不能删自己）"""
    if user_id == _admin["id"]:
        raise HTTPException(400, "不能删除自己的账号")

    db = await get_db()
    try:
        # 删除用户的模特库文件
        from app.services.model_store import delete_user_models
        delete_user_models(user_id)
        # 删除用户的历史文件
        from app.services.history_store import delete_user_history_files
        delete_user_history_files(user_id)

        # 删除用户数据
        await db.execute("DELETE FROM model_library WHERE user_id = ?", (user_id,))
        await db.execute("DELETE FROM video_tasks WHERE user_id = ?", (user_id,))
        await db.execute("DELETE FROM generation_history WHERE user_id = ?", (user_id,))
        cursor = await db.execute("DELETE FROM users WHERE id = ?", (user_id,))
        await db.commit()

        if cursor.rowcount == 0:
            raise HTTPException(404, "用户不存在")

        logger.info(f"管理员删除用户: user_id={user_id}")
        return {"success": True, "message": "用户已删除"}
    finally:
        await db.close()


@router.put("/users/{user_id}")
async def update_user(user_id: int, req: UpdateUserRequest, _admin=Depends(require_admin)):
    """管理员更新用户（重置密码/改角色）"""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT id FROM users WHERE id = ?", (user_id,))
        if not await cursor.fetchone():
            raise HTTPException(404, "用户不存在")

        updates = []
        params = []
        if req.password:
            if len(req.password) < 4:
                raise HTTPException(400, "密码长度至少 4 位")
            updates.append("password_hash = ?")
            params.append(hash_password(req.password))
        if req.role:
            if req.role not in ("admin", "user"):
                raise HTTPException(400, "角色只能是 admin 或 user")
            updates.append("role = ?")
            params.append(req.role)
        if req.display_name is not None:
            # 真实姓名：允许清空（空字符串转 None），上限 50 字符
            name = req.display_name.strip()[:50] if req.display_name else None
            updates.append("display_name = ?")
            params.append(name)

        if not updates:
            raise HTTPException(400, "没有需要更新的字段")

        params.append(user_id)
        # 字段名为代码内白名单追加（非用户输入），SQL 注入风险已防
        await db.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", params)
        await db.commit()
        logger.info(f"管理员更新用户: user_id={user_id}")
        return {"success": True, "message": "用户信息已更新"}
    finally:
        await db.close()
