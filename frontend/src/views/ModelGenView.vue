<template>
  <div class="model-gen">
    <el-row :gutter="20" class="main-content">
      <!-- 左侧：参数选择 -->
      <el-col :span="12">
        <el-card>
          <!-- 模式切换 -->
          <el-tabs v-model="mode" class="mode-tabs">
            <el-tab-pane label="文生图" name="text" />
            <el-tab-pane label="参考图变体" name="image" />
          </el-tabs>

          <!-- 参考图上传（多图） -->
          <el-form-item v-if="mode === 'image'" label="参考图片">
            <div class="ref-images-area">
              <div class="ref-thumbnails">
                <div v-for="(preview, idx) in refPreviews" :key="idx" class="ref-thumb thumb-item">
                  <img :src="preview" />
                  <span class="thumb-remove" @click="removeRefImage(idx)"><el-icon :size="12"><Close /></el-icon></span>
                </div>
                <el-upload
                  v-if="refImages.length < 3"
                  :auto-upload="false"
                  :show-file-list="false"
                  :on-change="handleRefImage"
                  accept=".jpg,.jpeg,.png,.webp"
                  class="ref-add-btn upload-add-btn"
                >
                  <div class="add-slot">
                    <el-icon :size="24" color="#e6a23c"><Plus /></el-icon>
                    <span>{{ refImages.length === 0 ? '上传参考图' : '添加更多' }}</span>
                  </div>
                </el-upload>
              </div>
              <div class="ref-hint">支持 1-3 张参考图，帮助 AI 更准确还原面部特征</div>
            </div>
          </el-form-item>

          <!-- 商品信息（参考图模式下可 AI 分析） -->
          <ProductInfoForm v-if="mode === 'image'" v-model="productInfo" :image="refImages[0] || null" />

          <el-form label-position="top">
            <!-- 核心参数：性别 + 人种 -->
            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="性别">
                  <el-radio-group v-model="form.gender">
                    <el-radio-button value="female">女性</el-radio-button>
                    <el-radio-button value="male">男性</el-radio-button>
                  </el-radio-group>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="人种">
                  <el-select v-model="form.ethnicity">
                    <el-option label="欧美" value="caucasian" />
                    <el-option label="亚裔" value="asian" />
                    <el-option label="非裔" value="african" />
                    <el-option label="拉丁" value="latino" />
                  </el-select>
                </el-form-item>
              </el-col>
            </el-row>

            <!-- 年龄 + 体型 -->
            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="年龄段">
                  <el-select v-model="form.age">
                    <el-option label="20-25" value="20-25" />
                    <el-option label="25-30（默认）" value="25-30" />
                    <el-option label="30-35" value="30-35" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="体型">
                  <el-select v-model="form.bodyType">
                    <el-option label="纤瘦" value="slim" />
                    <el-option label="标准（默认）" value="standard" />
                    <el-option label="健美" value="athletic" />
                  </el-select>
                </el-form-item>
              </el-col>
            </el-row>

            <el-divider />

            <!-- 灵活参数：标签 + 自由文本 -->
            <el-form-item label="发型">
              <div class="tag-input-row">
                <el-tag
                  v-for="h in hairPresets" :key="h"
                  :type="form.hairDesc === h ? '' : 'info'"
                  class="preset-tag"
                  @click="form.hairDesc = h"
                >{{ h }}</el-tag>
                <el-input v-model="form.hairDesc" placeholder="或输入自定义..." size="small" clearable class="tag-input" />
              </div>
            </el-form-item>

            <el-form-item label="表情">
              <div class="tag-input-row">
                <el-tag
                  v-for="e in expressionPresets" :key="e"
                  :type="form.expression === e ? '' : 'info'"
                  class="preset-tag"
                  @click="form.expression = e"
                >{{ e }}</el-tag>
                <el-input v-model="form.expression" placeholder="或输入自定义..." size="small" clearable class="tag-input" />
              </div>
            </el-form-item>

            <el-form-item label="姿势">
              <div class="tag-input-row">
                <el-tag
                  v-for="p in posePresets" :key="p"
                  :type="form.pose === p ? '' : 'info'"
                  class="preset-tag"
                  @click="form.pose = p"
                >{{ p }}</el-tag>
                <el-input v-model="form.pose" placeholder="或输入自定义..." size="small" clearable class="tag-input" />
              </div>
            </el-form-item>

            <el-form-item label="服装">
              <div class="tag-input-row">
                <el-tag
                  v-for="c in clothingPresets" :key="c"
                  :type="form.clothing === c ? '' : 'info'"
                  class="preset-tag"
                  @click="form.clothing = c"
                >{{ c }}</el-tag>
                <el-input v-model="form.clothing" placeholder="或输入自定义..." size="small" clearable class="tag-input" />
              </div>
            </el-form-item>

            <el-divider />

            <!-- 场景参数 -->
            <el-row :gutter="12">
              <el-col :span="6">
                <el-form-item label="背景">
                  <el-select v-model="form.background">
                    <el-option label="纯白" value="white" />
                    <el-option label="浅灰" value="light_gray" />
                    <el-option label="户外" value="outdoor" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="6">
                <el-form-item label="构图">
                  <el-radio-group v-model="form.composition">
                    <el-radio-button value="full_body">全身</el-radio-button>
                    <el-radio-button value="half_body">半身</el-radio-button>
                  </el-radio-group>
                </el-form-item>
              </el-col>
              <el-col :span="6">
                <el-form-item label="风格">
                  <el-select v-model="form.style">
                    <el-option label="电商" value="ecommerce" />
                    <el-option label="杂志" value="fashion" />
                    <el-option label="休闲" value="casual" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="6">
                <el-form-item label="比例">
                  <el-select v-model="form.aspectRatio">
                    <el-option label="1:1" value="1:1" />
                    <el-option label="3:4" value="3:4" />
                    <el-option label="4:3" value="4:3" />
                    <el-option label="9:16" value="9:16" />
                    <el-option label="16:9" value="16:9" />
                  </el-select>
                </el-form-item>
              </el-col>
            </el-row>

            <!-- 额外描述 -->
            <el-form-item>
              <template #label>
                <span>额外描述</span>
              </template>
              <div class="description-row">
                <el-input
                  v-model="form.customDesc"
                  type="textarea"
                  :rows="2"
                  placeholder="任何补充要求，如「戴墨镜」「手拿咖啡杯」「背景加逆光效果」"
                  style="flex: 1"
                />
                <el-button
                  v-if="mode === 'image'"
                  type="success"
                  plain
                  :loading="optimizing"
                  :disabled="refImages.length === 0"
                  @click="optimizeDescription"
                  style="align-self: flex-start;"
                >
                  <el-icon style="margin-right: 4px"><MagicStick /></el-icon>
                  AI 优化
                </el-button>
              </div>
            </el-form-item>

            <!-- 生成按钮 -->
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
                    :disabled="mode === 'image' && refImages.length === 0"
                    @click="handleGenerate"
                    style="width: 100%"
                  >
                    <el-icon v-if="!loading" style="margin-right: 6px"><Promotion /></el-icon>
                    {{ loading ? '生成中...' : (mode === 'image' ? '生成变体' : '生成模特') }}
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
          <el-empty :description="mode === 'image' ? '上传参考图后点击生成变体' : '选择参数后点击「生成模特」'" />
        </el-card>

        <el-card v-else>
          <ResultCardManager
            :cards="cards"
            :model-used="modelUsed"
            :total-cost="totalCost"
            :currency="currency"
            :show-save-model="true"
            :models="modelList"
            @retry="handleRetry"
            @retry-with-prompt="handleRetryWithPrompt"
            @remove="handleRemove"
            @save-model="handleSaveModel"
            @compare-model="handleCompareModel"
          />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Close, MagicStick, Promotion } from '@element-plus/icons-vue'
