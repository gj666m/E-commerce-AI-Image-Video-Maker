<template>
  <div class="video-gen">
    <el-page-header @back="$router.push('/')">
      <template #content>
        <span>视频生成</span>
      </template>
    </el-page-header>

    <el-row :gutter="20" class="main-content">
      <!-- 左侧：输入区 -->
      <el-col :span="12">
        <el-card>
          <el-form label-position="top">
            <!-- 商品图上传（必传） -->
            <el-form-item label="商品图（必传，1-6张）">
              <div v-if="productImages.length > 0" class="ref-images-grid">
                <div v-for="(img, idx) in productImages" :key="'p'+idx" class="ref-image-item">
                  <el-image
                    :src="'data:image/png;base64,' + img"
                    fit="contain"
                    class="ref-image-thumb"
                  />
                  <el-button type="danger" size="small" circle @click="removeProductImage(idx)">
                    <el-icon><Close /></el-icon>
                  </el-button>
                </div>
              </div>
              <ImageUploader v-if="productImages.length < 6" v-model="form.image" @update:model-value="(f: File | null) => onImageAdd(f, 'product')" />
            </el-form-item>

            <!-- 模特素材图上传（可选） -->
            <el-form-item>
              <template #label>
                <span>模特素材图（可选，0-3张）</span>
              </template>
              <div v-if="modelImages.length > 0" class="ref-images-grid">
                <div v-for="(img, idx) in modelImages" :key="'m'+idx" class="ref-image-item">
                  <el-image
                    :src="'data:image/png;base64,' + img"
                    fit="contain"
                    class="ref-image-thumb"
                  />
                  <el-button type="danger" size="small" circle @click="removeModelImage(idx)">
                    <el-icon><Close /></el-icon>
                  </el-button>
                </div>
              </div>
              <ImageUploader v-if="modelImages.length < 3" v-model="form.image" @update:model-value="(f: File | null) => onImageAdd(f, 'model')" />
              <div class="face-switch">
                <el-switch
                  v-model="modelHasFace"
                  active-text="含人脸（自动风格化）"
                  inactive-text="无人脸"
                />
              </div>
            </el-form-item>

            <!-- 商品信息（结构化，可 AI 分析） -->
            <ProductInfoForm v-model="productInfo" :image="analyzableImage" />

            <!-- 视频描述 -->
            <el-form-item label="视频描述" required>
              <div class="description-row">
                <el-input
                  v-model="form.description"
                  type="textarea"
                  :rows="3"
                  placeholder="描述你想要的视频效果，如：模特穿着连衣裙在花园中优雅转身..."
                  style="flex: 1"
                />
                <el-button
                  type="success"
                  plain
                  :loading="optimizing"
                  :disabled="!analyzableImage"
                  @click="optimizeDescription"
                  style="margin-left: 8px; align-self: flex-start;"
                >
                  AI 优化
                </el-button>
              </div>
              <div class="preset-tags">
                <el-tag
                  v-for="tag in motionPresets"
                  :key="tag"
                  size="small"
                  effect="plain"
                  class="preset-tag"
                  @click="appendDescription(tag)"
                >
                  {{ tag }}
                </el-tag>
              </div>
            </el-form-item>

            <!-- 风格 + 镜头运动 -->
            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="风格">
                  <el-select v-model="form.style" placeholder="选择风格" clearable>
                    <el-option label="生活方式" value="lifestyle" />
                    <el-option label="时尚秀场" value="fashion show" />
                    <el-option label="棚拍" value="studio" />
                    <el-option label="户外自然" value="outdoor" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="镜头运动">
                  <el-select v-model="form.cameraMovement" placeholder="选择镜头运动" clearable>
                    <el-option label="缓慢环绕" value="缓慢环绕" />
                    <el-option label="推近特写" value="缓慢推近，从全景到特写" />
                    <el-option label="拉远全景" value="缓慢拉远，从特写到全景" />
                    <el-option label="水平平移" value="水平平移，从左到右" />
                    <el-option label="跟随移动" value="跟随主体移动" />
                    <el-option label="低角度仰拍" value="低角度仰拍，缓慢上升" />
                    <el-option label="静态固定" value="固定机位，画面稳定不动" />
                  </el-select>
                </el-form-item>
              </el-col>
            </el-row>

            <!-- 比例 + 时长 + 音频 -->
            <el-row :gutter="12">
              <el-col :span="8">
                <el-form-item label="视频比例">
                  <el-select v-model="form.ratio">
                    <el-option label="16:9 横屏" value="16:9" />
                    <el-option label="9:16 竖屏" value="9:16" />
                    <el-option label="1:1 方形" value="1:1" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="时长">
                  <el-radio-group v-model="form.duration">
                    <el-radio-button :value="5">5秒</el-radio-button>
                    <el-radio-button :value="10">10秒</el-radio-button>
                    <el-radio-button :value="15">15秒</el-radio-button>
                    <el-radio-button :value="-1">自动</el-radio-button>
                  </el-radio-group>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="音频">
                  <el-switch
                    v-model="form.generateAudio"
                    active-text="开"
                    inactive-text="关"
                  />
                </el-form-item>
              </el-col>
            </el-row>

            <!-- Prompt 编辑 -->
            <PromptEditor v-model="form.customPrompt" />

            <!-- 模型选择 -->
            <el-form-item label="模型">
              <ModelSelector
                v-model="form.modelName"
                :models="videoModels"
              />
            </el-form-item>

            <!-- 生成按钮 -->
            <el-form-item>
              <el-button
                type="primary"
                size="large"
                :loading="submitting"
                :disabled="!canGenerate"
                @click="handleSubmit"
                style="width: 100%"
              >
                {{ submitting ? '提交中...' : '生成视频' }}
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <!-- 右侧：结果区 -->
      <el-col :span="12">
        <!-- 等待提交 -->
        <el-card v-if="!taskId">
          <el-empty description="填写参数后点击生成视频" />
        </el-card>

        <!-- 进度展示 -->
        <el-card v-else-if="taskStatus !== 'completed'">
          <div class="progress-area">
            <h4>视频生成中</h4>
            <el-progress
              :percentage="progress"
              :status="taskStatus === 'failed' ? 'exception' : undefined"
              :stroke-width="20"
              :text-inside="true"
            />
            <p class="status-text">
              <el-icon class="is-loading" v-if="taskStatus === 'processing'"><Loading /></el-icon>
              {{ statusText }}
            </p>
            <el-button
              v-if="taskStatus === 'failed'"
              type="primary"
              style="margin-top: 16px;"
              @click="handleSubmit"
            >
              重新生成
            </el-button>
          </div>
        </el-card>

        <!-- 完成 -->
        <el-card v-else>
          <VideoPreview
            :video-url="videoUrl!"
            :model-used="modelUsed"
            :cost="cost"
          />

          <div style="text-align: center; margin-top: 12px;">
            <el-button type="primary" plain @click="handleSubmit">
              重新生成
            </el-button>
          </div>

          <el-divider />

          <el-collapse>
            <el-collapse-item title="使用的 Prompt" name="prompt">
              <pre class="prompt-text">{{ promptUsed }}</pre>
            </el-collapse-item>
          </el-collapse>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Loading, Close } from '@element-plus/icons-vue'
