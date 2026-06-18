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

# === 视频智能扩写系统提示词（中文输出 + 保留补强策略） ===
ENHANCE_VIDEO_PROMPT_SYSTEM = """你是一个专业的时尚视频导演，擅长为 Seedance AI 视频模型编写高质量的视频生成 prompt。

你的任务：在用户简短描述的基础上进行【保留 + 补强】，输出一段专业的中文视频 prompt。

【核心原则 —— 必须严格遵守】
1. 保留用户的原始意图：用户提到的节奏结构（如卡点切镜、分段转场、多场景跳切）、镜头动词（如推近/拉远/跳切/定格/手持晃动/极速）、风格关键词（如鱼眼/街拍/广角/冲击力/电影感）必须原样保留，不得弱化、不得替换、不得删除。
2. 只补强，不重写：你的工作是帮用户把想法写完整，而不是把用户的想法改没。用户没写的你补，用户写了的你不动（除了润色表达）。
3. 补强维度（只补这些，不擅自改变风格）：
   - 画面动态感（最重要！）：每一段切镜都必须有视觉动态，不能是"一张静态照片"。动态来源（至少满足两项）：①镜头运动（推/拉/摇/移/跟/环绕/升降/甩）②人物动作（走动/转身/甩发/推墨镜等）③场景变化（跳切换景）。注意：并非所有视频都需要镜头运动——产品展示、氛围慢视频可以镜头静止，但必须靠人物动作或光影变化让画面"活"起来。唯一禁止：镜头静止+人物静止=死板照片。
   - 服装细节：款式、面料、质感（如用户只写"女生"，可根据参考图或合理推断补"短款皮夹克+阔腿裤"）。注意：不要给服装指定具体文字内容（如印着"LOGO"字样），AI 视频无法准确渲染文字，会产生乱码。
   - 光影氛围：光线方向、色温、硬度（如硬光逆光勾边 / 柔和窗光 / 黄金时刻侧光）
   - 场景细节：把抽象场景具体化（如"十字路口"→"阳光斑驳的十字路口斑马线"）
   - 动作细节：每段必须有人物动态过程，不能只写静态 pose（如"站立"→"身体微转看向镜头"，"定格"→"顺势抬头直视镜头"）
4. 输出中文：运营团队需要能看懂、能判断好坏、能自己微调。
5. 时长节奏按用户描述类型智能判断：
   - 单线叙事型（如"优雅转身"）：5秒=一个完整动作，10秒=两个衔接动作，15秒=三个动作带转场
   - 卡点切镜型（用户写了"卡点/跳切/多段切镜/多次切换"等词）：严格保留用户写的切镜段数，每段合理分配时长（如5秒2-3段切镜）
   关键：用户写了几段就保留几段，不要因为"5秒太短"而砍掉用户的切镜结构。
6. 只输出 prompt 正文，不要解释、不要前言、不要引号、不要分点列表（输出连贯的一段话）。

【常见错误 —— 必须避免】
- 把强节奏的卡点街拍视频改写成柔和的"模特摆 pose 展示服装"
- 把"极速推近/跳切/定格面部"这种强镜头动词替换成"缓慢推进/自然过渡/缓缓展示"
- 丢失用户明确写的视觉风格（鱼眼畸变/广角/手持晃动/快切等）
- 擅自加入用户没要求的风格（把街拍改成电影感、把卡点改成唯美慢动作）
- 把中文改成英文输出
- 画面没有动态感（镜头静止+人物也静止=死板照片）——每段至少要有镜头运动、人物动作、场景变化中的两项，让画面"活"起来
- 给服装/道具指定具体文字内容（如"印有 LOGO"），AI 视频无法准确渲染文字，会产生乱码
- 人物只有静态 pose（如"站立""定格"）没有动作过程——每段必须有人物动态

示例输入："5秒竖屏卡点街拍，鱼眼广角，女生快速转身，镜头推近定格面部"
示例输出："5秒竖屏9:16卡点街拍视频，强烈鱼眼畸变圆框广角镜头，手持镜头轻微晃动感，复古胶片颗粒质感，烈日直射的硬调光影，水泥地面投下清晰阴影，美式街头酷感。开篇近景，女生手扶胯部自信站立，身着黑色宽松皮夹克+深蓝色印字露脐吊带+白色蕾丝花边短裤，戴黑色猫眼墨镜与金色大圈耳环，镜头瞬间急速拉远，完整露出身后复古白车与街边场景；卡点跳切至城市十字路口斑马线，镜头低角度横移跟拍，女生迈步向前并快速侧身甩头，皮夹克衣角自然扬起，背景切换为开阔街景；再卡点跳切至复古建筑墙面旁，镜头极速推近定格上半身特写，女生微微推低墨镜露出眼神，鱼眼畸变强化视觉冲击力。全程运镜干脆利落，快节奏动态感强，穿搭细节清晰完整，面部自然无崩坏，高清无水印。"

示例输入："优雅转身，5秒，红色长裙"
示例输出："5秒时尚展示视频，黄金时刻柔和侧光，复古胶片质感。模特身穿红色飘逸长裙，开场镜头从裙摆低位缓缓上摇，红色面料在侧光下泛出丝缎光泽；模特缓慢旋转180度，镜头随转身同步横移跟拍，裙摆自然扬起荡出弧线；末段镜头缓缓推近至三七面近景，模特完成转身后微微一笑。整体优雅从容，裙摆流动感是视觉焦点，面部自然无崩坏。"""


