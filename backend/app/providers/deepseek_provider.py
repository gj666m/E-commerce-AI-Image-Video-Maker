# 商品视觉分析 Provider — 使用火山引擎豆包视觉模型
import base64
import json
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# 系统提示词：引导模型输出结构化商品分析
SYSTEM_PROMPT = """你是一个专业的服装商品分析助手。你需要根据用户上传的服装商品图片，进行详细的结构化分析。

请严格按照以下 JSON 格式输出分析结果（不要输出 JSON 以外的内容）：

{
  "category": "服装类型（如：连衣裙、T恤、衬衫、外套、半裙、裤装等）",
  "style": "款式描述（如：修身、宽松、A字、直筒、oversized等）",
  "fabric": "面料判断（如：棉质、丝绸、雪纺、针织、牛仔、蕾丝等）",
  "color": "主要颜色和配色描述",
  "pattern": "图案/纹理（如：纯色、碎花、条纹、格纹、波点等）",
  "details": "工艺细节（如：纽扣、拉链、褶皱、刺绣、镂空等）",
  "selling_points": ["卖点1", "卖点2", "卖点3"],
  "suitable_scenes": ["适用场景1", "适用场景2", "适用场景3"],
  "target_audience": "目标受众描述",
  "season": "适合季节（春/夏/秋/冬/四季）",
  "keywords": ["关键词1", "关键词2", "关键词3", "关键词4", "关键词5"]
}

注意：
- 分析基于图片中的实际内容，不要猜测图片中看不到的信息
- 卖点要突出商品的核心竞争力
- 适用场景要具体（如"周末休闲""办公室通勤""约会""度假"等）
- 关键词用于后续 AI 生图的 prompt 拼装
- 只输出 JSON，不要有任何其他文字"""

# 带已有信息的优化模式系统提示词
SYSTEM_PROMPT_WITH_EXISTING = """你是一个专业的服装商品分析助手。用户已提供了部分商品信息，你需要结合图片分析来优化和补全这些信息。

用户已提供的信息会在提示中标注。请遵循以下原则：
1. 对于用户已填写的字段：结合图片进行优化，保留用户的意图，补充更专业的描述
2. 对于用户未填写的字段：根据图片分析结果填写
3. 所有字段都必须填写完整

请严格按照以下 JSON 格式输出分析结果（不要输出 JSON 以外的内容）：

{
  "category": "服装类型（如：连衣裙、T恤、衬衫、外套、半裙、裤装等）",
  "style": "款式描述（如：修身、宽松、A字、直筒、oversized等）",
  "fabric": "面料判断（如：棉质、丝绸、雪纺、针织、牛仔、蕾丝等）",
  "color": "主要颜色和配色描述",
  "pattern": "图案/纹理（如：纯色、碎花、条纹、格纹、波点等）",
  "details": "工艺细节（如：纽扣、拉链、褶皱、刺绣、镂空等）",
  "selling_points": ["卖点1", "卖点2", "卖点3"],
  "suitable_scenes": ["适用场景1", "适用场景2", "适用场景3"],
  "target_audience": "目标受众描述",
  "season": "适合季节（春/夏/秋/冬/四季）",
  "keywords": ["关键词1", "关键词2", "关键词3", "关键词4", "关键词5"]
}

注意：
- 分析基于图片中的实际内容，不要猜测图片中看不到的信息
- 优化时保持用户原有的表达风格和专业性
- 只输出 JSON，不要有任何其他文字"""


