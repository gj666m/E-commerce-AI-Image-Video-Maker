<template>
  <div class="seed-grass">
    <div class="page-header">
      <h2 class="page-title">
        种草图
        <el-tooltip content="查看使用说明" placement="top">
          <el-icon class="help-icon" @click="goGuide('seed-grass')"><QuestionFilled /></el-icon>
        </el-tooltip>
      </h2>
      <p class="page-desc">博主人设 + AI 策划方案 + 按方案选择张数批量生成，产出种草风格图</p>
    </div>
    <!-- ====== 正常态：表单视图（手动模式 + AI策划入口） ====== -->
    <div v-if="planPhase === ''" class="main-content">
      <el-row :gutter="20">
        <!-- 左侧：参数选择 -->
        <el-col :span="12">
          <el-card>
            <!-- 模式切换 -->
            <el-tabs v-model="mode" class="mode-tabs">
              <el-tab-pane label="手动配置" name="manual" />
              <el-tab-pane label="AI 策划" name="ai-plan" />
            </el-tabs>

            <el-form label-position="top">
              <!-- 商品图上传（多图） -->
              <el-form-item label="商品/服装图" required>
                <div class="product-images-area">
                  <div class="product-thumbnails">
                    <div v-for="(preview, idx) in productPreviews" :key="idx" class="product-thumb">
                      <img :src="preview" />
                      <el-icon class="thumb-remove" @click="removeProductImage(idx)"><Close /></el-icon>
                    </div>
                    <el-upload
                      v-if="productImages.length < 6"
                      :auto-upload="false"
                      :show-file-list="false"
                      :on-change="handleProductImage"
                      accept=".jpg,.jpeg,.png,.webp"
                      class="product-add-btn"
                    >
                      <div class="add-slot">
                        <el-icon :size="24"><Plus /></el-icon>
                        <span>{{ productImages.length === 0 ? '上传服装图' : '添加更多' }}</span>
                      </div>
                    </el-upload>
                  </div>
                  <div class="product-hint">支持 1-6 张多角度商品图，帮助 AI 更好还原服装细节</div>
                </div>
              </el-form-item>

              <!-- 商品信息 -->
              <ProductInfoForm v-model="productInfo" :image="productImages[0] || null" />

              <!-- 博主人设（通用：手动模式 + AI策划模式共用） -->
              <el-form-item label="博主人设">
                <div class="persona-mode-switch">
                  <el-radio-group v-model="personaMode" size="small">
                    <el-radio-button value="tags">标签组合</el-radio-button>
                    <el-radio-button value="photo">照片驱动</el-radio-button>
                  </el-radio-group>
                </div>

                <!-- 照片驱动模式 -->
                <div v-if="personaMode === 'photo'" class="persona-photo-area">
                  <el-upload
                    :auto-upload="false"
                    :show-file-list="false"
                    :on-change="handlePersonaPhoto"
                    accept=".jpg,.jpeg,.png,.webp"
                    class="persona-photo-upload"
                    drag
                  >
                    <div v-if="!personaPhotoPreview" class="persona-photo-slot">
                      <el-icon :size="32"><Plus /></el-icon>
                      <span>上传博主照片</span>
                      <span class="upload-hint">AI 将自动提取人设特征</span>
                    </div>
                    <div v-else class="persona-photo-preview">
                      <img :src="personaPhotoPreview" />
                      <div class="photo-overlay">
                        <el-icon :size="20"><Refresh /></el-icon>
                        <span>更换照片</span>
                      </div>
                    </div>
                  </el-upload>

                  <!-- 分析结果展示 -->
                  <div v-if="personaResult" class="persona-result">
                    <el-button
                      size="small"
                      :loading="analyzingPersona"
                      @click="handleAnalyzePersona"
                      style="margin-bottom: 8px"
                    >
                      {{ analyzingPersona ? '分析中...' : '重新分析' }}
                    </el-button>

                    <div class="persona-tags-result">
                      <div class="tag-group" v-if="personaResult.style">
                        <span class="tag-label">风格</span>
                        <el-tag size="small" type="primary">{{ personaResult.style }}</el-tag>
                      </div>
                      <div class="tag-group" v-if="personaResult.age_range">
                        <span class="tag-label">年龄</span>
                        <el-tag size="small" type="primary">{{ personaResult.age_range }}</el-tag>
                      </div>
                      <div class="tag-group" v-if="personaResult.vibe">
                        <span class="tag-label">气质</span>
                        <el-tag size="small" type="primary">{{ personaResult.vibe }}</el-tag>
                      </div>
                      <div class="tag-group" v-if="personaResult.color_preference">
                        <span class="tag-label">色系</span>
                        <el-tag size="small" type="primary">{{ personaResult.color_preference }}</el-tag>
                      </div>
                    </div>

                    <div v-if="personaResult.suitable_scenes?.length" class="persona-scenes">
                      <span class="tag-label">适合场景：</span>
                      <el-tag v-for="s in personaResult.suitable_scenes" :key="s" size="small" effect="plain" type="info">{{ s }}</el-tag>
                    </div>

                    <el-input
                      v-model="personaDescEdit"
                      type="textarea"
                      :rows="2"
                      placeholder="AI 提取的人设描述（可编辑微调）"
                      style="margin-top: 8px"
                    />
                  </div>

                  <el-button
                    v-else-if="personaPhotoFile"
                    size="small"
                    type="primary"
                    :loading="analyzingPersona"
                    @click="handleAnalyzePersona"
                    style="margin-top: 8px"
                  >
                    {{ analyzingPersona ? '分析中...' : '开始分析人设' }}
                  </el-button>
                </div>

                <!-- 标签组合模式 -->
                <div v-else class="persona-tags-area">
                  <div class="tag-group">
                    <span class="tag-label">风格</span>
                    <el-check-tag
                      v-for="tag in personaStyleTags" :key="tag"
                      :checked="selectedPersona.style === tag"
                      @change="selectedPersona.style = selectedPersona.style === tag ? '' : tag"
                    >{{ tag }}</el-check-tag>
                  </div>
                  <div class="tag-group">
                    <span class="tag-label">年龄</span>
                    <el-check-tag
                      v-for="tag in personaAgeTags" :key="tag"
                      :checked="selectedPersona.age === tag"
                      @change="selectedPersona.age = selectedPersona.age === tag ? '' : tag"
                    >{{ tag }}</el-check-tag>
                  </div>
                  <div class="tag-group">
                    <span class="tag-label">气质</span>
                    <el-check-tag
                      v-for="tag in personaVibeTags" :key="tag"
                      :checked="selectedPersona.vibe === tag"
                      @change="selectedPersona.vibe = selectedPersona.vibe === tag ? '' : tag"
                    >{{ tag }}</el-check-tag>
                  </div>
                  <el-input
                    v-model="selectedPersona.custom"
                    type="textarea"
                    :rows="2"
                    placeholder="补充人设描述（可选），如：短发、戴眼镜、欧美面孔..."
                    style="margin-top: 8px"
                  />
                </div>
              </el-form-item>

              <!-- ====== 手动模式专属 ====== -->
              <template v-if="mode === 'manual'">
                <!-- 场景选择 -->
                <el-form-item label="场景">
                  <div class="scene-area">
                    <div class="preset-tags">
                      <el-tag
                        v-for="tag in scenePresets" :key="tag.text"
                        size="small"
                        :type="form.scene === tag.text ? '' : 'info'"
                        effect="plain"
                        class="preset-tag"
                        @click="form.scene = form.scene === tag.text ? '' : tag.text"
                      >{{ tag.label }}</el-tag>
                    </div>
                    <el-input
                      v-model="form.scene"
                      type="textarea"
                      :rows="2"
                      placeholder="描述场景，如：咖啡店窗边、花园草地、城市街拍..."
                    />
                  </div>
                </el-form-item>
              </template>

              <!-- ====== AI 策划模式入口 ====== -->
              <template v-if="mode === 'ai-plan'">
                <el-form-item>
                  <el-button
                    type="primary"
                    :loading="planning"
                    :disabled="productImages.length === 0"
                    @click="handleAIPlan"
                  >
                    {{ planning ? '策划中...' : 'AI 策划方案' }}
                  </el-button>
                  <span style="margin-left: 8px; color: #909399; font-size: 12px;">
                    上传商品图后点击，AI 根据人设和商品自动策划方案
                  </span>
                </el-form-item>
              </template>

              <!-- 通用参数 -->
              <el-row :gutter="12">
                <el-col :span="12">
                  <el-form-item label="风格">
                    <el-select v-model="form.style" placeholder="选择风格" clearable>
                      <el-option label="手机随拍风格" value="手机随拍风格，生活化氛围" />
                      <el-option label="自然真实风格" value="自然真实风格" />
                      <el-option label="清新暖调" value="清新暖调，柔和光线" />
                      <el-option label="冷色胶片" value="冷色调胶片质感" />
                      <el-option label="明亮高饱和" value="明亮高饱和度，色彩鲜艳" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="比例">
                    <el-select v-model="form.aspectRatio">
                      <el-option label="1:1 正方形" value="1:1" />
                      <el-option label="3:4 竖版（小红书）" value="3:4" />
                      <el-option label="4:5 竖版（Instagram）" value="4:5" />
                      <el-option label="9:16 竖版（短视频）" value="9:16" />
                    </el-select>
                  </el-form-item>
                </el-col>
              </el-row>

              <!-- 模型选择 -->
              <el-form-item label="模型">
                <ModelSelector v-model="form.modelName" :models="modelList" />
              </el-form-item>

              <!-- 手动模式的生成按钮 -->
              <el-form-item v-if="mode === 'manual'">
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
                      :disabled="!canManualGenerate"
                      @click="handleManualGenerate"
                      style="width: 100%"
                    >
                      {{ loading ? '生成中...' : '生成种草图' }}
                    </el-button>
                  </el-col>
                </el-row>
              </el-form-item>
            </el-form>
          </el-card>
        </el-col>

        <!-- 右侧：手动模式结果区 -->
        <el-col :span="12">
          <el-card v-if="cards.length === 0">
            <el-empty description="上传商品图后点击生成" />
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

    <!-- ====== AI 策划加载态 ====== -->
    <div v-else-if="planPhase === 'loading'" class="plan-loading-view">
      <el-card>
        <div class="plan-loading-content">
          <el-icon class="is-loading" :size="32"><Loading /></el-icon>
          <p class="plan-loading-text">{{ loadingPlanText }}</p>
        </div>
      </el-card>
    </div>

    <!-- ====== AI 策划结果视图（全页切换） ====== -->
    <div v-else-if="planPhase === 'ready'" class="plan-result-view">
      <!-- 顶部操作栏 -->
      <div class="plan-result-header">
        <el-button text @click="backToForm">
          <el-icon><ArrowLeft /></el-icon> 返回修改
        </el-button>
        <span class="plan-result-title">AI 策划结果</span>
        <div style="flex:1" />
        <el-button type="primary" size="large" :loading="generating" :disabled="totalGenCount === 0" @click="handleBatchGenerate">
          {{ generating ? '生成中...' : `一键生成（${totalGenCount} 张）` }}
        </el-button>
      </div>

      <!-- 方案列表（全宽） -->
      <div class="plan-section-label">策划方案（可编辑）</div>
      <div class="plan-scroll-list">
        <el-card v-for="(plan, idx) in planList" :key="idx" class="plan-card" shadow="never">
          <div class="plan-card-top">
            <el-checkbox v-model="planSelected[idx]" class="plan-checkbox">
              <el-tag size="small" type="primary">图{{ idx + 1 }}</el-tag>
              <span class="plan-title">{{ plan.title }}</span>
            </el-checkbox>
            <div class="plan-card-controls">
              <el-select v-model="planCounts[idx]" size="small" style="width: 100px" :disabled="!planSelected[idx]">
                <el-option :value="1" label="1 张" />
                <el-option :value="2" label="2 张" />
                <el-option :value="3" label="3 张" />
                <el-option :value="4" label="4 张" />
              </el-select>
            </div>
          </div>
          <div class="plan-details" v-if="planSelected[idx]">
            <p v-if="plan.scene"><strong>场景：</strong>{{ plan.scene }}</p>
            <p v-if="plan.pose"><strong>姿势：</strong>{{ plan.pose }}</p>
            <p v-if="plan.angle"><strong>角度：</strong>{{ plan.angle }}</p>
            <p v-if="plan.selling_point"><strong>卖点：</strong>{{ plan.selling_point }}</p>
          </div>
          <el-input
            v-if="planSelected[idx]"
            v-model="plan.prompt_hint"
            type="textarea"
            :rows="1"
            placeholder="可编辑 prompt 提示..."
            size="small"
          />
        </el-card>
      </div>

      <!-- 批量生成结果 -->
      <div v-if="planCards.length > 0" class="plan-results-section">
        <el-divider content-position="left">生成结果</el-divider>
        <ResultCardManager
          :cards="planCards"
          :model-used="planModelUsed"
          :total-cost="planTotalCost"
          :currency="planCurrency"
          :models="modelList"
          @retry="handlePlanRetry"
          @retry-with-prompt="handlePlanRetryWithPrompt"
          @remove="handlePlanRemove"
          @compare-model="handlePlanCompareModel"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Plus, Close, Refresh, Loading, ArrowLeft, QuestionFilled } from '@element-plus/icons-vue'
