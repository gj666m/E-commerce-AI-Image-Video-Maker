# Prompt 拼装引擎 - 加载模板 + 变量替换
import re
from pathlib import Path

from app.config import settings

# 模板目录
TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"


def load_template(task_type: str) -> str:
    """加载 Prompt 模板文件

    Args:
        task_type: 任务类型，对应模板文件名，如 'material_scene'

    Returns:
        模板内容字符串
    """
    # 模板文件名映射
    template_map = {
        "product_video": "product_video.md",
        "outfit": "outfit.md",
        "seed_grass": "seed_grass.md",
        "product_main": "product_main.md",
        "aplus": "aplus.md",
    }

    filename = template_map.get(task_type, f"{task_type}.md")
    path = TEMPLATES_DIR / filename

    if not path.exists():
        # 模板不存在时返回基础模板
        return _fallback_template(task_type)

    return path.read_text(encoding="utf-8")


def build_prompt(
    task_type: str,
    description: str,
    product_attrs: str | None = None,
    style: str | None = None,
    aspect_ratio: str = "1:1",
    user_custom: str | None = None,
    brand_gene: str | None = None,
    product_info_text: str | None = None,
) -> str:
    """拼装完整 Prompt

    Args:
        task_type: 任务类型
        description: 用户描述/场景描述
        product_attrs: 商品属性描述（P7 智能分析后填入，P2 阶段为 None）
        style: 风格偏好
        aspect_ratio: 宽高比
        user_custom: 用户自定义补充
        brand_gene: 品牌基因（可选）
        product_info_text: 商品信息文本（用户输入或AI分析），注入 prompt 帮助生图模型理解商品

    Returns:
        拼装后的完整 Prompt
    """
    template = load_template(task_type)

    # 商品属性：有分析结果用分析结果，否则用用户描述
    product_text = product_attrs or description

    # 卖点块（P7 后从分析结果提取，P2 阶段为空）
    selling_points_block = ""

    # 品牌基因块
    brand_gene_block = f"\n品牌风格要求：{brand_gene}" if brand_gene else ""

    # 用户自定义块
    user_custom_block = f"\n额外要求：{user_custom}" if user_custom else ""

    # 默认值统一中文
    default_style = "专业电商摄影"
    default_lighting = "自然柔和光线"

    # 变量替换
    variables = {
        "product_attrs": product_text,
        "scene_description": description,
        "style": style or default_style,
        "lighting": default_lighting,
        "aspect_ratio": aspect_ratio,
        "resolution": _aspect_to_resolution(aspect_ratio),
        "target_audience": "注重时尚的线上购物消费者",
        "selling_points_block": selling_points_block,
        "brand_gene_block": brand_gene_block,
        "user_custom_block": user_custom_block,
    }

    prompt = template
    for key, value in variables.items():
        prompt = prompt.replace(f"{{{{{key}}}}}", str(value))

    # 在 prompt 前面注入商品信息文本
    if product_info_text and product_info_text.strip():
        prompt = f"商品信息参考：\n{product_info_text.strip()}\n\n{prompt}"

    # 清理多余空行
    prompt = re.sub(r"\n{3,}", "\n\n", prompt).strip()

    return prompt


def _fallback_template(task_type: str) -> str:
    """模板文件不存在时的兜底模板"""
    return (
        "A professional e-commerce product photograph.\n"
        "Product: {{product_attrs}}\n"
        "Scene: {{scene_description}}\n"
        "Style: {{style}}\n"
        "Lighting: {{lighting}}\n"
        "Requirements:\n"
        "- Aspect ratio: {{aspect_ratio}}\n"
        "- High quality, professional photography standard\n"
        "{{selling_points_block}}"
        "{{brand_gene_block}}"
        "{{user_custom_block}}"
    )


