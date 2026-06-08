<template>
  <div class="product-analysis">
    <el-row :gutter="20" class="main-content">
      <!-- 左侧：上传 -->
      <el-col :span="10">
        <el-card>
          <el-form label-position="top">
            <!-- 图片上传 -->
            <el-form-item label="商品图片" required>
              <el-upload
                v-if="!imagePreview"
                :auto-upload="false"
                :show-file-list="false"
                :on-change="handleImageChange"
                accept=".jpg,.jpeg,.png,.webp"
                drag
                class="upload-area"
              >
                <el-icon :size="40"><UploadFilled /></el-icon>
                <div class="upload-text">拖拽或点击上传商品图片</div>
                <div class="upload-hint">支持 JPG / PNG / WebP，最大 20MB</div>
              </el-upload>
              <div v-else class="preview-area">
                <img :src="imagePreview" alt="商品预览" />
                <el-button
                  class="preview-remove"
                  type="danger"
                  :icon="Close"
                  circle
                  size="small"
                  @click="clearImage"
                />
              </div>
            </el-form-item>

            <!-- 额外提示 -->
            <el-form-item label="补充提示（可选）">
              <el-input
                v-model="extraPrompt"
                type="textarea"
                :rows="2"
                placeholder="如：这是一件夏季连衣裙 / 请重点关注面料质感"
              />
            </el-form-item>

            <!-- 分析按钮 -->
            <el-form-item>
              <el-button
                type="primary"
                size="large"
                :loading="loading"
                :disabled="!imageFile"
                @click="handleAnalyze"
                style="width: 100%"
              >
                {{ loading ? '分析中...' : '开始分析' }}
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <!-- 右侧：分析结果 -->
      <el-col :span="14">
        <!-- 无结果 -->
        <el-card v-if="!result && !loading">
          <el-empty description="上传商品图片后点击分析" />
        </el-card>

        <!-- 加载中 -->
        <el-card v-else-if="loading">
          <div class="loading-state">
            <el-icon :size="32" class="spin"><Loading /></el-icon>
            <p>AI 正在分析商品图片...</p>
          </div>
        </el-card>

        <!-- 结果展示 -->
        <el-card v-else-if="result" class="result-card">
          <template #header>
            <div class="result-header">
              <span>分析结果</span>
              <el-tag size="small" type="info">{{ result._meta?.model }}</el-tag>
            </div>
          </template>

          <!-- 基本信息 -->
          <el-descriptions :column="2" border size="default">
            <el-descriptions-item label="服装类型">{{ result.category }}</el-descriptions-item>
            <el-descriptions-item label="款式风格">{{ result.style }}</el-descriptions-item>
            <el-descriptions-item label="颜色">{{ result.color }}</el-descriptions-item>
            <el-descriptions-item label="面料">{{ result.fabric }}</el-descriptions-item>
            <el-descriptions-item label="图案">{{ result.pattern }}</el-descriptions-item>
            <el-descriptions-item label="工艺细节">{{ result.details }}</el-descriptions-item>
            <el-descriptions-item label="目标受众">{{ result.target_audience }}</el-descriptions-item>
            <el-descriptions-item label="适合季节">{{ result.season }}</el-descriptions-item>
          </el-descriptions>

          <!-- 核心卖点 -->
          <div class="section">
            <h4>核心卖点</h4>
            <div class="tag-list">
              <el-tag
                v-for="(sp, idx) in result.selling_points"
                :key="idx"
                type="success"
                effect="plain"
                class="analysis-tag"
              >{{ sp }}</el-tag>
            </div>
          </div>

          <!-- 适用场景 -->
          <div class="section">
            <h4>适用场景</h4>
            <div class="tag-list">
              <el-tag
                v-for="(scene, idx) in result.suitable_scenes"
                :key="idx"
                type="warning"
                effect="plain"
                class="analysis-tag"
              >{{ scene }}</el-tag>
            </div>
          </div>

          <!-- 关键词 -->
          <div class="section">
            <h4>关键词（可用于 AI 生图）</h4>
            <div class="tag-list">
              <el-tag
                v-for="(kw, idx) in result.keywords"
                :key="idx"
                effect="plain"
                class="analysis-tag"
              >{{ kw }}</el-tag>
            </div>
          </div>

          <!-- 使用分析结果去生成 -->
          <el-divider />
          <el-button type="primary" @click="goToGenerate">
            用分析结果去生成穿搭图
          </el-button>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { UploadFilled, Close, Loading } from '@element-plus/icons-vue'
import type { UploadFile } from 'element-plus'
import { analyzeProduct } from '../api'
import type { ProductAnalysis } from '../types'

const router = useRouter()

const imageFile = ref<File | null>(null)
const imagePreview = ref<string>('')
const extraPrompt = ref('')
const loading = ref(false)
const result = ref<ProductAnalysis | null>(null)

function handleImageChange(uploadFile: UploadFile) {
  const file = uploadFile.raw
  if (!file) return
  if (file.size > 20 * 1024 * 1024) {
    ElMessage.error('图片大小不能超过 20MB')
    return
  }
  imageFile.value = file
  imagePreview.value = URL.createObjectURL(file)
  result.value = null
}

function clearImage() {
  imageFile.value = null
  imagePreview.value = ''
  result.value = null
}

async function handleAnalyze() {
  if (!imageFile.value) return

  loading.value = true
  result.value = null

  try {
    const data = await analyzeProduct(imageFile.value, extraPrompt.value || undefined)
    result.value = data.analysis
    ElMessage.success('分析完成')
  } catch (e: any) {
    const msg = e?.response?.data?.detail || '分析失败，请稍后重试'
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}

function goToGenerate() {
  if (!result.value) return
  // 将关键词传递到穿搭生成页
  const keywords = result.value.keywords.join('，')
  const desc = `${result.value.style}${result.value.color}${result.value.category}`
  router.push({ path: '/outfit', query: { description: desc, keywords } })
}
</script>

<style scoped>
.product-analysis {
  max-width: 1200px;
}

.main-content {
  margin-top: 20px;
}

/* 上传区 */
.upload-area :deep(.el-upload-dragger) {
  padding: 36px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  border-radius: 12px;
  border: 2px dashed var(--border-color);
  transition: all 0.25s;
}

.upload-area :deep(.el-upload-dragger:hover) {
  border-color: #409eff;
  background: rgba(64, 158, 255, 0.04);
}

.upload-text {
  color: var(--text-regular);
  font-size: 14px;
  font-weight: 500;
}

.upload-hint {
  color: var(--text-secondary);
  font-size: 12px;
}

/* 预览区 */
.preview-area {
  position: relative;
  width: 100%;
  max-height: 400px;
  border-radius: 10px;
  overflow: hidden;
  border: 2px solid var(--border-color);
}

.preview-area img {
  width: 100%;
  max-height: 400px;
  object-fit: contain;
  display: block;
}

.preview-remove {
  position: absolute;
  top: 8px;
  right: 8px;
}

/* 加载状态 */
.loading-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-secondary);
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* 结果展示 */
.result-card :deep(.el-card__header) {
  padding: 14px 20px;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  color: var(--text-primary);
}

.section {
  margin-top: 18px;
}

.section h4 {
  margin: 0 0 10px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.analysis-tag {
  font-size: 13px;
  border-radius: 16px !important;
}
</style>
