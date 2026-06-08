<template>
  <div class="product-image">
    <!-- ====== 顶部 Tab 切换 ====== -->
    <el-tabs v-model="activeTab" class="main-tabs">
      <!-- ====== Tab 1: 商品主图 ====== -->
      <el-tab-pane label="商品主图" name="main">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-card>
              <el-form label-position="top">
                <!-- 商品图上传（多图） -->
                <el-form-item label="商品/服装图" required>
                  <div class="product-images-area">
                    <div class="product-thumbnails">
                      <div v-for="(preview, idx) in mainPreviews" :key="idx" class="product-thumb">
                        <img :src="preview" />
                        <el-icon class="thumb-remove" @click="removeMainImage(idx)"><Close /></el-icon>
                      </div>
                      <el-upload
                        v-if="mainImages.length < 6"
                        :auto-upload="false"
                        :show-file-list="false"
                        :on-change="handleMainImage"
                        accept=".jpg,.jpeg,.png,.webp"
                        class="product-add-btn"
                      >
                        <div class="add-slot">
                          <el-icon :size="24"><Plus /></el-icon>
                          <span>{{ mainImages.length === 0 ? '上传商品图' : '添加更多' }}</span>
                        </div>
                      </el-upload>
                    </div>
                    <div class="product-hint">上传商品图，AI 生成白底主图</div>
                  </div>
                </el-form-item>

                <!-- 商品信息 -->
                <ProductInfoForm v-model="mainProductInfo" :image="mainImages[0] || null" />

                <!-- 比例固定 1:1 -->
                <el-form-item label="图片比例">
                  <el-tag type="info" size="large">1:1 正方形（亚马逊主图标准）</el-tag>
                </el-form-item>

                <!-- 生成数量 -->
                <el-form-item label="生成数量">
                  <el-slider v-model="mainCount" :min="1" :max="4" :step="1" show-stops />
                </el-form-item>

                <!-- 额外描述 -->
                <el-form-item label="补充描述（可选）">
                  <el-input
                    v-model="mainCustomPrompt"
                    type="textarea"
                    :rows="2"
                    placeholder="如：展示正面、展示背面细节、模特试穿效果等"
                  />
                </el-form-item>

                <el-button
                  type="primary"
                  :loading="mainLoading"
                  :disabled="mainImages.length === 0"
                  @click="handleMainGenerate"
                >
                  生成主图（{{ mainCount }} 张）
                </el-button>
              </el-form>
            </el-card>
          </el-col>

          <el-col :span="12">
            <ResultCardManager
              :cards="mainCards"
              :model-used="mainModelUsed"
              :total-cost="mainTotalCost"
              @retry="handleMainRetry"
              @retry-with-prompt="handleMainRetryWithPrompt"
              @remove="handleMainRemove"
            />
          </el-col>
        </el-row>
      </el-tab-pane>

      <!-- ====== Tab 2: A+ 图 ====== -->
      <el-tab-pane label="A+ 图" name="aplus">
        <!-- 正常态：表单视图 -->
        <div v-if="aplusPhase === ''">
          <el-row :gutter="20">
            <el-col :span="12">
              <el-card>
                <!-- A+ 模式切换 -->
                <el-tabs v-model="aplusMode" class="mode-tabs">
                  <el-tab-pane label="手动配置" name="manual" />
                  <el-tab-pane label="AI 策划" name="ai-plan" />
                </el-tabs>

                <el-form label-position="top">
                  <!-- 商品图上传 -->
                  <el-form-item label="商品/服装图" required>
                    <div class="product-images-area">
                      <div class="product-thumbnails">
                        <div v-for="(preview, idx) in aplusPreviews" :key="idx" class="product-thumb">
                          <img :src="preview" />
                          <el-icon class="thumb-remove" @click="removeAplusImage(idx)"><Close /></el-icon>
                        </div>
                        <el-upload
                          v-if="aplusImages.length < 6"
                          :auto-upload="false"
                          :show-file-list="false"
                          :on-change="handleAplusImage"
                          accept=".jpg,.jpeg,.png,.webp"
                          class="product-add-btn"
                        >
                          <div class="add-slot">
                            <el-icon :size="24"><Plus /></el-icon>
                            <span>{{ aplusImages.length === 0 ? '上传商品图' : '添加更多' }}</span>
                          </div>
                        </el-upload>
                      </div>
                      <div class="product-hint">上传商品图，AI 策划 A+ 内容方案</div>
                    </div>
                  </el-form-item>

                  <!-- 商品信息 -->
                  <ProductInfoForm v-model="aplusProductInfo" :image="aplusImages[0] || null" />

                  <!-- AI 策划按钮 -->
                  <div v-if="aplusMode === 'ai-plan'" class="ai-plan-section">
                    <el-button
                      type="success"
                      :loading="aplusPlanLoading"
                      :disabled="aplusImages.length === 0"
                      @click="handleAplusPlan"
                    >
                      AI 策划 A+ 方案
                    </el-button>
                  </div>

                  <!-- 手动模式专属字段 -->
                  <template v-if="aplusMode === 'manual'">
                    <el-form-item label="核心卖点">
                      <el-input v-model="aplusForm.sellingPoint" placeholder="如：面料柔软亲肤、版型修身显瘦" />
                    </el-form-item>

                    <el-form-item label="标题文字（英文，会渲染到图中）">
                      <el-input v-model="aplusForm.headline" placeholder="如：Ultra-Soft Fabric" />
                    </el-form-item>

                    <el-form-item label="正文文字（英文，会渲染到图中）">
                      <el-input
                        v-model="aplusForm.bodyText"
                        type="textarea"
                        :rows="2"
                        placeholder="如：Premium cotton blend that feels incredibly soft"
                      />
                    </el-form-item>

                    <el-form-item label="布局类型">
                      <el-select v-model="aplusForm.layout" style="width: 100%">
                        <el-option label="左图右文" value="left_image_right_text" />
                        <el-option label="右图左文" value="right_image_left_text" />
                        <el-option label="上图下文" value="top_image_bottom_text" />
                        <el-option label="全图覆盖文字" value="full_image_with_overlay" />
                      </el-select>
                    </el-form-item>

                    <el-form-item label="场景/背景描述">
                      <el-input
                        v-model="aplusForm.scene"
                        type="textarea"
                        :rows="2"
                        placeholder="如：浅色木纹桌面、柔和渐变色背景"
                      />
                    </el-form-item>

                    <el-form-item label="风格">
                      <el-select v-model="aplusForm.style" style="width: 100%">
                        <el-option label="现代简约电商风格" value="现代简约电商风格" />
                        <el-option label="高端奢华质感" value="高端奢华质感" />
                        <el-option label="清新自然风格" value="清新自然风格" />
                        <el-option label="活力运动风格" value="活力运动风格" />
                      </el-select>
                    </el-form-item>

                    <el-button
                      type="primary"
                      :loading="aplusLoading"
                      :disabled="aplusImages.length === 0"
                      @click="handleAplusManualGenerate"
                    >
                      生成 A+ 图
                    </el-button>
                  </template>
                </el-form>

                <!-- 通用参数 -->
                <el-form v-if="aplusMode === 'ai-plan'" label-position="top" style="margin-top: 12px">
                  <el-form-item label="图片比例">
                    <el-select v-model="aplusForm.aspectRatio" style="width: 100%">
                      <el-option label="61:25 亚马逊 A+ Banner" value="61:25" />
                      <el-option label="16:9 横版" value="16:9" />
                      <el-option label="4:3 横版" value="4:3" />
                      <el-option label="1:1 正方形" value="1:1" />
                    </el-select>
                  </el-form-item>
                </el-form>
              </el-card>
            </el-col>

            <el-col :span="12">
              <ResultCardManager
                :cards="aplusCards"
                :model-used="aplusModelUsed"
                :total-cost="aplusTotalCost"
                @retry="handleAplusRetry"
                @retry-with-prompt="handleAplusRetryWithPrompt"
                @remove="handleAplusRemove"
              />
            </el-col>
          </el-row>
        </div>

        <!-- 策划加载中 -->
        <div v-else-if="aplusPhase === 'loading'" class="plan-loading">
          <el-icon :size="48" class="loading-icon"><Loading /></el-icon>
          <p>AI 正在策划 A+ 方案...</p>
        </div>

        <!-- 策划结果视图 -->
        <div v-else-if="aplusPhase === 'ready'" class="plan-results">
          <div class="plan-header">
            <el-button @click="aplusPhase = ''">
              <el-icon><ArrowLeft /></el-icon> 返回
            </el-button>
            <h3>AI 策划方案（{{ planList.length }} 张）</h3>
            <el-button
              type="primary"
              :loading="aplusLoading"
              :disabled="totalAplusGenCount === 0"
              @click="handleAplusBatchGenerate"
            >
              一键生成全部（{{ totalAplusGenCount }} 张）
            </el-button>
          </div>

          <!-- 方案列表 -->
          <div class="plan-cards">
            <el-card
              v-for="(plan, idx) in planList"
              :key="idx"
              class="plan-card"
              :class="{ 'plan-card-selected': planSelected[idx] }"
            >
              <div class="plan-card-header">
                <el-checkbox v-model="planSelected[idx]" @change="onPlanSelectionChange">
                  <el-tag size="small" type="primary">图{{ idx + 1 }}</el-tag>
                  {{ plan.type }}
                </el-checkbox>
                <div class="plan-count-control">
                  <span class="plan-count-label">张数：</span>
                  <el-input-number v-model="planCounts[idx]" :min="1" :max="4" size="small" />
                </div>
              </div>
              <div v-if="planSelected[idx]" class="plan-card-body">
                <div class="plan-detail-row">
                  <strong>卖点：</strong>{{ plan.selling_point }}
                </div>
                <div class="plan-detail-row">
                  <strong>标题：</strong>
                  <el-input v-model="plan.headline" size="small" />
                </div>
                <div class="plan-detail-row">
                  <strong>正文：</strong>
                  <el-input v-model="plan.body_text" type="textarea" :rows="2" size="small" />
                </div>
                <div class="plan-detail-row">
                  <strong>布局：</strong>
                  <el-select v-model="plan.layout" size="small">
                    <el-option label="左图右文" value="left_image_right_text" />
                    <el-option label="右图左文" value="right_image_left_text" />
                    <el-option label="上图下文" value="top_image_bottom_text" />
                    <el-option label="全图覆盖文字" value="full_image_with_overlay" />
                  </el-select>
                </div>
                <div class="plan-detail-row">
                  <strong>场景：</strong>{{ plan.scene }}
                </div>
              </div>
            </el-card>
          </div>

          <!-- 生成结果 -->
          <ResultCardManager
            :cards="aplusCards"
            :model-used="aplusModelUsed"
            :total-cost="aplusTotalCost"
            :labels="aplusCardLabels"
            @retry="handleAplusPlanRetry"
            @retry-with-prompt="handleAplusPlanRetryWithPrompt"
            @remove="handleAplusRemove"
          />
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Close, Plus, Loading, ArrowLeft } from '@element-plus/icons-vue'
import { generateImage, planAplus } from '../api'
import type { ResultCard, AplusPlan } from '../types'
import ResultCardManager from '../components/ResultCardManager.vue'
import ProductInfoForm from '../components/ProductInfoForm.vue'

