<template>
  <div class="quick-gen">
    <el-row :gutter="24" class="main-content">
      <!-- 左侧：极简表单 -->
      <el-col :span="12">
        <el-card>
          <div class="page-header">
            <span class="section-icon gradient-purple"><el-icon :size="20"><MagicStick /></el-icon></span>
            <div>
              <h2 class="page-title">
                快速生图
                <el-tooltip content="查看使用说明" placement="top">
                  <el-icon class="help-icon" @click="goGuide('quick-image')"><QuestionFilled /></el-icon>
                </el-tooltip>
              </h2>
              <p class="page-sub">上传参考图（可选）+ 一句话描述 + 选模型 → 出图</p>
            </div>
          </div>

          <el-form label-position="top">
            <!-- 参考图上传（可选，0-6 张） -->
            <el-form-item>
              <template #label>
                <div class="section-title">
                  <span class="section-icon gradient-blue"><el-icon><Upload /></el-icon></span>
                  参考图（可选）
                </div>
              </template>
              <div class="ref-images-area">
                <div class="ref-thumbnails">
                  <div v-for="(preview, idx) in refPreviews" :key="idx" class="ref-thumb thumb-item">
                    <img :src="preview" />
                    <span class="thumb-remove" @click="removeRefImage(idx)"><el-icon :size="12"><Close /></el-icon></span>
                  </div>
                  <el-upload
                    v-if="refImages.length < 6"
                    :auto-upload="false"
                    :show-file-list="false"
                    :on-change="handleRefImage"
                    accept=".jpg,.jpeg,.png,.webp"
                    class="ref-add-btn upload-add-btn"
                  >
                    <div class="add-slot">
                      <el-icon :size="24" color="#409eff"><Plus /></el-icon>
                      <span>{{ refImages.length === 0 ? '上传参考图' : '添加更多' }}</span>
                    </div>
                  </el-upload>
                </div>
                <div class="ref-hint">不传图 = 纯文生图；传图 = 参考图生图（最多 6 张）</div>
              </div>
            </el-form-item>

            <!-- 描述（必填） -->
            <el-form-item required>
              <template #label>
                <div class="section-title">
                  <span class="section-icon gradient-green"><el-icon><EditPen /></el-icon></span>
                  描述 / Prompt
                </div>
              </template>
              <MentionTextarea
                v-model="form.description"
                :refs-source="refsSource"
                :rows="5"
                placeholder="描述你想要的画面，例如：一位欧美女性穿着红色连衣裙站在海边，日落光线，全身照，真实摄影风格"
              />
            </el-form-item>

            <!-- 模型 + 比例 + 张数 -->
            <el-form-item label="模型">
              <ModelSelector v-model="form.modelName" :models="modelList" />
            </el-form-item>

            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="比例">
                  <el-select v-model="form.aspectRatio">
                    <el-option label="1:1 正方形" value="1:1" />
                    <el-option label="3:4 竖版（小红书）" value="3:4" />
                    <el-option label="4:3 横版" value="4:3" />
                    <el-option label="4:5 竖版（Instagram）" value="4:5" />
                    <el-option label="9:16 竖版（短视频）" value="9:16" />
                    <el-option label="16:9 横版（横屏）" value="16:9" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="张数">
                  <el-select v-model="form.count">
                    <el-option :value="1" label="生成 1 张" />
                    <el-option :value="2" label="生成 2 张" />
                    <el-option :value="3" label="生成 3 张" />
                    <el-option :value="4" label="生成 4 张" />
                  </el-select>
                </el-form-item>
              </el-col>
            </el-row>

            <!-- 生成按钮 -->
            <el-form-item>
              <el-button
                type="primary"
                size="large"
                :loading="loading"
                :disabled="!canGenerate"
                @click="handleGenerate"
                style="width: 100%"
              >
                <el-icon v-if="!loading" style="margin-right: 6px"><Promotion /></el-icon>
                {{ loading ? '生成中...' : '生成图片' }}
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <!-- 右侧：结果区 -->
      <el-col :span="12">
        <el-card v-if="cards.length === 0">
          <el-empty description="输入描述后点击生成" />
        </el-card>

        <el-card v-else>
          <ResultCardManager
            :cards="cards"
            :model-used="modelUsed"
            :total-cost="totalCost"
            :currency="currency"
            :models="modelList"
            @retry="handleRetry"
            @retry-with-prompt="handleRetryWithPrompt"
            @remove="handleRemove"
            @compare-model="handleCompareModel"
          />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Plus, Close, Upload, EditPen, MagicStick, Promotion, QuestionFilled } from '@element-plus/icons-vue'
