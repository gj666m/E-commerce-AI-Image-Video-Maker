<template>
  <div class="outfit-gen">
    <el-row :gutter="24" class="main-content">
      <!-- 左侧：参数选择 -->
      <el-col :span="12">
        <el-card>
          <!-- 模式切换 -->
          <el-tabs v-model="mode" class="mode-tabs">
            <el-tab-pane name="single">
              <template #label><span>商品图直出</span></template>
            </el-tab-pane>
            <el-tab-pane name="model">
              <template #label><span>模特+商品</span></template>
            </el-tab-pane>
          </el-tabs>

          <el-form label-position="top">
            <!-- 商品图上传（多图） -->
            <el-form-item required>
              <template #label>
                <div class="section-title">
                  <span class="section-icon gradient-blue"><el-icon><Upload /></el-icon></span>
                  商品/服装图
                </div>
              </template>
              <div class="product-images-area">
                <div class="product-thumbnails">
                  <div v-for="(preview, idx) in productPreviews" :key="idx" class="product-thumb thumb-item">
                    <img :src="preview" />
                    <span class="thumb-remove" @click="removeProductImage(idx)"><el-icon :size="12"><Close /></el-icon></span>
                  </div>
                  <el-upload
                    v-if="productImages.length < 6"
                    :auto-upload="false"
                    :show-file-list="false"
                    :on-change="handleProductImage"
                    accept=".jpg,.jpeg,.png,.webp"
                    class="product-add-btn upload-add-btn"
                  >
                    <div class="add-slot">
                      <el-icon :size="24" color="#409eff"><Plus /></el-icon>
                      <span>{{ productImages.length === 0 ? '上传服装图' : '添加更多' }}</span>
                    </div>
                  </el-upload>
                </div>
                <div class="product-hint">支持 1-6 张多角度商品图，帮助 AI 更好还原服装细节</div>
              </div>
            </el-form-item>

            <!-- 商品信息（结构化，可 AI 分析） -->
            <ProductInfoForm v-model="productInfo" :image="productImages[0] || null" />

            <!-- 模特选择（模特+商品模式） -->
            <el-form-item v-if="mode === 'model'" label="选择模特">
              <el-button type="primary" text size="small" @click="showModelLib = true">
                {{ selectedModel ? `已选: ${selectedModel.name}` : '从模特库选择' }}
              </el-button>
              <div v-if="selectedModelThumb" class="selected-model-thumb">
                <img :src="`/model-files/${selectedModelThumb}`" alt="已选模特" />
              </div>
            </el-form-item>

            <!-- 模特偏好（商品图直出模式） -->
            <template v-if="mode === 'single'">
              <el-row :gutter="12">
                <el-col :span="12">
                  <el-form-item label="模特性别">
                    <el-radio-group v-model="form.modelGender">
                      <el-radio-button value="female">女性</el-radio-button>
                      <el-radio-button value="male">男性</el-radio-button>
                    </el-radio-group>
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="模特人种">
                    <el-select v-model="form.modelEthnicity">
                      <el-option label="欧美" value="caucasian" />
                      <el-option label="亚裔" value="asian" />
                      <el-option label="非裔" value="african" />
                      <el-option label="拉丁" value="latino" />
                    </el-select>
                  </el-form-item>
                </el-col>
              </el-row>
            </template>

            <!-- 场景描述 -->
            <el-form-item>
              <template #label>
                <div class="section-title">
                  <span class="section-icon gradient-green"><el-icon><EditPen /></el-icon></span>
                  场景描述（可选）
                </div>
              </template>
              <div class="preset-tags">
                <el-tag
                  v-for="tag in scenePresets" :key="tag"
                  size="small"
                  effect="plain"
                  class="preset-tag"
                  @click="form.description = tag"
                >{{ tag }}</el-tag>
              </div>
              <div class="description-row">
                <el-input
                  v-model="form.description"
                  type="textarea"
                  :rows="2"
                  placeholder="描述想要的场景效果，如「海边日落」「城市街拍」"
                  style="flex: 1"
                />
                <el-button
                  type="success"
                  plain
                  :loading="optimizing"
                  :disabled="productImages.length === 0"
                  @click="optimizeDescription"
                  style="align-self: flex-start;"
                >
                  <el-icon style="margin-right: 4px"><MagicStick /></el-icon>
                  AI 优化
                </el-button>
              </div>
            </el-form-item>

            <!-- 风格 + 比例 -->
            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="风格">
                  <el-select v-model="form.style" placeholder="选择风格" clearable>
                    <el-option label="自然真实风格" value="自然真实风格" />
                    <el-option label="专业电商摄影" value="专业电商摄影" />
                    <el-option label="时尚杂志风" value="时尚杂志风格" />
                    <el-option label="街头摄影" value="街头摄影风格" />
                    <el-option label="生活化场景" value="生活化场景" />
                  </el-select>
                </el-form-item>
              </el-col>
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
            </el-row>

            <!-- 模型选择 -->
            <el-form-item label="模型">
              <ModelSelector v-model="form.modelName" :models="modelList" />
            </el-form-item>

            <!-- 生成数量 + 按钮 -->
            <el-form-item>
              <el-row :gutter="12" align="middle">
                <el-col :span="8">
                  <el-select v-model="form.count">
                    <el-option :value="1" label="生成 1 张" />
                    <el-option :value="2" label="生成 2 张" />
                    <el-option :value="3" label="生成 3 张" />
                    <el-option :value="4" label="生成 4 张" />
                  </el-select>
                </el-col>
                <el-col :span="16">
                  <el-button
                    type="primary"
                    size="large"
                    :loading="loading"
                    :disabled="!canGenerate"
                    @click="handleGenerate"
                    style="width: 100%"
                  >
                    <el-icon v-if="!loading" style="margin-right: 6px"><Promotion /></el-icon>
                    {{ loading ? '生成中...' : '生成穿搭展示图' }}
                  </el-button>
                </el-col>
              </el-row>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <!-- 右侧：结果区 -->
      <el-col :span="12">
        <el-card v-if="cards.length === 0">
          <el-empty description="上传商品图后点击生成" />
        </el-card>

        <el-card v-else>
          <ResultCardManager
            :cards="cards"
            :model-used="modelUsed"
            :total-cost="totalCost"
            @retry="handleRetry"
            @retry-with-prompt="handleRetryWithPrompt"
            @remove="handleRemove"
          />
        </el-card>
      </el-col>
    </el-row>

    <!-- 模特库弹窗 -->
    <el-dialog v-model="showModelLib" title="从模特库选择" width="600px">
      <ModelLibrary :selected-id="selectedModel?.id || null" @select="handleModelSelect" />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Close, Upload, EditPen, MagicStick, Promotion } from '@element-plus/icons-vue'