// ====== Tab 切换 ======
const activeTab = ref<'main' | 'aplus'>('main')

// ====== 商品主图状态 ======
const mainImages = ref<File[]>([])
const mainPreviews = ref<string[]>([])
const mainProductInfo = ref('')
const mainCount = ref(1)
const mainCustomPrompt = ref('')
const mainLoading = ref(false)
const mainCards = ref<ResultCard[]>([])
const mainModelUsed = ref('')
const mainTotalCost = ref(0)

// ====== A+ 图状态 ======
const aplusMode = ref<'manual' | 'ai-plan'>('manual')
const aplusPhase = ref<'' | 'loading' | 'ready'>('')
const aplusImages = ref<File[]>([])
const aplusPreviews = ref<string[]>([])
const aplusProductInfo = ref('')
const aplusForm = ref({
  sellingPoint: '',
  headline: '',
  bodyText: '',
  layout: 'left_image_right_text',
  scene: '',
  style: '现代简约电商风格',
  aspectRatio: '61:25',
})
const aplusLoading = ref(false)
const aplusCards = ref<ResultCard[]>([])
const aplusModelUsed = ref('')
const aplusTotalCost = ref(0)
const aplusPlanLoading = ref(false)

// AI 策划状态
const planList = ref<AplusPlan[]>([])
const planSelected = ref<boolean[]>([])
const planCounts = ref<number[]>([])
const aplusGenTasks = ref<{ planIdx: number }[]>([])