class ProductAnalysisProvider:
    """商品视觉分析 Provider

    使用火山引擎豆包视觉模型（Responses API）进行商品图片分析。
    不继承 BaseProvider（非图片生成模型）。
    """

    @property
    def name(self) -> str:
        return "product_analysis"

    @property
    def is_available(self) -> bool:
        return bool(settings.volcengine_api_key)

    async def analyze(
        self,
        image: bytes,
        mime_type: str = "image/jpeg",
        extra_prompt: str | None = None,
        existing_info: dict | None = None,
    ) -> dict:
        """分析商品图片，返回结构化商品信息

        Args:
            image: 图片二进制数据
            mime_type: 图片 MIME 类型
            extra_prompt: 用户额外提示（可选）
            existing_info: 用户已填写的商品信息（可选），AI 会在此基础上优化补全

        Returns:
            结构化商品分析结果 dict
        """
        b64_image = base64.b64encode(image).decode()

        # 构建 input_image 内容
        user_content = [
            {
                "type": "input_image",
                "image_url": f"data:{mime_type};base64,{b64_image}",
            },
        ]

        # 根据是否有已有信息选择系统提示词
        has_existing = existing_info and any(existing_info.values())
        system_prompt = SYSTEM_PROMPT_WITH_EXISTING if has_existing else SYSTEM_PROMPT

        text_prompt = "请分析这张服装商品图片，输出结构化的 JSON 分析结果。"
        if extra_prompt:
            text_prompt += f"\n\n用户额外提示：{extra_prompt}"
        if has_existing:
            text_prompt += f"\n\n用户已提供的商品信息（请在此基础上优化补全）：\n{json.dumps(existing_info, ensure_ascii=False)}"

        user_content.append({
            "type": "input_text",
            "text": text_prompt,
        })

        # 火山引擎 Responses API 格式
        payload = {
            "model": settings.volcengine_vision_model,
            "instructions": system_prompt,
            "input": [
                {"role": "user", "content": user_content},
            ],
            "max_output_tokens": 2048,
        }

        headers = {
            "Authorization": f"Bearer {settings.volcengine_api_key}",
            "Content-Type": "application/json",
        }

        url = f"https://ark.cn-beijing.volces.com/api/v3/responses"

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()

            # 从 Responses API 输出中提取文本
            content = self._extract_text(data)

            # 解析 JSON（兼容 markdown 代码块包裹）
            result = self._parse_json(content)

            # 附加元信息
            result["_meta"] = {
                "model": settings.volcengine_vision_model,
                "usage": data.get("usage", {}),
            }

            return result

        except httpx.HTTPStatusError as e:
            error_detail = e.response.text[:500]
            logger.error(f"视觉分析 API 错误: {e.response.status_code} - {error_detail}")
            raise RuntimeError(f"视觉分析 API 错误: {e.response.status_code} - {error_detail}")
        except Exception as e:
            logger.error(f"商品分析失败: {e}")
            raise RuntimeError(f"商品分析失败: {str(e)}")

    # 博主人设分析系统提示词
    PERSONA_SYSTEM_PROMPT = """你是一个专业的时尚博主人设分析助手。你需要根据用户上传的人物照片，分析该人物的形象特征和适合的博主人设风格。

请严格按照以下 JSON 格式输出分析结果（不要输出 JSON 以外的内容）：

{
  "style": "穿搭风格（如：极简风、甜美风、街头风、优雅风、休闲风、韩系、法式等）",
  "age_range": "年龄段判断（如：20-25岁、25-30岁、30-35岁等）",
  "vibe": "气质特征（如：清新自然、温柔知性、活泼元气、高冷文艺、阳光亲和等）",
  "suitable_scenes": ["适合的拍摄场景1", "适合的拍摄场景2", "适合的拍摄场景3"],
  "color_preference": "适合的服装色系（如：莫兰迪色系、大地色系、黑白灰、马卡龙色系等）",
  "description": "一段完整的人设描述文本，100字以内，用于 AI 生图 prompt，描述这个博主的形象特征和穿搭风格"
}

注意：
- 分析基于照片中人物的视觉特征（面部、发型、体型、穿着等）
- suitable_scenes 要具体（如"咖啡店""海边""城市街拍""公园"等）
- description 要像真人博主介绍，自然流畅，包含年龄、风格、气质
- 只输出 JSON，不要有任何其他文字"""

    async def analyze_persona(
        self,
        image: bytes,
        mime_type: str = "image/jpeg",
    ) -> dict:
        """分析博主照片，提取人设特征

        Args:
            image: 博主照片二进制数据
            mime_type: 图片 MIME 类型

        Returns:
            结构化人设分析结果 dict
        """
        b64_image = base64.b64encode(image).decode()

        user_content = [
            {
                "type": "input_image",
                "image_url": f"data:{mime_type};base64,{b64_image}",
            },
            {
                "type": "input_text",
                "text": "请分析这张人物照片，提取博主人设特征，输出结构化 JSON。",
            },
        ]

        payload = {
            "model": settings.volcengine_vision_model,
            "instructions": self.PERSONA_SYSTEM_PROMPT,
            "input": [
                {"role": "user", "content": user_content},
            ],
            "max_output_tokens": 2048,
        }

        headers = {
            "Authorization": f"Bearer {settings.volcengine_api_key}",
            "Content-Type": "application/json",
        }

        url = "https://ark.cn-beijing.volces.com/api/v3/responses"

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()

            # 检查输出是否被截断
            if data.get("incomplete_details", {}).get("reason") == "length":
                logger.warning("人设分析输出被截断，尝试解析已有内容")

            content = self._extract_text(data)
            result = self._parse_json(content)
            result["_meta"] = {
                "model": settings.volcengine_vision_model,
                "usage": data.get("usage", {}),
            }
            return result

        except httpx.HTTPStatusError as e:
            error_detail = e.response.text[:500]
            logger.error(f"人设分析 API 错误: {e.response.status_code} - {error_detail}")
            raise RuntimeError(f"人设分析 API 错误: {e.response.status_code} - {error_detail}")
        except Exception as e:
            logger.error(f"人设分析失败: {e}")
            raise RuntimeError(f"人设分析失败: {str(e)}")

    # 种草图策划系统提示词
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

    async def plan_shots(
        self,
        images: list[tuple[bytes, str]],
        product_info: str = "",
        persona: str = "",
    ) -> dict:
        """AI 策划种草图方案

        Args:
            images: 商品图片列表 [(bytes, mime_type), ...]
            product_info: 商品信息文本
            persona: 博主人设描述

        Returns:
            策划方案 dict，含 plans 数组
        """
        user_content = []

        # 添加所有商品图片
        for img_bytes, mime_type in images:
            b64 = base64.b64encode(img_bytes).decode()
            user_content.append({
                "type": "input_image",
                "image_url": f"data:{mime_type};base64,{b64}",
            })

        # 构建文本提示
        text_parts = ["请根据这些服装商品图片，策划一套种草图拍摄方案。"]
        if product_info:
            text_parts.append(f"\n商品信息：{product_info}")
        if persona:
            text_parts.append(f"\n博主人设：{persona}")
        text_parts.append("\n请输出 4-6 张种草图的拍摄方案。")

        user_content.append({
            "type": "input_text",
            "text": "\n".join(text_parts),
        })

        payload = {
            "model": settings.volcengine_vision_model,
            "instructions": self.PLAN_SHOTS_SYSTEM_PROMPT,
            "input": [
                {"role": "user", "content": user_content},
            ],
            "max_output_tokens": 4096,
        }

        headers = {
            "Authorization": f"Bearer {settings.volcengine_api_key}",
            "Content-Type": "application/json",
        }

        url = "https://ark.cn-beijing.volces.com/api/v3/responses"

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()

            # 检查截断
            if data.get("incomplete_details", {}).get("reason") == "length":
                logger.warning("策划输出被截断，尝试解析已有内容")

            content = self._extract_text(data)
            result = self._parse_json(content)
            result["_meta"] = {
                "model": settings.volcengine_vision_model,
                "usage": data.get("usage", {}),
            }
            return result

        except httpx.HTTPStatusError as e:
            error_detail = e.response.text[:500]
            logger.error(f"策划 API 错误: {e.response.status_code} - {error_detail}")
            raise RuntimeError(f"策划 API 错误: {e.response.status_code} - {error_detail}")
        except Exception as e:
            logger.error(f"AI 策划失败: {e}")
            raise RuntimeError(f"AI 策划失败: {str(e)}")

    # 风格推荐系统提示词
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

    async def recommend_styles(
        self,
        plans: list[dict],
        product_info: str = "",
        persona: str = "",
    ) -> dict:
        """AI 推荐风格方向

        Args:
            plans: 策划方案列表
            product_info: 商品信息文本
            persona: 博主人设描述

        Returns:
            风格推荐 dict，含 styles 数组
        """
        # 构建策划方案摘要
        plans_summary = []
        for i, plan in enumerate(plans[:3]):  # 最多取前3个方案作为参考
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

        user_content = [
            {
                "type": "input_text",
                "text": "\n".join(text_parts),
            },
        ]

        payload = {
            "model": settings.volcengine_vision_model,
            "instructions": self.RECOMMEND_STYLES_SYSTEM_PROMPT,
            "input": [
                {"role": "user", "content": user_content},
            ],
            "max_output_tokens": 4096,
        }

        headers = {
            "Authorization": f"Bearer {settings.volcengine_api_key}",
            "Content-Type": "application/json",
        }

        url = "https://ark.cn-beijing.volces.com/api/v3/responses"

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()

            content = self._extract_text(data)
            result = self._parse_json(content)
            result["_meta"] = {
                "model": settings.volcengine_vision_model,
                "usage": data.get("usage", {}),
            }
            return result

        except httpx.HTTPStatusError as e:
            error_detail = e.response.text[:500]
            logger.error(f"风格推荐 API 错误: {e.response.status_code} - {error_detail}")
            raise RuntimeError(f"风格推荐 API 错误: {e.response.status_code} - {error_detail}")
        except Exception as e:
            logger.error(f"风格推荐失败: {e}")
            raise RuntimeError(f"风格推荐失败: {str(e)}")

    # A+ 内容策划系统提示词
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

    async def plan_aplus(
        self,
        images: list[tuple[bytes, str]],
        product_info: str = "",
    ) -> dict:
        """AI 策划 A+ 内容图片方案

        Args:
            images: 商品图片列表 [(bytes, mime_type), ...]
            product_info: 商品信息文本

        Returns:
            策划方案 dict，含 plans 数组
        """
        user_content = []

        for img_bytes, mime_type in images:
            b64 = base64.b64encode(img_bytes).decode()
            user_content.append({
                "type": "input_image",
                "image_url": f"data:{mime_type};base64,{b64}",
            })

        text_parts = ["请根据这些服装商品图片，策划一套亚马逊 A+ 内容图片方案。"]
        if product_info:
            text_parts.append(f"\n商品信息：{product_info}")
        text_parts.append("\n请输出 3-5 张 A+ 内容图的策划方案。")

        user_content.append({
            "type": "input_text",
            "text": "\n".join(text_parts),
        })

        payload = {
            "model": settings.volcengine_vision_model,
            "instructions": self.PLAN_APLUS_SYSTEM_PROMPT,
            "input": [
                {"role": "user", "content": user_content},
            ],
            "max_output_tokens": 4096,
        }

        headers = {
            "Authorization": f"Bearer {settings.volcengine_api_key}",
            "Content-Type": "application/json",
        }

        url = "https://ark.cn-beijing.volces.com/api/v3/responses"

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()

            if data.get("incomplete_details", {}).get("reason") == "length":
                logger.warning("A+ 策划输出被截断，尝试解析已有内容")

            content = self._extract_text(data)
            result = self._parse_json(content)
            result["_meta"] = {
                "model": settings.volcengine_vision_model,
                "usage": data.get("usage", {}),
            }
            return result

        except httpx.HTTPStatusError as e:
            error_detail = e.response.text[:500]
            logger.error(f"A+ 策划 API 错误: {e.response.status_code} - {error_detail}")
            raise RuntimeError(f"A+ 策划 API 错误: {e.response.status_code} - {error_detail}")
        except Exception as e:
            logger.error(f"A+ 策划失败: {e}")
            raise RuntimeError(f"A+ 策划失败: {str(e)}")

    def _extract_text(self, data: dict) -> str:
        """从 Responses API 返回结果中提取输出文本"""
        for item in data.get("output", []):
            if item.get("type") == "message":
                for content in item.get("content", []):
                    if content.get("type") == "output_text":
                        return content["text"]
        raise ValueError(f"无法从 API 响应中提取文本: {json.dumps(data, ensure_ascii=False)[:300]}")

    async def free_text_query(
        self,
        image: bytes,
        prompt: str,
        mime_type: str = "image/jpeg",
    ) -> str:
        """自由文本查询：图片 + 提示词 → 纯文本回复

        用于视频描述优化等不需要结构化 JSON 的场景。
        """
        b64_image = base64.b64encode(image).decode()

        user_content = [
            {"type": "input_image", "image_url": f"data:{mime_type};base64,{b64_image}"},
            {"type": "input_text", "text": prompt},
        ]

        payload = {
            "model": settings.volcengine_vision_model,
            "instructions": "你是一个专业的 AI 视觉助手，请根据用户的请求和图片内容，直接输出文本回复。",
            "input": [{"role": "user", "content": user_content}],
            "max_output_tokens": 1024,
        }

        headers = {
            "Authorization": f"Bearer {settings.volcengine_api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    "https://ark.cn-beijing.volces.com/api/v3/responses",
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
                return self._extract_text(resp.json())
        except Exception as e:
            logger.error(f"自由文本查询失败: {e}")
            raise RuntimeError(f"AI 查询失败: {str(e)}")

    def _parse_json(self, text: str) -> dict:
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