def build_video_prompt(
    description: str,
    style: str | None = None,
    duration: int = 5,
    user_custom: str | None = None,
    brand_gene: str | None = None,
    camera_movement: str | None = None,
    product_info_text: str | None = None,
    has_stylized_model: bool = False,
) -> str:
    """拼装视频生成 Prompt

    Args:
        description: 视频描述/场景描述
        style: 风格偏好
        duration: 视频时长（秒）
        user_custom: 用户自定义补充
        brand_gene: 品牌基因
        camera_movement: 镜头运动（推近/拉远/环绕/平移/跟随），None 则不指定
        product_info_text: 商品信息文本，注入 prompt 帮助模型理解商品
        has_stylized_model: 是否包含风格化模特图，True 时添加引导前缀

    Returns:
        拼装后的视频 Prompt
    """
    template = load_template("product_video")

    brand_gene_block = f"\n品牌风格要求：{brand_gene}" if brand_gene else ""
    user_custom_block = f"\n额外要求：{user_custom}" if user_custom else ""

    # 镜头运动块
    camera_block = f"\n镜头运动：{camera_movement}" if camera_movement else ""

    variables = {
        "product_attrs": description,
        "scene_description": description,
        "style": style or "电影感电商时尚",
        "camera_movement": camera_movement or "缓慢跟拍",
        "duration": str(duration),
        "target_audience": "注重时尚的线上购物者",
        "brand_gene_block": brand_gene_block,
        "user_custom_block": user_custom_block,
        "camera_block": camera_block,
    }

    prompt = template
    for key, value in variables.items():
        prompt = prompt.replace(f"{{{{{key}}}}}", str(value))

    prompt = re.sub(r"\n{3,}", "\n\n", prompt).strip()

    # 在 prompt 前面注入商品信息文本
    if product_info_text and product_info_text.strip():
        prompt = f"商品信息参考：\n{product_info_text.strip()}\n\n{prompt}"

    # 风格化模特图引导前缀：引导 Seedance 从插画参考人物形象、从商品图参考服装
    if has_stylized_model:
        guide_prefix = (
            "请以上传的角色设计插画为参考生成人物外貌形象，"
            "并严格参照商品参考图还原服装细节（包括面料质感、颜色、图案和走线）。"
            "生成超写实真人实拍视频。"
        )
        prompt = guide_prefix + prompt

    return prompt