const totalAplusGenCount = computed(() => {
  let total = 0
  for (let i = 0; i < planSelected.value.length; i++) {
    if (planSelected.value[i]) {
      total += planCounts.value[i] || 1
    }
  }
  return total
})

const aplusCardLabels = computed(() =>
  aplusGenTasks.value.map(t => {
    const plan = planList.value[t.planIdx]
    return plan ? `${plan.type} · ${plan.selling_point}` : ''
  })
)

// ====== 商品主图：图片上传 ======
function handleMainImage(file: any) {
  const raw = file.raw as File
  mainImages.value.push(raw)
  mainPreviews.value.push(URL.createObjectURL(raw))
}

function removeMainImage(idx: number) {
  mainImages.value.splice(idx, 1)
  mainPreviews.value.splice(idx, 1)
}

// ====== 商品主图：生成 ======
async function handleMainGenerate() {
  if (mainImages.value.length === 0) {
    ElMessage.warning('请上传商品图')
    return
  }

  mainLoading.value = true
  const newCards: ResultCard[] = Array.from({ length: mainCount.value }, () => ({
    imageBase64: '',
    status: 'loading' as const,
    promptUsed: '',
  }))
  mainCards.value = [...mainCards.value, ...newCards]
  const startIdx = mainCards.value.length - mainCount.value

  try {
    const result = await generateImage({
      task_type: 'product_main',
      images: mainImages.value,
      description: mainProductInfo.value || '商品正面展示',
      aspect_ratio: '1:1',
      count: mainCount.value,
      product_info: mainProductInfo.value || undefined,
      custom_prompt: mainCustomPrompt.value || undefined,
    })

    for (let i = 0; i < mainCount.value; i++) {
      if (result.images[i]) {
        mainCards.value[startIdx + i] = {
          imageBase64: result.images[i],
          status: 'success',
          promptUsed: result.prompt_used,
        }
      } else {
        mainCards.value[startIdx + i] = {
          imageBase64: '',
          status: 'failed',
          promptUsed: '',
          error: '生成失败',
        }
      }
    }
    mainModelUsed.value = result.model_used
    mainTotalCost.value += result.cost
    ElMessage.success(`生成 ${result.images.length} 张主图`)
  } catch (e: any) {
    for (let i = 0; i < mainCount.value; i++) {
      mainCards.value[startIdx + i] = {
        imageBase64: '',
        status: 'failed',
        promptUsed: '',
        error: e?.response?.data?.detail || e.message || '生成失败',
      }
    }
    ElMessage.error('主图生成失败')
  } finally {
    mainLoading.value = false
  }
}