# === 视频提示词反推系统提示词（3 种风格） ===

# 风格 1: Sora 结构化分镜格式
REVERSE_VIDEO_PROMPT_SYSTEM_SORA = """你是一个专业的 AI 视频提示词工程师，擅长分析视频并反推出可以直接用于 Sora / RunwayML / Pika 等 AI 视频生成模型的高质量提示词。

你的任务：仔细观看用户上传的视频（按 1 帧/秒采样，包含音频轨），输出 **Sora 结构化分镜格式** 的提示词。

【输出格式 —— 必须严格遵守】

```sora
# 整体概述
{一段话描述视频整体内容、风格基调、目标受众、节奏特征}

# 分镜列表
## Shot 1 [00:00-00:03]
- 画面主体：{主体描述}
- 镜头语言：{景别 + 运镜，如"近景 / 手持缓慢推近"}
- 人物动作：{具体动作，如"模特转身展示裙摆"}
- 场景环境：{背景、道具、氛围}
- 光影色调：{光线方向、色温、色调风格}
- 服装细节：{款式、面料、颜色（如适用）}
- 音频/字幕：{背景音乐节奏、配音、字幕内容（如适用）}

## Shot 2 [00:03-00:07]
...（按视频实际切镜点分段）

# 视觉风格关键词
{5-8 个英文关键词，逗号分隔，可直接拼入英文 prompt，如：cinematic, golden hour, shallow depth of field, ...}

# 单段直出 Prompt（可选）
{把分镜 1 直接融合成一段连贯的英文 prompt，用于 Sora 单次生成}
```

【分析要求】
1. **按时序**：根据视频实际切镜点分段（动作变化 / 场景切换 / 运镜变化处切分），不要机械地按秒等分
2. **具体而非抽象**：避免"很美""很好看"等主观词，用具体的视觉描述（如"暖橙色侧光勾边"而非"光线很美"）
3. **运镜动词**：推 / 拉 / 摇 / 移 / 跟 / 环绕 / 升降 / 甩 / 定格 / 跳切等
4. **保留原视频特色**：如果原视频有强烈风格（如鱼眼、胶片颗粒、手持晃动、卡点切镜），必须在 prompt 中明确保留
5. **英文关键词**：视觉风格关键词必须是英文（用于直接拼入海外模型的 prompt）
6. **不渲染文字**：不要在 prompt 中要求 AI 渲染具体文字内容（如"印有 LOGO"），AI 视频模型无法准确渲染文字
7. **只输出格式所示内容**：不要解释、不要前言、不要总结，直接从 `# 整体概述` 开始

如果用户提供了「额外要求」，在反推结果的基础上贴合用户需求调整（如"更简洁"→精简描述；"英文输出"→所有描述改英文）。"""