def build_model_prompt(
    gender: str = "female",
    ethnicity: str = "caucasian",
    age: str = "25-30",
    body_type: str = "standard",
    hair_desc: str = "",
    background: str = "white",
    composition: str = "full_body",
    style: str = "ecommerce",
    expression: str = "",
    pose: str = "",
    clothing: str = "",
    custom_desc: str = "",
    has_reference_image: bool = False,
) -> str:
    """拼装模特生成 Prompt

    支持两种模式：
    - 文生图（无参考图）：完整描述所有参数
    - 图生图（有参考图）：基于参考图做变体，只描述变化部分

    新增灵活参数：hair_desc/expression/pose/clothing 支持自定义文本
    """
    # ---- 共用词汇映射 ----
    gender_map = {"female": "女性", "male": "男性"}
    ethnicity_map = {
        "caucasian": "白人欧美", "asian": "东亚亚裔",
        "african": "黑人非裔", "latino": "拉美混血",
    }
    age_map = {"20-25": "年轻", "25-30": "25岁左右", "30-35": "成熟"}
    body_map = {
        "slim": "身材高挑纤细", "standard": "身材匀称",
        "athletic": "身材健美有线条感",
    }
    facial_map = {
        "caucasian": "深眼窝，五官立体，高颧骨，清晰下颌线",
        "asian": "柔和五官，自然肤色",
        "african": "深肤色，饱满唇形",
        "latino": "小麦色肌肤，混血五官",
    }
    background_map = {
        "white": "纯白色背景，专业影棚",
        "light_gray": "浅灰色背景，极简影棚",
        "outdoor": "欧洲街景背景，户外自然场景",
    }
    composition_map = {
        "full_body": "全身构图",
        "half_body": "半身构图",
    }
    style_map = {
        "ecommerce": {"lighting": "专业影棚柔光，光线均匀明亮", "photography": "商业摄影"},
        "fashion": {"lighting": "时尚杂志风格，高端摄影质感", "photography": "时尚杂志摄影"},
        "casual": {"lighting": "自然光线", "photography": "休闲随性摄影"},
    }

    # ---- 填充变量 ----
    sty = style_map.get(style, style_map["ecommerce"])

    # 发型：用户自定义 > 默认
    if not hair_desc:
        hair_desc = "金色长直发"

    # 表情：用户自定义 > 默认
    if not expression:
        expression = "表情自然"

    # 姿势：用户自定义 > 根据构图
    if not pose:
        pose = "自然站立，双手自然下垂，身体放松" if composition == "full_body" else "上半身微侧"

    # 服装：用户自定义 > 默认
    if not clothing:
        clothing = "穿着简约白色T恤和蓝色牛仔裤"

    # 额外描述
    custom_block = custom_desc.strip() if custom_desc else ""

    # ---- 组装自然语言主体描述（句号分段：人物→动作→环境） ----
    age_desc = age_map.get(age, "25岁左右")
    ethnicity_desc = ethnicity_map.get(ethnicity, "白人欧美")
    gender_desc = gender_map.get(gender, "女性")
    facial = facial_map.get(ethnicity, "五官端正")
    composition_desc = composition_map.get(composition, "全身构图")
    background_desc = background_map.get(background, "纯白色背景，专业影棚")

    if has_reference_image:
        # ---- 图生图模式：强调参考面部特征 ----
        template = load_template("model_ref")
        desc = (
            f"参考输入图片中人物的面部特征，"
            f"生成一位{age_desc}{ethnicity_desc}{gender_desc}，{facial}，{hair_desc}。"
        )
    else:
        # ---- 文生图模式：完整描述 ----
        template = load_template("model_gen")
        body_type_desc = body_map.get(body_type, "身材匀称")
        desc = (
            f"一位{age_desc}{ethnicity_desc}{gender_desc}，{body_type_desc}，"
            f"{facial}，{hair_desc}。"
        )

    desc += f"她{clothing}，{pose}，{expression}。"
    desc += f"{composition_desc}，{background_desc}，{sty['lighting']}，{sty['photography']}风格。"
    if custom_block:
        desc += custom_block

    prompt = template.replace("{{main_description}}", desc)
    prompt = re.sub(r"\n{3,}", "\n\n", prompt).strip()
    return prompt


def _aspect_to_resolution(aspect_ratio: str) -> str:
    """宽高比转中文描述（Seedream 通过 prompt 控制实际比例）"""
    ratio_desc = {
        "1:1": "正方形构图，1:1 比例",
        "3:4": "竖版构图，3:4 比例（适合小红书）",
        "4:3": "横版构图，4:3 比例",
        "4:5": "竖版构图，4:5 比例（适合 Instagram）",
        "5:4": "横版构图，5:4 比例",
        "9:16": "竖版构图，9:16 比例（适合短视频封面）",
        "16:9": "横版宽幅构图，16:9 比例（适合横屏展示）",
        "61:25": "宽幅横版构图，61:25 比例（亚马逊 A+ Banner）",
    }
    return ratio_desc.get(aspect_ratio, "正方形构图，1:1 比例")


def build_quick_prompt(description: str, aspect_ratio: str = "1:1") -> str:
    """快速生图 Prompt：用户描述原样透传，仅前置比例描述

    不走任何模板，用户写什么就生成什么。比例描述复用 _aspect_to_resolution()，
    因为 Seedream/GPT-Image 等模型靠 prompt 前缀控制实际输出比例。
    """
    ratio_desc = _aspect_to_resolution(aspect_ratio)
    return f"{ratio_desc}，{description.strip()}"