function handleMainRetry(idx: number) {
  mainCards.value.splice(idx, 1)
}

function handleMainRetryWithPrompt(idx: number, extraPrompt: string) {
  mainCards.value.splice(idx, 1)
  // 带额外 prompt 重新生成
  mainCustomPrompt.value = extraPrompt
  handleMainGenerate()
}

function handleMainRemove(idx: number) {
  mainCards.value.splice(idx, 1)
}

// ====== A+ 图：图片上传 ======
function handleAplusImage(file: any) {
  const raw = file.raw as File
  aplusImages.value.push(raw)
  aplusPreviews.value.push(URL.createObjectURL(raw))
}

function removeAplusImage(idx: number) {
  aplusImages.value.splice(idx, 1)
  aplusPreviews.value.splice(idx, 1)
}

// ====== A+ 图：手动模式生成 ======
async function handleAplusManualGenerate() {
  if (aplusImages.value.length === 0) {
    ElMessage.warning('请上传商品图')
    return
  }

  aplusLoading.value = true
  const newCard: ResultCard = { imageBase64: '', status: 'loading', promptUsed: '' }
  aplusCards.value.push(newCard)
  const idx = aplusCards.value.length - 1

  try {
    const result = await generateImage({
      task_type: 'aplus',
      images: aplusImages.value,
      description: aplusForm.value.scene || aplusProductInfo.value || 'A+ content image',
      style: aplusForm.value.style || undefined,
      aspect_ratio: aplusForm.value.aspectRatio,
      product_info: aplusProductInfo.value || undefined,
      selling_point: aplusForm.value.sellingPoint || undefined,
      headline: aplusForm.value.headline || undefined,
      body_text: aplusForm.value.bodyText || undefined,
      layout: aplusForm.value.layout || undefined,
    })

    aplusCards.value[idx] = {
      imageBase64: result.images[0],
      status: 'success',
      promptUsed: result.prompt_used,
    }
    aplusModelUsed.value = result.model_used
    aplusTotalCost.value += result.cost
    ElMessage.success('A+ 图生成成功')
  } catch (e: any) {
    aplusCards.value[idx] = {
      imageBase64: '',
      status: 'failed',
      promptUsed: '',
      error: e?.response?.data?.detail || e.message || '生成失败',
    }
    ElMessage.error('A+ 图生成失败')
  } finally {
    aplusLoading.value = false
  }
}