import ResultCardManager from '../components/ResultCardManager.vue'
import ProductInfoForm from '../components/ProductInfoForm.vue'
import { generateModel, saveModel, analyzeFree, getModels, getErrorMessage } from '../api'
import type { ResultCard, ModelInfo } from '../types'
import { useImageList } from '../composables/useImageList'

const mode = ref<'text' | 'image'>('text')
const loading = ref(false)
const modelList = ref<ModelInfo[]>([])

// 获取可用模型列表
onMounted(async () => {
  try {
    const data = await getModels()
    modelList.value = data.models
  } catch {
    // 静默失败，不影响主流程
  }
})

// 结果卡片
const cards = ref<ResultCard[]>([])
const modelUsed = ref('')
const totalCost = ref(0)
const currency = ref('¥')

// 参考图（多张）
const { files: refImages, previews: refPreviews, add: handleRefImage, remove: removeRefImage } = useImageList(3, '参考图')

// 商品信息（自由文本）
const productInfo = ref('')
// 预设标签
const hairPresets = ['金色长直发', '黑色长卷发', '利落短发', '高马尾', '棕色波浪卷']
const expressionPresets = ['微笑', '自然', '冷酷', '俏皮', '优雅']
const posePresets = ['自然站立', '行走中', '坐姿', '叉腰', '转身回望']
const clothingPresets = ['白T恤+牛仔裤', '白色连衣裙', '黑色西装', '运动装']