import ImageUploader from '../components/ImageUploader.vue'
import ModelSelector from '../components/ModelSelector.vue'
import PromptEditor from '../components/PromptEditor.vue'
import VideoPreview from '../components/VideoPreview.vue'
import ProductInfoForm from '../components/ProductInfoForm.vue'
import { submitVideo, getVideoStatus, getVideoModels, analyzeFree } from '../api'
import type { ModelInfo } from '../types'

const submitting = ref(false)
const taskId = ref<string | null>(null)
const taskStatus = ref<string>('pending')
const progress = ref(0)
const videoUrl = ref<string | null>(null)
const modelUsed = ref('')
const promptUsed = ref('')
const cost = ref(0)

let pollTimer: ReturnType<typeof setInterval> | null = null

const form = ref({
  image: null as File | null,
  description: '',
  style: '',
  duration: 5,
  modelName: 'mock_video',
  customPrompt: '',
  ratio: '16:9',
  generateAudio: false,
  cameraMovement: '',
})

const videoModels = ref<ModelInfo[]>([])

// 运动描述预设标签
const motionPresets = [
  '优雅转身', '走猫步', '捋头发', '眼看镜头',
  '展示服装细节', '从左走到右', '自然走动', '对着镜头微笑',
  '提裙摆', '整理衣领', '侧身回眸',
]