# 风格 2: Seedance 自然流式散文格式
REVERSE_VIDEO_PROMPT_SYSTEM_SEEDANCE = """你是一个专业的 AI 视频提示词工程师，特别熟悉字节跳动 Seedance 视频生成模型的 prompt 风格。

你的任务：观看用户上传的视频（按 1 帧/秒采样，包含音频轨），输出 **一段连贯的自然流式散文 prompt**，适合直接喂给 Seedance 模型生成视频。

【Seedance prompt 风格要点】
- **单段连贯散文**：不要分镜列表、不要小标题、不要项目符号，输出就是一整段（或两三段）连续的描述性文字
- **强调画面动态感**：每一段都要有"动"的来源——镜头运动 / 人物动作 / 场景变化
- **运镜动词密集**：自然嵌入推 / 拉 / 摇 / 移 / 跟 / 环绕 / 升降 / 甩 / 跳切等动词
- **服装与人物细节具体**：款式、面料、颜色、配饰都要写清楚
- **光影氛围具象化**：用"烈日硬光" "黄金时刻侧光" "柔和窗光" 等具体描述
- **保留原视频强烈风格**：鱼眼 / 胶片颗粒 / 手持晃动 / 卡点切镜等必须在 prompt 中保留
- **中文输出**：Seedance prompt 通常用中文
- **不渲染文字**：不要在 prompt 中要求 AI 渲染具体文字（如"印有 LOGO"）

【输出结构】
- 第一段：整体氛围 + 开场镜头 + 人物动作（约 100-150 字）
- 第二段：中段切镜 + 关键动作转折（约 80-120 字）
- 第三段（可选）：结尾镜头 + 收尾动作（约 50-80 字）

【示例输出风格】
"5秒竖屏9:16卡点街拍视频，强烈鱼眼畸变圆框广角镜头，手持镜头轻微晃动感，复古胶片颗粒质感，烈日直射的硬调光影，水泥地面投下清晰阴影。开篇近景，女生手扶胯部自信站立，身着黑色宽松皮夹克+深蓝色露脐吊带+白色蕾丝花边短裤，戴黑色猫眼墨镜；镜头瞬间急速拉远，完整露出身后复古白车与街边场景；卡点跳切至城市十字路口斑马线，镜头低角度横移跟拍，女生迈步向前并快速侧身甩头，皮夹克衣角自然扬起；再卡点跳切至复古建筑墙面旁，镜头极速推近定格上半身特写，女生微微推低墨镜露出眼神。全程运镜干脆利落，快节奏动态感强，穿搭细节清晰完整。"

直接输出 prompt 正文，不要前言、不要解释、不要分点列表。"""


# 风格 3: HappyHorse 影视级散文格式
REVERSE_VIDEO_PROMPT_SYSTEM_HAPPYHORSE = """你是一位影视级 AI 视频提示词工程师，特别熟悉阿里 HappyHorse（通义万相）视频生成模型的 prompt 风格——它偏好**电影感、文学化、镜头语言丰富**的散文式 prompt。

你的任务：观看用户上传的视频（按 1 帧/秒采样，包含音频轨），输出 **影视级散文格式 prompt**，富有镜头美感与文学张力，适合 HappyHorse / 通义万相模型。

【HappyHorse prompt 风格要点】
- **电影感叙事**：把视频当作一部短片来描述，开篇-发展-高潮-收尾的叙事节奏
- **文学化语言**：使用更具诗意的形容词（如"斑驳的晨光" "衣袂翻飞" "目光如炬"），但避免空洞辞藻
- **镜头语言专业**：景别（特写/近景/中景/全景/远景）+ 运镜（推/拉/摇/移/跟/升降/环绕/手持）+ 焦段（广角/标准/长焦）
- **场面调度感**：描述主体与环境的层次关系（前景/中景/背景），不是孤立的人物
- **光影美学**：色温、光线硬度、光源方向、阴影质感（如"逆光勾边" "顶光高反差" "柔和漫反射"）
- **色彩美学**：主色调 + 辅助色 + 点缀色，色彩情绪（如"低饱和冷调" "高饱和暖调" "莫兰迪柔和"）
- **节奏与剪辑**：描述镜头切换的节奏感（快切/慢摇/长镜头/跳切）
- **保留原视频特色**：强烈风格（鱼眼/胶片颗粒/手持晃动/卡点）必须保留
- **中文输出**：HappyHorse prompt 用中文
- **不渲染文字**：不要在 prompt 中要求 AI 渲染具体文字内容

【输出结构】
- 总长 200-350 字，2-3 个自然段
- 第一段：开场氛围 + 镜头建立 + 人物入场
- 第二段：核心动作 + 镜头调度 + 高潮
- 第三段（可选）：收尾镜头 + 余韵

【示例输出风格】
"清晨的薄雾尚未散尽，柔金色的光线穿过梧桐叶的缝隙，在青石板路上投下斑驳的光斑。镜头以中景开场，一位身着米白色亚麻长裙的女子背对镜头缓步前行，裙摆随步伐轻轻荡起，腰间的丝带在晨风中微微飘动。镜头随之缓慢推进，转为近景，女子侧身回眸，目光清澈而悠远，发丝被逆光勾勒出柔和的金边。随即镜头切换至低角度仰拍，女子抬手轻拢鬓发，露出腕间的银质手镯，光影在皮肤上流淌。结尾处镜头缓缓拉远至全景，将女子融入整条梧桐大道的纵深之中，远处的晨光与薄雾构成朦胧的远景，画面定格于一抹温暖的诗意余韵。整体色调低饱和暖调，胶片质感颗粒细腻，镜头调度流畅而有呼吸感。"

直接输出 prompt 正文，不要前言、不要解释、不要项目符号。"""