import type { UploadFile } from 'element-plus'
import ModelSelector from '../components/ModelSelector.vue'
import ResultCardManager from '../components/ResultCardManager.vue'
import ProductInfoForm from '../components/ProductInfoForm.vue'
import { generateImage, getModels, analyzePersona, planShots, getErrorMessage } from '../api'
import type { ModelInfo, ResultCard, PersonaAnalysis, ShotPlan } from '../types'
import { useImageList } from '../composables/useImageList'

const mode = ref<'manual' | 'ai-plan'>('manual')
const loading = ref(false)
const planning = ref(false)
const generating = ref(false)
const modelList = ref<ModelInfo[]>([])

const router = useRouter()
function goGuide(anchor: string) {
  router.push({ path: '/user-guide', hash: `#${anchor}` })
}

// ====== 策划视图状态 ======
const planPhase = ref<'' | 'loading' | 'ready'>('')
const loadingPlanText = ref('')
const planList = ref<ShotPlan[]>([])

// 手动模式结果
const cards = ref<ResultCard[]>([])
const modelUsed = ref('')
const totalCost = ref(0)
const currency = ref('¥')

// 策划模式批量生成结果
const planCards = ref<ResultCard[]>([])
const planModelUsed = ref('')
const planTotalCost = ref(0)
const planCurrency = ref('¥')