function appendDescription(tag: string) {
  if (form.value.description) {
    form.value.description += '，' + tag
  } else {
    form.value.description = tag
  }
}

// 商品图（base64 列表）
const productImages = ref<string[]>([])
// 模特素材图（base64 列表）
const modelImages = ref<string[]>([])
// 模特图含人脸开关
const modelHasFace = ref(true)

// 商品信息（自由文本）
const productInfo = ref('')

const canGenerate = computed(() =>
  form.value.description.trim().length > 0 && productImages.value.length > 0
)

// 供 ProductInfoForm 分析的图片（取商品图第一张）
const analyzableImage = computed<File | null>(() => {
  if (productImages.value.length > 0) return base64ToFile(productImages.value[0], 'product_image.png')
  return null
})

// AI 优化描述
const optimizing = ref(false)

async function optimizeDescription() {
  const img = analyzableImage.value
  if (!img) {
    ElMessage.warning('请先上传商品图')
    return
  }
  optimizing.value = true
  try {
    const existingDesc = form.value.description || ''
    const prompt = existingDesc
      ? `请根据这张商品图，优化以下视频描述，使其更生动精准（不超过200字）：\n${existingDesc}`
      : '请根据这张商品图，生成一段短视频描述（中文），描述语公式：主体(人物和商品)+场景+运动+镜头语言+光影。要求简洁精准，不超过200字。直接输出描述文本，不要输出其他内容。'
    const resp = await analyzeFree(img, prompt)
    if (resp.text) {
      form.value.description = resp.text
    }
    ElMessage.success('描述已优化')
  } catch {
    ElMessage.error('AI 优化失败，请手动填写')
  } finally {
    optimizing.value = false
  }
}

onMounted(async () => {
  // 从图片生成页接收参考图（放入商品图区）
  const refImagesStr = sessionStorage.getItem('video_ref_images')
  if (refImagesStr) {
    try {
      const images: string[] = JSON.parse(refImagesStr)
      productImages.value = images
    } catch {
      productImages.value = [refImagesStr]
    }
    sessionStorage.removeItem('video_ref_images')
  } else {
    const singleImage = sessionStorage.getItem('video_ref_image')
    if (singleImage) {
      productImages.value = [singleImage]
      sessionStorage.removeItem('video_ref_image')
    }
  }
  // 加载视频模型列表
  try {
    const data = await getVideoModels()
    videoModels.value = data.models
    if (data.default) form.value.modelName = data.default
  } catch {
    ElMessage.error('获取视频模型列表失败')
  }
})

const statusText = computed(() => {
  switch (taskStatus.value) {
    case 'pending': return '任务排队中...'
    case 'processing': return `正在生成视频 (${progress.value}%)...`
    case 'failed': return '生成失败，请重试'
    default: return ''
  }
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})

function removeProductImage(idx: number) {
  productImages.value.splice(idx, 1)
}

function removeModelImage(idx: number) {
  modelImages.value.splice(idx, 1)
}

// 本地上传新图时加入对应区域
function onImageAdd(file: File | null, target: 'product' | 'model') {
  if (!file) return
  const reader = new FileReader()
  reader.onload = () => {
    const base64 = (reader.result as string).split(',')[1]
    if (base64) {
      if (target === 'product') {
        productImages.value.push(base64)
      } else {
        modelImages.value.push(base64)
      }
      form.value.image = null // 清空 uploader
    }
  }
  reader.readAsDataURL(file)
}