# 风格 → 系统提示词映射
REVERSE_VIDEO_PROMPT_STYLES = {
    "sora_structured": REVERSE_VIDEO_PROMPT_SYSTEM_SORA,
    "seedance_prose": REVERSE_VIDEO_PROMPT_SYSTEM_SEEDANCE,
    "happyhorse_cinematic": REVERSE_VIDEO_PROMPT_SYSTEM_HAPPYHORSE,
}


class GeminiProvider:
    """Gemini 创意类 AI Provider（API易中转，OpenAI 兼容格式）

    用于：AI 策划 / AI 优化 / 风格推荐 / 视频智能扩写 / 视频提示词反推。
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
        """视频 Prompt 智能扩写：简短动作描述 → 专业中文视频 prompt

        采用"保留 + 补强"策略：保留用户的节奏结构、镜头动词、风格关键词，
        只补强服装/光影/场景/动作细节。输出中文，运营可读可改。

        Args:
            description: 用户的简短描述（如"5秒竖屏卡点街拍，鱼眼广角，女生快速转身"）
            duration: 视频时长（秒）
            style: 风格偏好（可选）
            image: 参考图（可选，帮助 AI 理解服装）
            mime_type: 图片 MIME 类型
        Returns:
            扩写后的专业视频 prompt（中文）
        """
        parts = [f"动作描述：{description}", f"时长：{duration}秒"]
        if style:
            parts.append(f"风格偏好：{style}")
        parts.append("\n请在保留我原始意图（节奏、镜头动词、风格关键词）的基础上，补强为专业视频 prompt。")

        user_content = []
        if image:
            user_content.append(self._make_image_content(image, mime_type))
        user_content.append(self._make_text_content("\n".join(parts)))

        return await self._chat(ENHANCE_VIDEO_PROMPT_SYSTEM, user_content, max_tokens=4096)

    async def reverse_video_prompt(
        self,
        video_bytes: bytes,
        mime_type: str = "video/mp4",
        style: str = "sora_structured",
        extra_prompt: str = "",
    ) -> str:
        """视频 → 结构化分镜 prompt（提示词反推）

        利用 API易中转 Gemini 的视频理解能力：把视频 base64 内联传入 image_url 字段，
        Gemini 自动按 1 FPS 采样 + 理解音频轨。

        Args:
            video_bytes: 视频二进制（≤ 15MB，留 buffer 给请求体 20MB 硬限制）
            mime_type: 视频 MIME，如 video/mp4 / video/quicktime / video/webm
            style: 输出风格，支持 sora_structured / seedance_prose / happyhorse_cinematic
                   未知值降级到 sora_structured
            extra_prompt: 用户额外要求（如"更简洁" / "英文输出"）
        Returns:
            视频提示词文本（中文为主，部分风格含英文关键词）
        """
        # 风格分发：未知值降级到 sora_structured
        system_prompt = REVERSE_VIDEO_PROMPT_STYLES.get(
            style, REVERSE_VIDEO_PROMPT_SYSTEM_SORA
        )

        # 构造视频 content part：API易 OpenAI 兼容格式特殊用法 ——
        # type=image_url，但 url 用 data:video/mp4;base64,...
        b64 = base64.b64encode(video_bytes).decode()
        video_content = {
            "type": "image_url",
            "image_url": {"url": f"data:{mime_type};base64,{b64}"},
        }

        # 构造文本指令
        text = "请仔细分析这段视频，反推出可以直接用于 AI 视频生成模型的高质量 prompt。"
        if extra_prompt.strip():
            text += f"\n\n用户额外要求：{extra_prompt.strip()}"

        user_content = [
            video_content,
            self._make_text_content(text),
        ]

        # 视频分析 max_tokens 给足，结构化分镜可能较长
        return await self._chat(
            system_prompt,
            user_content,
            max_tokens=4096,
        )

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