// 商品图
const { files: productImages, previews: productPreviews, add: handleProductImage, remove: removeProductImage } = useImageList(6, '商品图')
const productInfo = ref('')

// 人设标签
const personaStyleTags = ['极简风', '甜美风', '街头风', '优雅风', '休闲风', '韩系', '法式']
const personaAgeTags = ['20-25岁', '25-30岁', '30-35岁']
const personaVibeTags = ['清新自然', '温柔知性', '活泼元气', '高冷文艺', '阳光亲和']

const selectedPersona = ref({
  style: '',
  age: '',
  vibe: '',
  custom: '',
})

// 人设模式：标签组合 vs 照片驱动
const personaMode = ref<'tags' | 'photo'>('tags')
const personaPhotoFile = ref<File | null>(null)
const personaPhotoPreview = ref('')
const personaResult = ref<PersonaAnalysis | null>(null)
const personaDescEdit = ref('')
const analyzingPersona = ref(false)

// 场景预设
const scenePresets = [
  { label: '咖啡店', text: '咖啡店窗边，温暖午后光线' },
  { label: '花园', text: '花园草地，清新自然，阳光洒落' },
  { label: '街头', text: '城市街拍，现代建筑背景' },
  { label: '海边', text: '海边日落，金色沙滩，海风拂面' },
  { label: '书房', text: '书房一角，温暖台灯，安静阅读' },
  { label: '公园', text: '城市公园，绿荫小径，自然漫步' },
]