const form = ref({
  gender: 'female',
  ethnicity: 'caucasian',
  age: '25-30',
  bodyType: 'standard',
  hairDesc: '',
  expression: '',
  pose: '',
  clothing: '',
  background: 'white',
  composition: 'full_body',
  style: 'ecommerce',
  customDesc: '',
  count: 1,
  aspectRatio: '1:1',
})

// 上一次生成参数（用于重试）
let lastGenParams: {
  formValues: typeof form.value
  refImages: File[]
  mode: 'text' | 'image'
} | null = null

// AI 优化额外描述
const optimizing = ref(false)

async function optimizeDescription() {
  const img = refImages.value[0]
  if (!img) {
    ElMessage.warning('请先上传参考图')
    return
  }
  optimizing.value = true
  try {
    const existingDesc = form.value.customDesc || ''
    const prompt = existingDesc
      ? `请根据这张参考照片，优化以下模特描述，使其更精准（不超过80字）：\n${existingDesc}`
      : '请根据这张参考照片，生成一段补充描述（中文），帮助AI更好地还原或调整这个模特形象。简洁精准，不超过80字。直接输出描述文本，不要输出其他内容。'
    const resp = await analyzeFree(img, prompt)
    if (resp.text) {
      form.value.customDesc = resp.text
    }
    ElMessage.success('描述已优化')
  } catch {
    ElMessage.error('AI 优化失败，请手动填写')
  } finally {
    optimizing.value = false
  }
}