import type { UploadFile } from 'element-plus'
import ModelSelector from '../components/ModelSelector.vue'
import ResultCardManager from '../components/ResultCardManager.vue'
import ModelLibrary from '../components/ModelLibrary.vue'
import ProductInfoForm from '../components/ProductInfoForm.vue'
import { generateImage, getModels, analyzeFree } from '../api'
import type { ModelInfo, ModelItem, ResultCard } from '../types'

const mode = ref<'single' | 'model'>('single')
const loading = ref(false)
const modelList = ref<ModelInfo[]>([])

// 结果卡片
const cards = ref<ResultCard[]>([])
const modelUsed = ref('')
const totalCost = ref(0)

// 商品图（支持多张）
const productImages = ref<File[]>([])
const productPreviews = ref<string[]>([])

// 商品信息（自由文本）
const productInfo = ref('')
// 模特库
const showModelLib = ref(false)
const selectedModel = ref<ModelItem | null>(null)
const selectedModelFile = ref<File | null>(null)

const form = ref({
  description: '',
  style: '自然真实风格',
  aspectRatio: '9:16',
  modelName: 'volcengine',
  count: 1,
  modelGender: 'female',
  modelEthnicity: 'caucasian',
})

// 场景预设
const scenePresets = [
  '海边日落，金色沙滩',
  '城市街拍，现代建筑背景',
  '纯白影棚，专业电商',
  '欧洲复古街道，自然光线',
  '花园草地，清新自然',
  '咖啡店窗边，温暖氛围',
]