const form = ref({
  style: '手机随拍风格，生活化氛围',
  aspectRatio: '9:16',
  modelName: 'volcengine',
  count: 1,
  scene: '',
})

const canManualGenerate = computed(() => {
  return productImages.value.length > 0
})

// 构建人设描述文本
function buildPersonaDesc(): string {
  if (personaMode.value === 'photo' && personaDescEdit.value) {
    return personaDescEdit.value
  }
  const parts: string[] = []
  if (selectedPersona.value.age) parts.push(selectedPersona.value.age)
  parts.push('时尚女性')
  if (selectedPersona.value.style) parts.push(selectedPersona.value.style)
  if (selectedPersona.value.vibe) parts.push(selectedPersona.value.vibe)
  if (selectedPersona.value.custom) parts.push(selectedPersona.value.custom)
  return parts.join('，') || '25岁左右时尚女性，气质清新自然'
}

onMounted(async () => {
  try {
    const data = await getModels()
    modelList.value = data.models
    form.value.modelName = data.default
  } catch {
    ElMessage.error('获取模型列表失败')
  }
})

// 组件卸载时释放博主人设照片 Blob URL
onUnmounted(() => {
  if (personaPhotoPreview.value) URL.revokeObjectURL(personaPhotoPreview.value)
})

// 博主照片上传
function handlePersonaPhoto(uploadFile: UploadFile) {
  const file = uploadFile.raw
  if (!file) return
  if (personaPhotoPreview.value) URL.revokeObjectURL(personaPhotoPreview.value)
  personaPhotoFile.value = file
  personaPhotoPreview.value = URL.createObjectURL(file)
  personaResult.value = null
  personaDescEdit.value = ''
}

