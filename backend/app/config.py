# 配置管理 - Pydantic Settings 加载 .env
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# 先把 .env 加载进 os.environ，供其他模块（如 auth.py 的 JWT_SECRET）直接读取
load_dotenv()


class Settings(BaseSettings):
    # 应用配置
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8001
    debug: bool = True

    # 图片处理
    max_upload_size_mb: int = 20
    image_max_long_edge: int = 2048

    # 视频临时文件
    video_temp_dir: str = "temp_videos"
    video_expire_seconds: int = 259200  # 3 天过期（文件保留期，与图片历史文件保留期一致）
    video_history_record_expire_days: int = 90  # 视频任务元数据保留期（到期删整行）

    # AI 模型 API Keys（按需配置，不配则为空字符串）
    openai_api_key: str = ""
    fal_api_key: str = ""
    kling_api_key: str = ""
    photoroom_api_key: str = ""
    volcengine_api_key: str = ""
    volcengine_model_id: str = "doubao-seedream-4-5-251128"
    volcengine_vision_model: str = "doubao-seed-2-0-lite-260428"
    volcengine_seedance_endpoint: str = ""  # Seedance 2.0 视频 API endpoint ID（火山方舟直连）
    # Seedance 2.0 中转站（API易，不限并发不排队）
    seedance_apiyi_api_key: str = ""
    seedance_apiyi_base_url: str = "https://api.apiyi.com/seedance/api/v3"
    seedance_apiyi_model: str = "doubao-seedance-2-0-260128"
    # Seedance 2.0 Mini（火山官网直连，半价；API Key 直接作 Bearer，不走中转）
    seedance_mini_api_key: str = ""
    seedance_mini_model: str = "doubao-seedance-2-0-mini-260615"
    # API易账户系统令牌（个人中心生成，用于 /api/user/self 查余额；非业务 sk- key）
    apiyi_balance_token: str = ""
    # Seedream 图片生成（API易中转站，2026-06-17 由火山方舟官方切中转）
    # 注意：4.5/5.0 使用独立 API Key + Model ID（无 doubao- 前缀）
    seedream_apiyi_base_url: str = "https://api.apiyi.com/v1"
    seedream45_apiyi_api_key: str = ""
    seedream45_apiyi_model: str = "seedream-4-5-251128"
    seedream5_apiyi_api_key: str = ""
    seedream5_apiyi_model: str = "seedream-5-0-260128"
    # Seedream 5.0 Lite（独立 API Key）
    seedream5_api_key: str = ""
    seedream5_model_id: str = "doubao-seedream-5-0-lite"

    # DeepSeek V4（文本分析，视觉暂不可用）
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-v4-flash"
    deepseek_base_url: str = "https://api.deepseek.com"

    # Nano Banana 2（API易中转站，Gemini 图片生成）
    nanobanana_api_key: str = ""
    nanobanana_base_url: str = "https://api.apiyi.com"
    nanobanana_model: str = "gemini-3.1-flash-image-preview"

    # GPT-Image-2-All（API易中转站，OpenAI Images API 格式）
    gptimage_api_key: str = ""
    gptimage_base_url: str = "https://api.apiyi.com"
    gptimage_model: str = "gpt-image-2-all"

    # GPT-Image-2-VIP（API易中转站，支持 size + 4K）
    gptimage_vip_api_key: str = ""
    gptimage_vip_base_url: str = "https://api.apiyi.com"
    gptimage_vip_model: str = "gpt-image-2-vip"

    # Gemini（API易中转站，创意类 AI 任务：AI策划/AI优化/智能扩写）
    gemini_apiyi_api_key: str = ""
    gemini_apiyi_base_url: str = "https://api.apiyi.com/v1"
    gemini_apiyi_model: str = "gemini-3.5-flash"

    # Claude Sonnet 4.6（API易中转站，Anthropic 原生端点，用于对话式 Agent）
    claude_apiyi_api_key: str = ""
    claude_apiyi_base_url: str = "https://api.apiyi.com"
    claude_apiyi_model: str = "claude-sonnet-4-6"

    # 对话式 Agent 配置
    agent_max_qc_retries: int = 3          # 质检重试上限
    agent_image_store_ttl: int = 3600      # ImageStore 条目过期秒数（1 小时）
    agent_request_timeout: int = 300       # 单次对话请求超时秒数
    agent_recursion_limit: int = 30        # LangGraph 递归步数上限（防死循环）
    agent_checkpoint_db: str = "data/agent_checkpoints.db"  # LangGraph checkpoint DB（独立于 app.db）

    # 模特库
    model_store_dir: str = "assets/models"

    # 图片生成历史
    generation_history_dir: str = "assets/generations"
    generation_history_expire_days: int = 3  # 文件过期天数（到期删盘 + 标记 file_expired）
    generation_history_record_expire_days: int = 90  # 记录元数据保留天数（到期删整行）

    # 素材资产库视频缩略图（沉淀时 ffmpeg 抽首帧存 jpg）
    asset_thumb_dir: str = "assets/asset_thumbs"

    # 模型默认配置
    default_image_model: str = "gpt-image-2"

    @property
    def has_openai(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def has_fal(self) -> bool:
        return bool(self.fal_api_key)

    @property
    def has_kling(self) -> bool:
        return bool(self.kling_api_key)

    @property
    def has_photoroom(self) -> bool:
        return bool(self.photoroom_api_key)

    @property
    def has_volcengine(self) -> bool:
        return bool(self.volcengine_api_key)

    @property
    def has_seedance(self) -> bool:
        return bool(self.volcengine_seedance_endpoint)

    @property
    def has_seedance_apiyi(self) -> bool:
        return bool(self.seedance_apiyi_api_key)

    @property
    def has_seedance_mini(self) -> bool:
        return bool(self.seedance_mini_api_key)

    @property
    def has_seedream45_apiyi(self) -> bool:
        return bool(self.seedream45_apiyi_api_key)

    @property
    def has_seedream5_apiyi(self) -> bool:
        return bool(self.seedream5_apiyi_api_key)

    @property
    def has_deepseek(self) -> bool:
        return bool(self.deepseek_api_key)

    @property
    def has_product_analysis(self) -> bool:
        """商品视觉分析是否可用（依赖火山引擎视觉模型）"""
        return bool(self.volcengine_api_key)

    @property
    def has_nanobanana(self) -> bool:
        return bool(self.nanobanana_api_key)

    @property
    def has_gptimage(self) -> bool:
        return bool(self.gptimage_api_key)

    @property
    def has_gptimage_vip(self) -> bool:
        return bool(self.gptimage_vip_api_key)

    @property
    def has_seedream5(self) -> bool:
        return bool(self.seedream5_api_key)

    @property
    def has_gemini(self) -> bool:
        return bool(self.gemini_apiyi_api_key)

    @property
    def has_claude(self) -> bool:
        return bool(self.claude_apiyi_api_key)

    @property
    def has_any_provider(self) -> bool:
        """是否有至少一个可用的 AI 模型"""
        return any([self.has_openai, self.has_fal, self.has_kling, self.has_photoroom, self.has_volcengine, self.has_seedream45_apiyi, self.has_seedream5, self.has_seedream5_apiyi, self.has_deepseek, self.has_seedance, self.has_seedance_apiyi, self.has_seedance_mini, self.has_nanobanana, self.has_gptimage, self.has_gptimage_vip])

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