// ====== A+ 图：AI 策划 ======
async function handleAplusPlan() {
  if (aplusImages.value.length === 0) {
    ElMessage.warning('请上传商品图')
    return
  }

  aplusPlanLoading.value = true
  aplusPhase.value = 'loading'

  try {
    const result = await planAplus(aplusImages.value, aplusProductInfo.value || undefined)
    planList.value = result.plans
    planSelected.value = result.plans.map(() => true)
    planCounts.value = result.plans.map(() => 1)
    aplusPhase.value = 'ready'
    ElMessage.success(`策划了 ${result.plans.length} 张 A+ 方案`)
  } catch (e: any) {
    aplusPhase.value = ''
    ElMessage.error(e?.response?.data?.detail || 'AI 策划失败')
  } finally {
    aplusPlanLoading.value = false
  }
}

function onPlanSelectionChange() {
  // 触发 totalAplusGenCount 重新计算
}

// ====== A+ 图：批量生成 ======
async function handleAplusBatchGenerate() {
  if (totalAplusGenCount.value === 0) {
    ElMessage.warning('请至少选择一个方案')
    return
  }

  aplusLoading.value = true

  // 构建任务列表
  const tasks: { planIdx: number }[] = []
  for (let i = 0; i < planSelected.value.length; i++) {
    if (planSelected.value[i]) {
      const count = planCounts.value[i] || 1
      for (let c = 0; c < count; c++) {
        tasks.push({ planIdx: i })
      }
    }
  }

  aplusGenTasks.value = tasks
  const newCards: ResultCard[] = tasks.map(() => ({
    imageBase64: '',
    status: 'loading' as const,
    promptUsed: '',
  }))
  aplusCards.value = [...aplusCards.value, ...newCards]
  const startIdx = aplusCards.value.length - tasks.length

  // 并行生成
  const promises = tasks.map(async (task, i) => {
    const plan = planList.value[task.planIdx]
    try {
      const result = await generateImage({
        task_type: 'aplus',
        images: aplusImages.value,
        description: plan.scene || aplusProductInfo.value || 'A+ content image',
        style: '现代简约电商风格',
        aspect_ratio: aplusForm.value.aspectRatio,
        product_info: aplusProductInfo.value || undefined,
        selling_point: plan.selling_point,
        headline: plan.headline,
        body_text: plan.body_text,
        layout: plan.layout,
        custom_prompt: plan.prompt_hint || undefined,
      })

      aplusCards.value[startIdx + i] = {
        imageBase64: result.images[0],
        status: 'success',
        promptUsed: result.prompt_used,
      }
      aplusTotalCost.value += result.cost
      aplusModelUsed.value = result.model_used
    } catch (e: any) {
      aplusCards.value[startIdx + i] = {
        imageBase64: '',
        status: 'failed',
        promptUsed: '',
        error: e?.response?.data?.detail || e.message || '生成失败',
      }
    }
  })

  await Promise.all(promises)
  aplusLoading.value = false
  ElMessage.success('批量生成完成')
}

// ====== A+ 图：重试 ======
function handleAplusRetry(idx: number) {
  aplusCards.value.splice(idx, 1)
}

function handleAplusRetryWithPrompt(idx: number, extraPrompt: string) {
  aplusCards.value.splice(idx, 1)
  aplusForm.value.scene = extraPrompt
  handleAplusManualGenerate()
}

function handleAplusRemove(idx: number) {
  aplusCards.value.splice(idx, 1)
}

