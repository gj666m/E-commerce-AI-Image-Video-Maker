# Gemini Provider — API易中转站 OpenAI 兼容格式，用于创意类 AI 任务
import base64
import json
import logging

import httpx

from app.config import settings
from app.services.http_client import get_http_client

logger = logging.getLogger(__name__)

# === 系统提示词（从 deepseek_provider 迁移，内容不变） ===

PLAN_SHOTS_SYSTEM_PROMPT = """你是一个专业的时尚电商视觉策划师。你需要根据用户上传的服装商品图片、商品信息和博主人设，策划一套种草图拍摄方案。

每张种草图应该像真实博主在日常生活中自然拍摄的照片，不同角度和场景展示商品的卖点。

请严格按照以下 JSON 格式输出策划方案（不要输出 JSON 以外的内容）：

{
  "plans": [
    {
      "title": "方案标题（简短，如：咖啡店休闲）",
      "scene": "场景描述（具体，如：咖啡店窗边，温暖午后阳光透过玻璃）",
      "pose": "人物姿势描述（如：手拿咖啡杯，身体微侧看向窗外）",
      "angle": "拍摄角度（如：侧面半身、正面中景、全身远景、特写近景等）",
      "selling_point": "这张图要突出的卖点（如：面料柔软舒适、版型修身显瘦等）",
      "prompt_hint": "额外的 prompt 提示词，用于引导 AI 生图（中文，简洁）"
    }
  ]
}

策划要求：
- 生成 4-6 张方案，覆盖不同角度（近景/中景/远景）和不同场景
- 场景要生活化、多样化（咖啡店/街头/公园/居家/海边等），避免重复
- 姿势要自然随性，像被朋友抓拍的感觉
- 每张图聚焦一个核心卖点
- prompt_hint 要简洁实用，可以直接用于 AI 生图

人设-商品适配要求（非常重要）：
- 如果提供了博主人设描述，必须根据人设特征调整每个方案的姿势、场景和氛围
- 人设气质和商品风格要协调：甜美风人设+活泼场景，优雅风人设+安静高级场景，街头风人设+城市户外场景
- 配色方案要同时考虑人设色系偏好和商品颜色，避免冲突
- 姿势要符合人设性格：活泼元气的博主适合动感姿势，温柔知性的博主适合安静姿态
- prompt_hint 中要体现人设与商品的协调感
- 只输出 JSON，不要有任何其他文字"""

PLAN_APLUS_SYSTEM_PROMPT = """你是一个专业的亚马逊 A+ 内容策划师。你需要根据用户上传的服装商品图片和商品信息，策划一套 A+ 内容图片方案。

每个方案是一张独立的 A+ 内容图，图片中会包含文字（标题和正文），需要考虑布局和卖点的匹配。

请严格按照以下 JSON 格式输出策划方案（不要输出 JSON 以外的内容）：

{
  "plans": [
    {
      "type": "图片类型（如：卖点突出型、场景氛围型、对比展示型、细节特写型）",
      "selling_point": "这张图要突出的核心卖点（如：面料柔软亲肤、版型修身显瘦、百搭多场景等）",
      "headline": "图片中的标题文字，简短有力（英文，如：Ultra-Soft Fabric / Perfect Fit / Versatile Style）",
      "body_text": "图片中的正文文字，1-2句描述（英文，如：Premium cotton blend that feels incredibly soft against your skin）",
      "layout": "布局类型（left_image_right_text / right_image_left_text / top_image_bottom_text / full_image_with_overlay）",
      "scene": "场景/背景描述（如：浅色木纹桌面、大理石台面、柔和渐变色背景等）",
      "prompt_hint": "额外的 prompt 提示词，用于引导 AI 生图（中文，简洁）"
    }
  ]
}

策划要求：
- 生成 3-5 张方案，覆盖不同卖点和布局类型
- 每个方案聚焦一个核心卖点，卖点之间不重复
- headline 和 body_text 必须是英文（面向海外市场），简短有力
- layout 选择要与卖点和场景匹配
- 场景要简洁专业，适合 A+ 内容图，不要太复杂
- prompt_hint 要包含视觉风格、色彩、氛围等关键词
- 整体风格统一，适合同一款商品的 A+ 内容系列
- 只输出 JSON，不要有任何其他文字"""