import ModelSelector from '../components/ModelSelector.vue'
import ResultCardManager from '../components/ResultCardManager.vue'
import { generateImage, getModels, getErrorMessage } from '../api'
import type { ModelInfo, ResultCard } from '../types'
import { useImageList } from '../composables/useImageList'
import MentionTextarea from '../components/MentionTextarea.vue'

const router = useRouter()
function goGuide(anchor: string) {
  router.push({ path: '/user-guide', hash: `#${anchor}` })
}

const loading = ref(false)
const modelList = ref<ModelInfo[]>([])

// 结果卡片
const cards = ref<ResultCard[]>([])
const modelUsed = ref('')
const totalCost = ref(0)
const currency = ref('¥')

// 参考图（可选，0-6 张）
const { files: refImages, previews: refPreviews, add: handleRefImage, remove: removeRefImage } = useImageList(6, '参考图')

const form = ref({
  description: '',
  aspectRatio: '3:4',
  modelName: 'volcengine',
  count: 1,
})

// @ 引用数据源：参考图按上传顺序映射为 RefItem[]
const refsSource = computed(() =>
  refPreviews.value.map((url, i) => ({
    preview_url: url,
    filename: refImages.value[i]?.name || `参考图${i + 1}`,
  })),
)

const canGenerate = computed(() => form.value.description.trim().length > 0)

// 上一次生成参数（用于重试）
let lastGenParams: {
  images: File[]
  description: string
  aspectRatio: string
  modelName: string
} | null = null

onMounted(async () => {
  try {
    const data = await getModels()
    modelList.value = data.models
    form.value.modelName = data.default
  } catch {
    ElMessage.error('获取模型列表失败')
  }
})