// 生成
async function handleGenerate() {
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

  // 存储参数用于重试
  lastGenParams = {
    formValues: { ...form.value },
    refImages: [...refImages.value],
    mode: mode.value,
  }

  try {
    const data = await generateModel(
      {
        gender: form.value.gender,
        ethnicity: form.value.ethnicity,
        age: form.value.age,
        body_type: form.value.bodyType,
        hair_desc: form.value.hairDesc || undefined,
        expression: form.value.expression || undefined,
        pose: form.value.pose || undefined,
        clothing: form.value.clothing || undefined,
        background: form.value.background,
        composition: form.value.composition,
        style: form.value.style,
        custom_desc: form.value.customDesc || undefined,
        count: genCount,
        aspect_ratio: form.value.aspectRatio,
      },
      mode.value === 'image' ? refImages.value : undefined,
    )

    cards.value = data.images.map((img: string) => ({
      imageBase64: img,
      status: 'success' as const,
      promptUsed: data.prompt_used,
    }))
    modelUsed.value = data.model_used
    totalCost.value = data.cost
    currency.value = data.currency ?? '¥'
    ElMessage.success(`生成完成，共 ${data.images.length} 张`)
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
    const p = lastGenParams
    const data = await generateModel(
      {
        gender: p.formValues.gender,
        ethnicity: p.formValues.ethnicity,
        age: p.formValues.age,
        body_type: p.formValues.bodyType,
        hair_desc: p.formValues.hairDesc || undefined,
        expression: p.formValues.expression || undefined,
        pose: p.formValues.pose || undefined,
        clothing: p.formValues.clothing || undefined,
        background: p.formValues.background,
        composition: p.formValues.composition,
        style: p.formValues.style,
        custom_desc: p.formValues.customDesc || undefined,
        count: 1,
        aspect_ratio: p.formValues.aspectRatio,
      },
      p.mode === 'image' ? p.refImages : undefined,
    )

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

// 编辑 Prompt 重试
async function handleRetryWithPrompt(index: number, extraPrompt: string) {
  if (!lastGenParams) return

  cards.value[index] = { ...cards.value[index], status: 'loading', error: undefined }

  try {
    const p = lastGenParams
    const data = await generateModel(
      {
        gender: p.formValues.gender,
        ethnicity: p.formValues.ethnicity,
        age: p.formValues.age,
        body_type: p.formValues.bodyType,
        hair_desc: p.formValues.hairDesc || undefined,
        expression: p.formValues.expression || undefined,
        pose: p.formValues.pose || undefined,
        clothing: p.formValues.clothing || undefined,
        background: p.formValues.background,
        composition: p.formValues.composition,
        style: p.formValues.style,
        custom_desc: extraPrompt ? `${p.formValues.customDesc || ''} ${extraPrompt}`.trim() : undefined,
        count: 1,
        aspect_ratio: p.formValues.aspectRatio,
      },
      p.mode === 'image' ? p.refImages : undefined,
    )

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
    const p = lastGenParams
    const data = await generateModel(
      {
        gender: p.formValues.gender,
        ethnicity: p.formValues.ethnicity,
        age: p.formValues.age,
        body_type: p.formValues.bodyType,
        hair_desc: p.formValues.hairDesc || undefined,
        expression: p.formValues.expression || undefined,
        pose: p.formValues.pose || undefined,
        clothing: p.formValues.clothing || undefined,
        background: p.formValues.background,
        composition: p.formValues.composition,
        style: p.formValues.style,
        custom_desc: p.formValues.customDesc || undefined,
        count: 1,
        aspect_ratio: p.formValues.aspectRatio,
        model_name: newModel,
      },
      p.mode === 'image' ? p.refImages : undefined,
    )

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

// 保存到模特库
async function handleSaveModel(index: number) {
  const card = cards.value[index]
  if (card.status !== 'success') return

  try {
    const name = buildName()
    await saveModel({
      name,
      params: { ...form.value, count: String(form.value.count), mode: mode.value },
      image_data: card.imageBase64,
    })
    ElMessage.success(`已保存「${name}」到模特库`)
  } catch (e: unknown) {
    const msg = getErrorMessage(e, '保存失败')
    ElMessage.error(msg)
  }
}

function buildName(): string {
  const genderMap: Record<string, string> = { female: '女', male: '男' }
  const ethMap: Record<string, string> = { caucasian: '欧美', asian: '亚裔', african: '非裔', latino: '拉丁' }
  const base = `${ethMap[form.value.ethnicity] || ''}${genderMap[form.value.gender] || ''}`
  const detail = form.value.hairDesc || form.value.expression || ''
  return detail ? `${base}-${detail}` : base
}
</script>

<style scoped>
.model-gen {
  max-width: 1200px;
}

.main-content {
  margin-top: 20px;
}

.mode-tabs {
  margin-bottom: 16px;
}

/* 参考图多图上传 */
.ref-images-area {
  width: 100%;
}

.ref-thumbnails {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: flex-start;
}

.ref-thumb {
  position: relative;
  width: 84px;
  height: 84px;
  border-radius: 10px;
  overflow: hidden;
  border: 2px solid var(--border-color);
  transition: border-color 0.2s;
}

.ref-thumb:hover {
  border-color: #409eff;
}

.ref-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.thumb-remove {
  position: absolute;
  top: 4px;
  right: 4px;
  background: rgba(0, 0, 0, 0.55);
  color: white;
  border-radius: 50%;
  padding: 2px;
  font-size: 12px;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.2s;
}

.ref-thumb:hover .thumb-remove {
  opacity: 1;
}

.ref-add-btn :deep(.el-upload) {
  width: 84px;
  height: 84px;
  border: 2px dashed var(--border-color);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.25s;
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
  background: rgba(230, 162, 60, 0.06);
  border-radius: 6px;
  border-left: 3px solid #e6a23c;
}

/* 标签输入行 */
.tag-input-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  width: 100%;
}

.preset-tag {
  cursor: pointer;
  transition: all 0.2s;
}

.preset-tag:hover {
  transform: translateY(-1px);
}

.tag-input {
  width: 140px;
  flex-shrink: 0;
}

.description-row {
  display: flex;
  width: 100%;
}
</style>