RECOMMEND_STYLES_SYSTEM_PROMPT = """你是一个专业的时尚摄影风格顾问。你需要根据服装商品信息和拍摄策划方案，推荐 3-4 种适合的视觉风格方向。

每种风格方向要有明确的视觉特征描述，可以直接用于 AI 生图的 prompt。

请严格按照以下 JSON 格式输出推荐结果（不要输出 JSON 以外的内容）：

{
  "styles": [
    {
      "name": "风格名称（简短，如：暖调随拍）",
      "description": "风格描述（一句话概括，如：温暖午后光线，手机随拍感，生活化氛围）",
      "prompt_modifier": "可以直接拼入生图 prompt 的风格描述（中文，如：温暖午后自然光，暖色调，手机随拍质感，轻微颗粒感，生活化氛围）"
    }
  ]
}

推荐要求：
- 推荐 3-4 种风格，覆盖不同色调和氛围方向
- 风格方向要和商品类型、目标受众匹配
- 如果有博主人设信息，风格要兼顾人设气质
- prompt_modifier 要具体实用，包含色调、光线、质感等关键词
- 不同风格之间要有明显视觉差异
- 只输出 JSON，不要有任何其他文字"""

# === 视频智能扩写系统提示词（新增） ===
ENHANCE_VIDEO_PROMPT_SYSTEM = """You are a professional fashion video director specializing in e-commerce clothing showcase videos for the Seedance AI video model.

Your task: expand the user's brief description into a detailed, professional video prompt.

Rules:
1. Complete action narrative: describe a clear beginning pose → movement process → ending pose
2. Camera work that matches the action (e.g., tracking, panning, dollying, static, push-in)
3. Lighting and atmosphere details (golden hour, soft studio light, natural window light, etc.)
4. Paced for the duration: 5s = one clean action; 10s = 2 connected actions; 15s = 3 actions with transitions
5. Write in English — Seedance performs significantly better with English prompts
6. 2-4 sentences, concise but cinematic and specific
7. Focus on garment movement (fabric flow, drape, texture) as the hero element
8. Do NOT include camera technical specs like resolution or fps — only creative direction
9. Output ONLY the prompt text, no explanations, no preamble, no quotation marks

Example input: "优雅转身, 5s, red dress"
Example output: A model in a flowing red dress starts with her back to camera, medium full shot, slowly rotates 180 degrees over 3 seconds with the dress naturally swaying, soft golden backlight catching the fabric, camera tracks the rotation then settles on a three-quarter frontal close-up as she completes the turn with a subtle confident smile."""


