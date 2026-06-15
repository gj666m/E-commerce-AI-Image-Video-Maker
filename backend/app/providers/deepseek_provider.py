# 商品视觉分析 Provider — 使用火山引擎豆包视觉模型
import base64
import json
import logging

import httpx

from app.config import settings
from app.services.http_client import get_http_client

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
            client = get_http_client()
            resp = await client.post(url, headers=headers, json=payload, timeout=60)
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
            client = get_http_client()
            resp = await client.post(url, headers=headers, json=payload, timeout=60)
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

    def _extract_text(self, data: dict) -> str:
        """从 Responses API 返回结果中提取输出文本"""
        for item in data.get("output", []):
            if item.get("type") == "message":
                for content in item.get("content", []):
                    if content.get("type") == "output_text":
                        return content["text"]
        raise ValueError(f"无法从 API 响应中提取文本: {json.dumps(data, ensure_ascii=False)[:300]}")

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


# ===== 以下方法已迁移到 GeminiProvider（gemini_provider.py）=====
# plan_shots / plan_aplus / recommend_styles / free_text_query
# 系统提示词常量 PLAN_SHOTS_SYSTEM_PROMPT / PLAN_APLUS_SYSTEM_PROMPT /
# RECOMMEND_STYLES_SYSTEM_PROMPT 也已迁移，此处不再保留。