def build_seed_grass_prompt(
    description: str,
    persona: str | None = None,
    scene: str | None = None,
    style: str | None = None,
    aspect_ratio: str = "9:16",
    user_custom: str | None = None,
    product_info_text: str | None = None,
) -> str:
    """拼装种草图生成 Prompt

    Args:
        description: 用户描述/场景描述
        persona: 博主人设描述（如"25岁欧美女性，极简穿搭风格"）
        scene: 场景描述（如"咖啡店窗边，温暖午后"）
        style: 风格偏好
        aspect_ratio: 宽高比
        user_custom: 用户自定义补充
        product_info_text: 商品信息文本

    Returns:
        拼装后的种草图 Prompt
    """
    template = load_template("seed_grass")

    # 人设描述：有则用，无则默认
    persona_desc = persona or "25岁左右时尚女性，气质清新自然"

    # 场景：scene 优先，否则用 description
    scene_description = scene or description

    user_custom_block = f"\n额外要求：{user_custom}" if user_custom else ""

    variables = {
        "persona_desc": persona_desc,
        "scene_description": scene_description,
        "style": style or "手机随拍风格，生活化氛围",
        "resolution": _aspect_to_resolution(aspect_ratio),
        "user_custom_block": user_custom_block,
    }

    prompt = template
    for key, value in variables.items():
        prompt = prompt.replace(f"{{{{{key}}}}}", str(value))

    prompt = re.sub(r"\n{3,}", "\n\n", prompt).strip()

    # 商品信息注入
    if product_info_text and product_info_text.strip():
        prompt = f"商品信息参考：\n{product_info_text.strip()}\n\n{prompt}"

    return prompt


def build_product_main_prompt(
    description: str,
    user_custom: str | None = None,
    product_info_text: str | None = None,
) -> str:
    """拼装商品主图生成 Prompt

    Args:
        description: 商品描述（用户输入或 AI 分析）
        user_custom: 用户自定义补充
        product_info_text: 商品信息文本

    Returns:
        拼装后的商品主图 Prompt
    """
    template = load_template("product_main")

    user_custom_block = f"\n额外要求：{user_custom}" if user_custom else ""

    variables = {
        "product_description": description,
        "user_custom_block": user_custom_block,
    }

    prompt = template
    for key, value in variables.items():
        prompt = prompt.replace(f"{{{{{key}}}}}", str(value))

    prompt = re.sub(r"\n{3,}", "\n\n", prompt).strip()

    if product_info_text and product_info_text.strip():
        prompt = f"商品信息参考：\n{product_info_text.strip()}\n\n{prompt}"

    return prompt


def build_aplus_prompt(
    selling_point: str = "",
    headline: str = "",
    body_text: str = "",
    layout: str = "left_image_right_text",
    scene: str = "",
    style: str | None = None,
    aspect_ratio: str = "61:25",
    user_custom: str | None = None,
    product_info_text: str | None = None,
) -> str:
    """拼装 A+ 图生成 Prompt

    Args:
        selling_point: 核心卖点
        headline: 标题文字（会渲染到图片中）
        body_text: 正文文字（会渲染到图片中）
        layout: 布局类型
        scene: 场景/背景描述
        style: 整体风格
        aspect_ratio: 宽高比
        user_custom: 用户自定义补充
        product_info_text: 商品信息文本

    Returns:
        拼装后的 A+ 图 Prompt
    """
    template = load_template("aplus")

    layout_map = {
        "left_image_right_text": "左图右文（左侧商品图，右侧文字说明）",
        "right_image_left_text": "右图左文（右侧商品图，左侧文字说明）",
        "top_image_bottom_text": "上图下文（上方商品图，下方文字说明）",
        "full_image_with_overlay": "全图覆盖文字（商品图全幅，文字半透明叠加）",
    }

    user_custom_block = f"\n额外要求：{user_custom}" if user_custom else ""

    variables = {
        "layout_type": layout_map.get(layout, layout),
        "selling_point": selling_point or "商品核心卖点",
        "headline": headline or "Product Title",
        "body_text": body_text or "Product description text",
        "scene": scene or "简洁专业背景",
        "style": style or "现代简约电商风格",
        "aspect_ratio": _aspect_to_resolution(aspect_ratio),
        "user_custom_block": user_custom_block,
    }

    prompt = template
    for key, value in variables.items():
        prompt = prompt.replace(f"{{{{{key}}}}}", str(value))

    prompt = re.sub(r"\n{3,}", "\n\n", prompt).strip()

    if product_info_text and product_info_text.strip():
        prompt = f"商品信息参考：\n{product_info_text.strip()}\n\n{prompt}"

    return prompt