function base64ToFile(base64: string, filename: string): File {
  const bstr = atob(base64)
  const n = bstr.length
  const u8arr = new Uint8Array(n)
  for (let i = 0; i < n; i++) u8arr[i] = bstr.charCodeAt(i)
  return new File([u8arr], filename, { type: 'image/png' })
}

async function handleSubmit() {
  if (!canGenerate.value) return

  submitting.value = true
  taskId.value = null
  taskStatus.value = 'pending'
  progress.value = 0
  videoUrl.value = null

  try {
    const data = await submitVideo({
      product_images: productImages.value.map((b64, i) =>
        base64ToFile(b64, `product_${i}.png`)
      ),
      model_images: modelImages.value.length > 0
        ? modelImages.value.map((b64, i) =>
            base64ToFile(b64, `model_${i}.png`)
          )
        : undefined,
      model_has_face: modelImages.value.length > 0 ? modelHasFace.value : undefined,
      description: form.value.description,
      duration: form.value.duration,
      model_name: form.value.modelName,
      style: form.value.style || undefined,
      custom_prompt: form.value.customPrompt || undefined,
      ratio: form.value.ratio,
      generate_audio: form.value.generateAudio,
      camera_movement: form.value.cameraMovement || undefined,
      product_info: productInfo.value || undefined,
    })
    taskId.value = data.task_id
    taskStatus.value = 'processing'
    startPolling()
  } catch (e: any) {
    const msg = e?.response?.data?.detail || '提交失败，请稍后重试'
    ElMessage.error(msg)
  } finally {
    submitting.value = false
  }
}

function startPolling() {
  if (pollTimer) clearInterval(pollTimer)

  pollTimer = setInterval(async () => {
    if (!taskId.value) return

    try {
      const data = await getVideoStatus(taskId.value)
      taskStatus.value = data.status
      progress.value = data.progress
      modelUsed.value = data.model_used
      promptUsed.value = data.prompt_used
      cost.value = data.cost

      if (data.video_url) {
        videoUrl.value = data.video_url
      }

      if (data.status === 'completed') {
        clearInterval(pollTimer!)
        pollTimer = null
        ElMessage.success('视频生成完成')
      } else if (data.status === 'failed') {
        clearInterval(pollTimer!)
        pollTimer = null
        ElMessage.error(data.error || '视频生成失败')
      }
    } catch {
      clearInterval(pollTimer!)
      pollTimer = null
      ElMessage.error('查询状态失败')
    }
  }, 2000)
}
</script>

<style scoped>
.video-gen {
  max-width: 1200px;
  margin: 20px auto;
  padding: 0 20px;
}

.main-content {
  margin-top: 20px;
}

.progress-area {
  text-align: center;
  padding: 40px 20px;
}

.progress-area h4 {
  margin-bottom: 20px;
  color: #303133;
}

.progress-area .el-progress {
  margin-bottom: 16px;
}

.status-text {
  color: #909399;
  font-size: 14px;
}

.status-text .el-icon {
  margin-right: 4px;
  vertical-align: middle;
}

.prompt-text {
  white-space: pre-wrap;
  word-break: break-all;
  font-size: 13px;
  color: #606266;
  background: #f5f7fa;
  padding: 12px;
  border-radius: 4px;
  max-height: 200px;
  overflow-y: auto;
}

.ref-images-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
}

.ref-image-item {
  position: relative;
  display: inline-block;
}

.ref-image-thumb {
  width: 80px;
  height: 80px;
  border-radius: 6px;
  border: 1px solid #ebeef5;
}

.ref-image-item .el-button {
  position: absolute;
  top: -6px;
  right: -6px;
  width: 20px;
  height: 20px;
}

.face-switch {
  margin-top: 8px;
}

.preset-tags {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.preset-tag {
  cursor: pointer;
  transition: all 0.2s;
}

.preset-tag:hover {
  color: #409eff;
  border-color: #409eff;
}

.description-row {
  display: flex;
  width: 100%;
}
</style>