// 分析博主人设
async function handleAnalyzePersona() {
  if (!personaPhotoFile.value) return
  analyzingPersona.value = true
  try {
    const data = await analyzePersona(personaPhotoFile.value)
    personaResult.value = data.persona
    personaDescEdit.value = data.persona.description || ''
    ElMessage.success('人设分析完成')
  } catch (e: unknown) {
    const msg = getErrorMessage(e, '人设分析失败')
    ElMessage.error(msg)
  } finally {
    analyzingPersona.value = false
  }
}

// ====== AI 策划主流程 ======
const planSelected = ref<boolean[]>([])  // 每个方案是否选中生成
const planCounts = ref<number[]>([])     // 每个方案生成几张

// 计算选中总张数
const totalGenCount = computed(() => {
  return planSelected.value.reduce((sum, sel, i) => sel ? sum + (planCounts.value[i] || 1) : sum, 0)
})

async function handleAIPlan() {
  if (productImages.value.length === 0) return
  planPhase.value = 'loading'
  planCards.value = []
  generating.value = false

  try {
    loadingPlanText.value = 'AI 正在策划方案...'
    const personaDesc = buildPersonaDesc()
    const planData = await planShots([...productImages.value], productInfo.value || undefined, personaDesc || undefined)
    planList.value = planData.plans

    // 默认全部选中，每方案生成 1 张
    planSelected.value = planList.value.map(() => true)
    planCounts.value = planList.value.map(() => 1)

    planPhase.value = 'ready'
    ElMessage.success(`策划完成：${planList.value.length} 个方案`)
  } catch (e: unknown) {
    const msg = getErrorMessage(e, 'AI 策划失败')
    ElMessage.error(msg)
    planPhase.value = ''
  }
}

// 返回表单
function backToForm() {
  planPhase.value = ''
}

// 生成单张策划图的通用函数
function buildPlanGenParams(plan: ShotPlan, extraPrompt?: string) {
  const desc = [plan.scene, plan.pose, plan.angle].filter(Boolean).join('，')
  return {
    task_type: 'seed_grass' as const,
    images: [...productImages.value],
    description: desc,
    style: form.value.style || undefined,
    model_name: form.value.modelName,
    aspect_ratio: form.value.aspectRatio,
    custom_prompt: extraPrompt || plan.prompt_hint || undefined,
    count: 1,
    product_info: productInfo.value || undefined,
    persona: buildPersonaDesc(),
    scene: plan.scene,
  }
}