class GeminiProvider:
    """Gemini 创意类 AI Provider（API易中转，OpenAI 兼容格式）

    用于：AI 策划 / AI 优化 / 风格推荐 / 视频智能扩写。
    商品分析、人设分析等"信息提取"类任务继续走豆包（deepseek_provider）。
    """

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def is_available(self) -> bool:
        return settings.has_gemini

    async def _chat(
        self,
        system_prompt: str,
        user_content: list[dict],
        max_tokens: int = 2048,
        model: str | None = None,
    ) -> str:
        """通用 OpenAI 兼容 chat/completions 调用

        Args:
            system_prompt: 系统提示词
            user_content: user 消息 content 数组（text / image_url 类型，OpenAI 兼容格式）
            max_tokens: 最大输出 token
            model: 指定模型，None 则用默认 gemini_apiyi_model
        Returns:
            模型回复文本
        """
        payload = {
            "model": model or settings.gemini_apiyi_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "max_tokens": max_tokens,
        }

        headers = {
            "Authorization": f"Bearer {settings.gemini_apiyi_api_key}",
            "Content-Type": "application/json",
            "Accept-Encoding": "identity",  # API易已知坑：避免 gzip 解码错误
        }

        url = f"{settings.gemini_apiyi_base_url}/chat/completions"

        try:
            client = get_http_client()
            resp = await client.post(url, headers=headers, json=payload, timeout=180)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text[:500]
            logger.error(f"Gemini API 错误: {e.response.status_code} - {error_detail}")
            raise RuntimeError(f"Gemini API 错误: {e.response.status_code} - {error_detail}")
        except (KeyError, IndexError) as e:
            logger.error(f"Gemini 响应格式异常: {e}")
            raise RuntimeError(f"Gemini 响应格式异常: {str(e)}")
        except Exception as e:
            logger.error(f"Gemini 调用失败: {type(e).__name__}: {e}")
            raise RuntimeError(f"Gemini 调用失败: {type(e).__name__}: {str(e)}")

    @staticmethod
    def _make_image_content(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
        """构造 OpenAI 兼容的 image_url content part"""
        b64 = base64.b64encode(image_bytes).decode()
        return {
            "type": "image_url",
            "image_url": {"url": f"data:{mime_type};base64,{b64}"},
        }

    @staticmethod
    def _make_text_content(text: str) -> dict:
        return {"type": "text", "text": text}

    async def free_text_query(
        self,
        image: bytes,
        prompt: str,
        mime_type: str = "image/jpeg",
    ) -> str:
        """自由文本查询：图片 + 提示词 → 纯文本回复

        用于 AI 优化描述（视频描述优化 / 场景描述优化 / 模特描述优化）。
        """
        user_content = [
            self._make_image_content(image, mime_type),
            self._make_text_content(prompt),
        ]
        return await self._chat(
            "你是一个专业的 AI 视觉助手，请根据用户的请求和图片内容，直接输出文本回复。",
            user_content,
            max_tokens=2048,
        )

    async def plan_shots(
        self,
        images: list[tuple[bytes, str]],
        product_info: str = "",
        persona: str = "",
    ) -> dict:
        """AI 策划种草图方案"""
        user_content = []
        for img_bytes, mime_type in images:
            user_content.append(self._make_image_content(img_bytes, mime_type))

        text_parts = ["请根据这些服装商品图片，策划一套种草图拍摄方案。"]
        if product_info:
            text_parts.append(f"\n商品信息：{product_info}")
        if persona:
            text_parts.append(f"\n博主人设：{persona}")
        text_parts.append("\n请输出 4-6 张种草图的拍摄方案。")
        user_content.append(self._make_text_content("\n".join(text_parts)))

        raw = await self._chat(PLAN_SHOTS_SYSTEM_PROMPT, user_content, max_tokens=4096)
        result = self._parse_json(raw)
        result["_meta"] = {"model": settings.gemini_apiyi_model}
        return result

    async def plan_aplus(
        self,
        images: list[tuple[bytes, str]],
        product_info: str = "",
    ) -> dict:
        """AI 策划 A+ 内容图片方案"""
        user_content = []
        for img_bytes, mime_type in images:
            user_content.append(self._make_image_content(img_bytes, mime_type))

        text_parts = ["请根据这些服装商品图片，策划一套亚马逊 A+ 内容图片方案。"]
        if product_info:
            text_parts.append(f"\n商品信息：{product_info}")
        text_parts.append("\n请输出 3-5 张 A+ 内容图的策划方案。")
        user_content.append(self._make_text_content("\n".join(text_parts)))

        raw = await self._chat(PLAN_APLUS_SYSTEM_PROMPT, user_content, max_tokens=4096)
        result = self._parse_json(raw)
        result["_meta"] = {"model": settings.gemini_apiyi_model}
        return result

    async def recommend_styles(
        self,
        plans: list[dict],
        product_info: str = "",
        persona: str = "",
    ) -> dict:
        """AI 推荐视觉风格方向"""
        plans_summary = []
        for i, plan in enumerate(plans[:3]):
            plans_summary.append(
                f"方案{i+1}：{plan.get('title', '')} - {plan.get('scene', '')}"
            )

        text_parts = [
            "请根据以下服装商品拍摄策划，推荐适合的视觉风格方向。",
            f"\n策划方案：\n" + "\n".join(plans_summary),
        ]
        if product_info:
            text_parts.append(f"\n商品信息：{product_info}")
        if persona:
            text_parts.append(f"\n博主人设：{persona}")

        user_content = [self._make_text_content("\n".join(text_parts))]
        raw = await self._chat(RECOMMEND_STYLES_SYSTEM_PROMPT, user_content, max_tokens=4096)
        result = self._parse_json(raw)
        result["_meta"] = {"model": settings.gemini_apiyi_model}
        return result

    async def enhance_video_prompt(
        self,
        description: str,
        duration: int = 5,
        style: str | None = None,
        image: bytes | None = None,
        mime_type: str = "image/jpeg",
    ) -> str:
        """视频 Prompt 智能扩写：简短动作描述 → 专业视频叙事 prompt

        Args:
            description: 用户的简短描述（如"优雅转身"）
            duration: 视频时长（秒）
            style: 风格偏好（可选）
            image: 参考图（可选，帮助 AI 理解服装）
            mime_type: 图片 MIME 类型
        Returns:
            扩写后的专业视频 prompt（英文）
        """
        parts = [f"Action description: {description}", f"Duration: {duration}s"]
        if style:
            parts.append(f"Style: {style}")
        parts.append("\nExpand this into a professional video prompt.")

        user_content = []
        if image:
            user_content.append(self._make_image_content(image, mime_type))
        user_content.append(self._make_text_content("\n".join(parts)))

        return await self._chat(ENHANCE_VIDEO_PROMPT_SYSTEM, user_content, max_tokens=4096)

    @staticmethod
    def _parse_json(text: str) -> dict:
        """解析模型输出的 JSON（兼容 markdown 代码块包裹）"""
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        if "```json" in text:
            start = text.index("```json") + 7
            end = text.index("```", start)
            return json.loads(text[start:end].strip())
        if "```" in text:
            start = text.index("```") + 3
            end = text.index("```", start)
            return json.loads(text[start:end].strip())

        raise ValueError(f"无法解析模型输出为 JSON: {text[:200]}")