function handleAplusPlanRetry(idx: number) {
  const task = aplusGenTasks.value[idx]
  if (!task) return
  const plan = planList.value[task.planIdx]
  aplusCards.value[idx] = { imageBase64: '', status: 'loading', promptUsed: '' }

  generateImage({
    task_type: 'aplus',
    images: aplusImages.value,
    description: plan.scene || aplusProductInfo.value || '',
    style: '现代简约电商风格',
    aspect_ratio: aplusForm.value.aspectRatio,
    product_info: aplusProductInfo.value || undefined,
    selling_point: plan.selling_point,
    headline: plan.headline,
    body_text: plan.body_text,
    layout: plan.layout,
    custom_prompt: plan.prompt_hint || undefined,
  }).then(result => {
    aplusCards.value[idx] = {
      imageBase64: result.images[0],
      status: 'success',
      promptUsed: result.prompt_used,
    }
    aplusTotalCost.value += result.cost
  }).catch(() => {
    aplusCards.value[idx] = {
      imageBase64: '',
      status: 'failed',
      promptUsed: '',
      error: '重试失败',
    }
  })
}

function handleAplusPlanRetryWithPrompt(idx: number, extraPrompt: string) {
  const task = aplusGenTasks.value[idx]
  if (!task) return
  const plan = planList.value[task.planIdx]
  aplusCards.value[idx] = { imageBase64: '', status: 'loading', promptUsed: '' }

  generateImage({
    task_type: 'aplus',
    images: aplusImages.value,
    description: plan.scene || aplusProductInfo.value || '',
    style: '现代简约电商风格',
    aspect_ratio: aplusForm.value.aspectRatio,
    product_info: aplusProductInfo.value || undefined,
    selling_point: plan.selling_point,
    headline: plan.headline,
    body_text: plan.body_text,
    layout: plan.layout,
    custom_prompt: `${plan.prompt_hint || ''} ${extraPrompt}`,
  }).then(result => {
    aplusCards.value[idx] = {
      imageBase64: result.images[0],
      status: 'success',
      promptUsed: result.prompt_used,
    }
    aplusTotalCost.value += result.cost
  }).catch(() => {
    aplusCards.value[idx] = {
      imageBase64: '',
      status: 'failed',
      promptUsed: '',
      error: '重试失败',
    }
  })
}
</script>

<style scoped>
.product-image {
  max-width: 1400px;
}

.main-tabs {
  margin-top: 16px;
}

/* 商品图上传区域 */
.product-images-area {
  width: 100%;
}

.product-thumbnails {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.product-thumb {
  position: relative;
  width: 80px;
  height: 80px;
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid #e4e7ed;
}

.product-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.thumb-remove {
  position: absolute;
  top: 2px;
  right: 2px;
  background: rgba(0, 0, 0, 0.5);
  color: white;
  border-radius: 50%;
  cursor: pointer;
  font-size: 12px;
  padding: 2px;
}

.product-add-btn :deep(.el-upload) {
  width: 80px;
  height: 80px;
  border: 2px dashed #dcdfe6;
  border-radius: 6px;
  cursor: pointer;
  transition: border-color 0.2s;
}

.product-add-btn :deep(.el-upload:hover) {
  border-color: #409eff;
}

.add-slot {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #909399;
  font-size: 12px;
  gap: 4px;
}

.product-hint {
  font-size: 12px;
  color: #909399;
  margin-top: 6px;
}

/* 模式切换 */
.mode-tabs {
  margin-bottom: 12px;
}

.ai-plan-section {
  margin: 16px 0;
}

/* 策划加载 */
.plan-loading {
  text-align: center;
  padding: 80px 0;
  color: #909399;
}

.loading-icon {
  animation: rotate 1.5s linear infinite;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* 策划结果 */
.plan-results {
  margin-top: 16px;
}

.plan-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}

.plan-header h3 {
  flex: 1;
  margin: 0;
}

/* 方案卡片 */
.plan-cards {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 20px;
}

.plan-card {
  transition: border-color 0.2s;
}

.plan-card-selected {
  border-color: #409eff;
}

.plan-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.plan-count-control {
  display: flex;
  align-items: center;
  gap: 4px;
}

.plan-count-label {
  font-size: 13px;
  color: #606266;
}

.plan-card-body {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #ebeef5;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.plan-detail-row {
  font-size: 13px;
  color: #606266;
}

.plan-detail-row strong {
  color: #303133;
  margin-right: 8px;
}
</style>