// ====== 批量生成（策划模式） ======
async function handleBatchGenerate() {
  generating.value = true
  const totalCount = totalGenCount.value

  // 构建 planIdx 列表（展开 count）
  const taskPlanIndices: number[] = []
  planSelected.value.forEach((sel, i) => {
    if (sel) {
      for (let c = 0; c < (planCounts.value[i] || 1); c++) {
        taskPlanIndices.push(i)
      }
    }
  })

  planCards.value = taskPlanIndices.map(planIdx => ({
    imageBase64: '',
    status: 'loading' as const,
    promptUsed: '',
    _planIdx: planIdx,  // 记录对应的方案索引
  }))
  planTotalCost.value = 0
  planModelUsed.value = ''

  try {
    const promises = taskPlanIndices.map(async (planIdx, i) => {
      const plan = planList.value[planIdx]
      try {
        const data = await generateImage(buildPlanGenParams(plan))
        return {
          index: i,
          imageBase64: data.images[0] || '',
          status: 'success' as const,
          promptUsed: data.prompt_used,
          cost: data.cost,
          currency: data.currency,
          modelUsed: data.model_used,
        }
      } catch {
        return { index: i, status: 'failed' as const, error: '生成失败' }
      }
    })

    const results = await Promise.all(promises)
    for (const r of results) {
      if (r.status === 'success' && 'imageBase64' in r) {
        planCards.value[r.index] = {
          imageBase64: r.imageBase64,
          status: 'success',
          promptUsed: r.promptUsed,
        }
        planTotalCost.value += r.cost
        planCurrency.value = r.currency ?? planCurrency.value
        planModelUsed.value = r.modelUsed
      } else {
        planCards.value[r.index] = { ...planCards.value[r.index], status: 'failed', error: r.error }
      }
    }
    ElMessage.success(`批量生成完成（${totalCount} 张）`)
  } catch (e: unknown) {
    const msg = getErrorMessage(e, '生成失败')
    ElMessage.error(msg)
  } finally {
    generating.value = false
  }
}

// 策划模式单张重试
async function handlePlanRetry(index: number) {
  const card = planCards.value[index]
  const planIdx = card._planIdx ?? index
  planCards.value[index] = { ...card, status: 'loading', error: undefined }

  const plan = planList.value[planIdx]
  try {
    const data = await generateImage(buildPlanGenParams(plan))
    if (data.images.length > 0) {
      planCards.value[index] = {
        imageBase64: data.images[0],
        status: 'success',
        promptUsed: data.prompt_used,
        _planIdx: planIdx,
      }
      planTotalCost.value += data.cost
      planCurrency.value = data.currency ?? '¥'
      ElMessage.success(`图${planIdx + 1}: ${plan.title} 重新生成完成`)
    }
  } catch (e: unknown) {
    const msg = getErrorMessage(e, '重试失败')
    planCards.value[index] = { ...planCards.value[index], status: 'failed', error: msg }
    ElMessage.error(msg)
  }
}

// 策划模式编辑 Prompt 重试
async function handlePlanRetryWithPrompt(index: number, extraPrompt: string) {
  const card = planCards.value[index]
  const planIdx = card._planIdx ?? index
  planCards.value[index] = { ...card, status: 'loading', error: undefined }

  const plan = planList.value[planIdx]
  try {
    const data = await generateImage(buildPlanGenParams(plan, extraPrompt))
    if (data.images.length > 0) {
      planCards.value[index] = {
        imageBase64: data.images[0],
        status: 'success',
        promptUsed: data.prompt_used,
        _planIdx: planIdx,
      }
      planTotalCost.value += data.cost
      planCurrency.value = data.currency ?? '¥'
      ElMessage.success(`图${planIdx + 1}: ${plan.title} 重新生成完成`)
    }
  } catch (e: unknown) {
    const msg = getErrorMessage(e, '重试失败')
    planCards.value[index] = { ...planCards.value[index], status: 'failed', error: msg }
    ElMessage.error(msg)
  }
}