// 检查商品信息是否有实质内容
function hasProductInfo(): boolean {
  return productInfo.value.trim().length > 0
}

const canGenerate = computed(() => {
  if (productImages.value.length === 0) return false
  if (mode.value === 'model' && !selectedModelFile.value) return false
  return true
})

// AI 优化场景描述
const optimizing = ref(false)

async function optimizeDescription() {
  const img = productImages.value[0]
  if (!img) {
    ElMessage.warning('请先上传商品图')
    return
  }
  optimizing.value = true
  try {
    const existingDesc = form.value.description || ''
    const prompt = existingDesc
      ? `请根据这张商品图，优化以下穿搭场景描述，使其更生动具体（不超过100字）：\n${existingDesc}`
      : '请根据这张商品图，生成一段穿搭场景描述（中文），包含场景、光线、氛围。简洁精准，不超过100字。直接输出描述文本，不要输出其他内容。'
    const resp = await analyzeFree(img, prompt)
    if (resp.text) {
      form.value.description = resp.text
    }
    ElMessage.success('场景描述已优化')
  } catch {
    ElMessage.error('AI 优化失败，请手动填写')
  } finally {
    optimizing.value = false
  }
}

// 上一次生成参数（用于重试）
let lastGenParams: {
  mode: 'single' | 'model'
  images: File[]
  description: string
  style: string
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

// 商品图处理
function handleProductImage(uploadFile: UploadFile) {
  const file = uploadFile.raw
  if (!file) return
  if (productImages.value.length >= 6) {
    ElMessage.warning('最多上传 6 张商品图')
    return
  }
  productImages.value.push(file)
  productPreviews.value.push(URL.createObjectURL(file))
}

function removeProductImage(index: number) {
  productImages.value.splice(index, 1)
  productPreviews.value.splice(index, 1)
}

// 模特选择
async function handleModelSelect(model: ModelItem) {
  try {
    const resp = await fetch(`/model-files/${model.file}`)
    const blob = await resp.blob()
    const file = new File([blob], `${model.name}.jpeg`, { type: 'image/jpeg' })
    selectedModel.value = model
    selectedModelFile.value = file
    showModelLib.value = false
    ElMessage.success(`已选择模特: ${model.name}`)
  } catch {
    ElMessage.error('加载模特图失败')
  }
}

const selectedModelThumb = computed(() => selectedModel.value?.thumbnail || null)

// 构建描述
function buildSingleDesc(): string {
  const genderMap: Record<string, string> = { female: '女性', male: '男性' }
  const ethMap: Record<string, string> = { caucasian: '欧美', asian: '亚裔', african: '非裔', latino: '拉丁' }
  const n = productImages.value.length
  let desc = ''
  if (n > 1) {
    desc = `参考图1至图${n}为同一服装的不同角度照片，`
  } else {
    desc = '参考图中的服装，'
  }
  desc += `${ethMap[form.value.modelEthnicity] || ''}${genderMap[form.value.modelGender] || ''}模特穿着该服装自然展示`
  if (form.value.description) {
    desc += `，${form.value.description}`
  }
  return desc
}

function buildModelDesc(): string {
  const n = productImages.value.length
  let desc = '图1为模特'
  if (n > 1) {
    desc += `，图2至图${n + 1}为同一服装的不同角度照片`
  } else {
    desc += '，图2为服装'
  }
  desc += '，模特穿着该服装自然展示'
  if (form.value.description) {
    desc += `，${form.value.description}`
  }
  return desc
}

// 生成
async function handleGenerate() {
  if (!canGenerate.value) return

  loading.value = true
  const genCount = form.value.count

  // 初始化 loading 卡片
  const newCards: ResultCard[] = Array.from({ length: genCount }, () => ({
    imageBase64: '',
    status: 'loading' as const,
    promptUsed: '',
  }))
  cards.value = newCards
  totalCost.value = 0
  modelUsed.value = ''

  try {
    const images = buildImages()
    const desc = mode.value === 'single' ? buildSingleDesc() : buildModelDesc()

    // 存储参数用于重试
    lastGenParams = {
      mode: mode.value,
      images: [...images],
      description: desc,
      style: form.value.style,
      aspectRatio: form.value.aspectRatio,
      modelName: form.value.modelName,
    }

    const data = await generateImage({
      task_type: 'outfit',
      images,
      description: desc,
      style: form.value.style || undefined,
      model_name: form.value.modelName,
      aspect_ratio: form.value.aspectRatio,
      count: genCount,
      product_info: hasProductInfo() ? productInfo.value : undefined,
    })

    // 更新卡片
    cards.value = data.images.map((img) => ({
      imageBase64: img,
      status: 'success' as const,
      promptUsed: data.prompt_used,
    }))
    modelUsed.value = data.model_used
    totalCost.value = data.cost
    ElMessage.success('生成完成')
  } catch (e: any) {
    const msg = e?.response?.data?.detail || '生成失败，请稍后重试'
    cards.value = cards.value.map(c => ({ ...c, status: 'failed' as const, error: msg }))
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}

function buildImages(): File[] {
  if (mode.value === 'model' && selectedModelFile.value) {
    return [selectedModelFile.value, ...productImages.value]
  }
  return [...productImages.value]
}

// 单张重试
async function handleRetry(index: number) {
  if (!lastGenParams) return

  const card = cards.value[index]
  cards.value[index] = { ...card, status: 'loading', error: undefined }

  try {
    const data = await generateImage({
      task_type: 'outfit',
      images: lastGenParams.images,
      description: lastGenParams.description,
      style: lastGenParams.style || undefined,
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
      ElMessage.success(`#${index + 1} 重新生成完成`)
    }
  } catch (e: any) {
    const msg = e?.response?.data?.detail || '重试失败'
    cards.value[index] = { ...cards.value[index], status: 'failed', error: msg }
    ElMessage.error(msg)
  }
}

// 编辑 Prompt 重试
async function handleRetryWithPrompt(index: number, extraPrompt: string) {
  if (!lastGenParams) return

  const card = cards.value[index]
  cards.value[index] = { ...card, status: 'loading', error: undefined }

  try {
    const data = await generateImage({
      task_type: 'outfit',
      images: lastGenParams.images,
      description: lastGenParams.description,
      style: lastGenParams.style || undefined,
      model_name: lastGenParams.modelName,
      aspect_ratio: lastGenParams.aspectRatio,
      custom_prompt: extraPrompt || undefined,
      count: 1,
    })

    if (data.images.length > 0) {
      cards.value[index] = {
        imageBase64: data.images[0],
        status: 'success',
        promptUsed: data.prompt_used,
      }
      totalCost.value += data.cost
      ElMessage.success(`#${index + 1} 重新生成完成`)
    }
  } catch (e: any) {
    const msg = e?.response?.data?.detail || '重试失败'
    cards.value[index] = { ...cards.value[index], status: 'failed', error: msg }
    ElMessage.error(msg)
  }
}

// 删除卡片
function handleRemove(index: number) {
  cards.value.splice(index, 1)
}
</script>

<style scoped>
.outfit-gen {
  max-width: 1200px;
}

.main-content {
  margin-top: 20px;
}

.mode-tabs {
  margin-bottom: 16px;
}

/* 商品图上传区 */
.product-images-area {
  width: 100%;
}

.product-thumbnails {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  align-items: flex-start;
}

.product-thumb {
  width: 90px;
  height: 90px;
}

.product-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.product-add-btn :deep(.el-upload) {
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

.product-hint {
  margin-top: 10px;
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.5;
  padding: 8px 12px;
  background: rgba(64, 158, 255, 0.04);
  border-radius: 6px;
  border-left: 3px solid #409eff;
}

/* 模特缩略图 */
.selected-model-thumb img {
  width: 64px;
  height: 64px;
  object-fit: cover;
  border-radius: 10px;
  margin-top: 6px;
  border: 2px solid var(--border-color);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}
</style>