// 生成
async function handleGenerate() {
  if (!canGenerate.value) return

  loading.value = true
  const genCount = form.value.count

  // 初始化 loading 卡片
  cards.value = Array.from({ length: genCount }, () => ({
    imageBase64: '',
    status: 'loading' as const,
    promptUsed: '',
  }))
  totalCost.value = 0
  modelUsed.value = ''

  try {
    const images = [...refImages.value]
    lastGenParams = {
      images,
      description: form.value.description,
      aspectRatio: form.value.aspectRatio,
      modelName: form.value.modelName,
    }

    const data = await generateImage({
      task_type: 'quick',
      images: images.length > 0 ? images : undefined,
      description: form.value.description,
      model_name: form.value.modelName,
      aspect_ratio: form.value.aspectRatio,
      count: genCount,
    })

    cards.value = data.images.map((img) => ({
      imageBase64: img,
      status: 'success' as const,
      promptUsed: data.prompt_used,
    }))
    modelUsed.value = data.model_used
    totalCost.value = data.cost
    currency.value = data.currency ?? '¥'
    ElMessage.success('生成完成')
  } catch (e: unknown) {
    const msg = getErrorMessage(e, '生成失败，请稍后重试')
    cards.value = cards.value.map(c => ({ ...c, status: 'failed' as const, error: msg }))
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}

// 单张重试
async function handleRetry(index: number) {
  if (!lastGenParams) return

  cards.value[index] = { ...cards.value[index], status: 'loading', error: undefined }

  try {
    const data = await generateImage({
      task_type: 'quick',
      images: lastGenParams.images.length > 0 ? lastGenParams.images : undefined,
      description: lastGenParams.description,
      model_name: lastGenParams.modelName,
      aspect_ratio: lastGenParams.aspectRatio,
      count: 1,
    })

    if (data.images.length > 0) {
      cards.value[index] = {
        imageBase64: data.images[0],
        status: 'success',
        promptUsed: data.prompt_used,
      }
      totalCost.value += data.cost
      currency.value = data.currency ?? '¥'
      ElMessage.success(`#${index + 1} 重新生成完成`)
    }
  } catch (e: unknown) {
    const msg = getErrorMessage(e, '重试失败')
    cards.value[index] = { ...cards.value[index], status: 'failed', error: msg }
    ElMessage.error(msg)
  }
}

// 编辑 Prompt 重试（用户修改描述后重试单张）
async function handleRetryWithPrompt(_index: number, extraPrompt: string) {
  if (!lastGenParams) return

  // quick 模式：extraPrompt 作为新的描述
  const newDesc = extraPrompt || lastGenParams.description
  cards.value[_index] = { ...cards.value[_index], status: 'loading', error: undefined }

  try {
    const data = await generateImage({
      task_type: 'quick',
      images: lastGenParams.images.length > 0 ? lastGenParams.images : undefined,
      description: newDesc,
      model_name: lastGenParams.modelName,
      aspect_ratio: lastGenParams.aspectRatio,
      count: 1,
    })

    if (data.images.length > 0) {
      cards.value[_index] = {
        imageBase64: data.images[0],
        status: 'success',
        promptUsed: data.prompt_used,
      }
      totalCost.value += data.cost
      currency.value = data.currency ?? '¥'
      ElMessage.success(`#${_index + 1} 重新生成完成`)
    }
  } catch (e: unknown) {
    const msg = getErrorMessage(e, '重试失败')
    cards.value[_index] = { ...cards.value[_index], status: 'failed', error: msg }
    ElMessage.error(msg)
  }
}

// 换模型对比
async function handleCompareModel(cardIndex: number, newModel: string) {
  if (!lastGenParams) return

  const sourcePrompt = cards.value[cardIndex].promptUsed
  const startIdx = cards.value.length
  cards.value.push({
    imageBase64: '',
    status: 'loading',
    promptUsed: sourcePrompt,
  })

  try {
    const data = await generateImage({
      task_type: 'quick',
      images: lastGenParams.images.length > 0 ? lastGenParams.images : undefined,
      description: lastGenParams.description,
      model_name: newModel,
      aspect_ratio: lastGenParams.aspectRatio,
      count: 1,
    })

    for (let i = 0; i < data.images.length; i++) {
      if (startIdx + i < cards.value.length) {
        cards.value[startIdx + i] = {
          imageBase64: data.images[i],
          status: 'success',
          promptUsed: data.prompt_used,
        }
      } else {
        cards.value.push({
          imageBase64: data.images[i],
          status: 'success',
          promptUsed: data.prompt_used,
        })
      }
    }
    totalCost.value += data.cost
    currency.value = data.currency ?? '¥'
  } catch (e: unknown) {
    cards.value[startIdx] = {
      ...cards.value[startIdx],
      status: 'failed',
      error: getErrorMessage(e),
    }
  }
}

// 删除卡片
function handleRemove(index: number) {
  cards.value.splice(index, 1)
}
</script>

<style scoped>
.quick-gen {
  max-width: 1200px;
}

.main-content {
  margin-top: 20px;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.page-header .section-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
}

.page-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.page-sub {
  margin: 2px 0 0;
  font-size: 12px;
  color: var(--text-secondary);
}

/* 参考图上传区 */
.ref-images-area {
  width: 100%;
}

.ref-thumbnails {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  align-items: flex-start;
}

.ref-thumb {
  width: 90px;
  height: 90px;
}

.ref-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.ref-add-btn :deep(.el-upload) {
  width: 90px;
  height: 90px;
}

.add-slot {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  color: var(--text-secondary);
  font-size: 12px;
}

.ref-hint {
  margin-top: 10px;
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.5;
  padding: 8px 12px;
  background: rgba(64, 158, 255, 0.04);
  border-radius: 6px;
  border-left: 3px solid #409eff;
}
</style>