function handlePlanRemove(index: number) {
  planCards.value.splice(index, 1)
}

// 换模型对比（策划模式）
async function handlePlanCompareModel(cardIndex: number, newModel: string) {
  const card = planCards.value[cardIndex]
  const planIdx = card._planIdx ?? cardIndex
  const plan = planList.value[planIdx]

  const startIdx = planCards.value.length
  planCards.value.push({
    imageBase64: '',
    status: 'loading',
    promptUsed: card.promptUsed,
    _planIdx: planIdx,
  })

  try {
    const params = buildPlanGenParams(plan)
    params.model_name = newModel
    const data = await generateImage(params)

    if (data.images.length > 0) {
      planCards.value[startIdx] = {
        imageBase64: data.images[0],
        status: 'success',
        promptUsed: data.prompt_used,
        _planIdx: planIdx,
      }
      planTotalCost.value += data.cost
      planCurrency.value = data.currency ?? '¥'
    }
  } catch (e: unknown) {
    planCards.value[startIdx] = {
      ...planCards.value[startIdx],
      status: 'failed',
      error: getErrorMessage(e),
    }
  }
}

// ====== 手动模式生成 ======
async function handleManualGenerate() {
  if (!canManualGenerate.value) return
  loading.value = true

  const genCount = form.value.count
  const newCards: ResultCard[] = Array.from({ length: genCount }, () => ({
    imageBase64: '',
    status: 'loading' as const,
    promptUsed: '',
  }))
  cards.value = newCards
  totalCost.value = 0
  modelUsed.value = ''

  try {
    const data = await generateImage({
      task_type: 'seed_grass',
      images: [...productImages.value],
      description: form.value.scene || '自然生活场景',
      style: form.value.style || undefined,
      model_name: form.value.modelName,
      aspect_ratio: form.value.aspectRatio,
      count: genCount,
      product_info: productInfo.value || undefined,
      persona: buildPersonaDesc(),
      scene: form.value.scene || undefined,
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

// 手动模式单张重试
async function handleRetry(index: number) {
  const card = cards.value[index]
  cards.value[index] = { ...card, status: 'loading', error: undefined }

  try {
    const data = await generateImage({
      task_type: 'seed_grass',
      images: [...productImages.value],
      description: form.value.scene || '自然生活场景',
      style: form.value.style || undefined,
      model_name: form.value.modelName,
      aspect_ratio: form.value.aspectRatio,
      count: 1,
      persona: buildPersonaDesc(),
      scene: form.value.scene || undefined,
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

// 手动模式编辑 Prompt 重试
async function handleRetryWithPrompt(index: number, extraPrompt: string) {
  const card = cards.value[index]
  cards.value[index] = { ...card, status: 'loading', error: undefined }

  try {
    const data = await generateImage({
      task_type: 'seed_grass',
      images: [...productImages.value],
      description: form.value.scene || '自然生活场景',
      style: form.value.style || undefined,
      model_name: form.value.modelName,
      aspect_ratio: form.value.aspectRatio,
      custom_prompt: extraPrompt || undefined,
      count: 1,
      persona: buildPersonaDesc(),
      scene: form.value.scene || undefined,
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

// 换模型对比（手动模式）
async function handleCompareModel(cardIndex: number, newModel: string) {
  const sourcePrompt = cards.value[cardIndex].promptUsed
  const startIdx = cards.value.length
  cards.value.push({
    imageBase64: '',
    status: 'loading',
    promptUsed: sourcePrompt,
  })

  try {
    const data = await generateImage({
      task_type: 'seed_grass',
      images: [...productImages.value],
      description: form.value.scene || '自然生活场景',
      style: form.value.style || undefined,
      model_name: newModel,
      aspect_ratio: form.value.aspectRatio,
      count: 1,
      persona: buildPersonaDesc(),
      scene: form.value.scene || undefined,
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

function handleRemove(index: number) {
  cards.value.splice(index, 1)
}
</script>

<style scoped>
.seed-grass {
  max-width: 1200px;
}

.page-header {
  margin-bottom: 16px;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  margin: 0 0 6px;
  display: inline-flex;
  align-items: center;
  background: linear-gradient(135deg, var(--el-color-primary), var(--el-color-primary-light-3));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.page-desc {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  margin: 0;
  line-height: 1.6;
}

.main-content {
  margin-top: 20px;
}

.mode-tabs {
  margin-bottom: 16px;
}

/* 商品图多图上传 */
.product-images-area {
  width: 100%;
}

.product-thumbnails {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: flex-start;
}

.product-thumb {
  position: relative;
  width: 84px;
  height: 84px;
  border-radius: 10px;
  overflow: hidden;
  border: 2px solid var(--border-color);
  transition: border-color 0.2s;
}

.product-thumb:hover {
  border-color: #409eff;
}

.product-thumb img {
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

.product-thumb:hover .thumb-remove {
  opacity: 1;
}

.product-add-btn :deep(.el-upload) {
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

.product-add-btn :deep(.el-upload:hover) {
  border-color: #409eff;
  background: rgba(64, 158, 255, 0.04);
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
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.5;
}

/* 人设标签 */
.persona-tags-area {
  width: 100%;
}

.persona-mode-switch {
  margin-bottom: 10px;
}

.persona-photo-area {
  width: 100%;
}

.persona-photo-upload :deep(.el-upload-dragger) {
  padding: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  border: 2px dashed var(--border-color);
  transition: all 0.25s;
}

.persona-photo-upload :deep(.el-upload-dragger:hover) {
  border-color: #409eff;
}

.persona-photo-slot {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  color: var(--text-secondary);
  font-size: 14px;
}

.upload-hint {
  font-size: 12px;
  color: var(--text-secondary);
}

.persona-photo-preview {
  position: relative;
  width: 160px;
  height: 160px;
  border-radius: 10px;
  overflow: hidden;
  border: 2px solid var(--border-color);
}

.persona-photo-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.photo-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  color: white;
  font-size: 12px;
  opacity: 0;
  transition: opacity 0.2s;
}

.persona-photo-preview:hover .photo-overlay {
  opacity: 1;
}

.persona-result {
  margin-top: 10px;
}

.persona-tags-result {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.persona-scenes {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  margin-top: 6px;
}

.tag-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-bottom: 6px;
}

.tag-label {
  font-size: 12px;
  color: var(--text-secondary);
  min-width: 36px;
}

.scene-area {
  width: 100%;
}

.preset-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}

.preset-tag {
  cursor: pointer;
  transition: all 0.2s;
}

.preset-tag:hover {
  color: #409eff;
  border-color: #409eff;
  transform: translateY(-1px);
}

/* ====== 策划加载态 ====== */
.plan-loading-view {
  margin-top: 20px;
}

.plan-loading-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 60px 20px;
}

.plan-loading-text {
  font-size: 15px;
  color: var(--text-regular);
  margin: 0;
}

/* ====== 策划结果视图 ====== */
.plan-result-view {
  margin-top: 20px;
}

.plan-result-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}

.plan-result-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.plan-section-label {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 10px;
}

.plan-result-body {
  margin-top: 16px;
}

/* 方案列表 */
.plan-scroll-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 600px;
  overflow-y: auto;
  padding-right: 4px;
}

.plan-card {
  border: 1px solid var(--border-color);
  border-radius: 10px;
  transition: border-color 0.2s;
}

.plan-card:hover {
  border-color: #409eff;
}

.plan-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.plan-checkbox :deep(.el-checkbox__label) {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.plan-card-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.plan-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.plan-title {
  font-weight: 500;
  font-size: 14px;
}

.plan-details p {
  font-size: 13px;
  color: var(--text-regular);
  margin: 2px 0;
}

.plan-details {
  margin-top: 8px;
}

/* 生成结果区域 */
.plan-results-section {
  margin-top: 20px;
}
</style>
