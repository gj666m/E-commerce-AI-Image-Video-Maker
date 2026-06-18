<template>
  <div class="video-prompt-view">
    <!-- 标题区 -->
    <div class="page-header">
      <h1 class="page-title">视频转提示词</h1>
      <p class="page-desc">上传短视频，AI 自动反推出 Sora 结构化分镜格式的提示词，可直接用于 Sora / Seedance / RunwayML 等视频生成模型</p>
    </div>

    <el-row :gutter="20" class="main-content">
      <!-- 左侧：输入区 -->
      <el-col :span="10">
        <el-card>
          <el-form label-position="top">
            <!-- 提示词风格 -->
            <el-form-item label="提示词风格">
              <el-select v-model="style" style="width: 100%">
                <el-option
                  label="Sora 结构化分镜格式（适合 OpenAI Sora 等大多数模型）"
                  value="sora_structured"
                />
                <el-option label="自然语言描述（即将支持）" value="natural_language" disabled />
                <el-option label="RunwayML 格式（即将支持）" value="runwayml" disabled />
              </el-select>
            </el-form-item>

            <!-- 要分析的视频 -->
            <el-form-item label="要分析的视频" required>
              <!-- 方式一：链接解析（占位） -->
              <div class="link-input-row">
                <el-input
                  v-model="videoUrl"
                  placeholder="粘贴视频链接，自动解析"
                  clearable
                  :disabled="!!videoFile"
                >
                  <template #append>
                    <el-button :disabled="!videoUrl || !!videoFile" @click="handleParseLink">
                      解析
                    </el-button>
                  </template>
                </el-input>
              </div>
              <div class="link-hint">当前仅支持上传视频文件，链接解析功能即将上线</div>

              <!-- 分隔线 -->
              <div class="divider">
                <span>或</span>
              </div>

              <!-- 方式二：文件上传 -->
              <el-upload
                v-if="!videoFile"
                :auto-upload="false"
                :show-file-list="false"
                :on-change="handleVideoChange"
                accept=".mp4,.mov,.webm,.mkv"
                drag
                class="upload-area"
                :disabled="!!videoUrl"
              >
                <el-icon :size="40"><UploadFilled /></el-icon>
                <div class="upload-text">拖拽或点击上传</div>
                <div class="upload-hint">支持 MP4 / MOV / WebM，最大 15MB</div>
              </el-upload>
              <div v-else class="video-preview">
                <div class="video-info">
                  <el-icon :size="20"><VideoCamera /></el-icon>
                  <span class="video-name" :title="videoFile.name">{{ videoFile.name }}</span>
                  <span class="video-size">{{ formatSize(videoFile.size) }}</span>
                </div>
                <el-button
                  type="danger"
                  :icon="Close"
                  circle
                  size="small"
                  class="preview-remove"
                  @click="clearVideo"
                />
              </div>
            </el-form-item>

            <!-- 额外要求 -->
            <el-form-item label="额外要求（可选）">
              <el-input
                v-model="extraPrompt"
                type="textarea"
                :rows="2"
                placeholder="如：更简洁 / 英文输出 / 重点关注运镜 / 保留原视频的卡点节奏"
              />
            </el-form-item>

            <!-- 提交按钮 -->
            <el-form-item>
              <el-button
                type="primary"
                size="large"
                :loading="loading"
                :disabled="!videoFile"
                @click="handleSubmit"
                style="width: 100%"
              >
                {{ loading ? 'AI 分析中（最长 90 秒）...' : '生成提示词' }}
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <!-- 右侧：结果区 -->
      <el-col :span="14">
        <!-- 无结果 -->
        <el-card v-if="!result && !loading">
          <el-empty description="上传视频后点击「生成提示词」" />
        </el-card>

        <!-- 加载中 -->
        <el-card v-else-if="loading">
          <div class="loading-state">
            <el-icon :size="32" class="spin"><Loading /></el-icon>
            <p>AI 正在分析视频内容...</p>
            <p class="loading-hint">Gemini 会按 1 帧/秒采样并理解音频，预计 30-90 秒</p>
          </div>
        </el-card>

        <!-- 结果展示 -->
        <el-card v-else-if="result" class="result-card">
          <template #header>
            <div class="result-header">
              <div class="result-title">
                <el-icon><MagicStick /></el-icon>
                <span>Sora 结构化分镜提示词</span>
              </div>
              <div class="result-actions">
                <el-tag size="small" type="info">{{ formatSize(result.video_size) }}</el-tag>
                <el-tag size="small">{{ result.model_used }}</el-tag>
                <el-button type="primary" size="small" :icon="CopyDocument" @click="copyPrompt">
                  复制全部
                </el-button>
              </div>
            </div>
          </template>

          <pre class="prompt-output">{{ result.prompt }}</pre>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { UploadFile } from 'element-plus'
import {
  UploadFilled,
  VideoCamera,
  Close,
  Loading,
  CopyDocument,
  MagicStick,
} from '@element-plus/icons-vue'
import { reverseVideoPrompt, type VideoPromptResult } from '../api'
import { getErrorMessage } from '../api'

const MAX_VIDEO_SIZE = 15 * 1024 * 1024 // 15MB（与后端一致）

const style = ref('sora_structured')
const videoUrl = ref('')
const videoFile = ref<File | null>(null)
const extraPrompt = ref('')
const loading = ref(false)
const result = ref<VideoPromptResult | null>(null)

function handleParseLink() {
  ElMessage.info('链接解析功能即将上线，请先用文件上传')
}

function handleVideoChange(file: UploadFile) {
  if (!file.raw) return
  if (file.raw.size > MAX_VIDEO_SIZE) {
    ElMessage.error(`视频大小 ${formatSize(file.raw.size)} 超过 15MB 限制，请压缩或截短后重试`)
    return
  }
  videoFile.value = file.raw
  result.value = null
}

function clearVideo() {
  videoFile.value = null
}

function formatSize(bytes: number): string {
  const mb = bytes / 1024 / 1024
  if (mb < 1) return `${(bytes / 1024).toFixed(0)} KB`
  return `${mb.toFixed(2)} MB`
}

async function handleSubmit() {
  if (!videoFile.value) return
  loading.value = true
  result.value = null
  try {
    const res = await reverseVideoPrompt(videoFile.value, style.value, extraPrompt.value)
    result.value = res
    ElMessage.success('提示词生成完成')
  } catch (e) {
    ElMessage.error(getErrorMessage(e, '视频分析失败，请重试'))
  } finally {
    loading.value = false
  }
}

async function copyPrompt() {
  if (!result.value) return
  try {
    await navigator.clipboard.writeText(result.value.prompt)
    ElMessage.success('已复制到剪贴板')
  } catch {
    ElMessage.error('复制失败，请手动选择文本复制')
  }
}
</script>

<style scoped>
.video-prompt-view {
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 20px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  margin: 0 0 8px 0;
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
  align-items: stretch;
}

.link-input-row {
  width: 100%;
}

.link-hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
}

.divider {
  display: flex;
  align-items: center;
  text-align: center;
  margin: 16px 0;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.divider::before,
.divider::after {
  content: '';
  flex: 1;
  border-bottom: 1px solid var(--el-border-color);
}

.divider span {
  padding: 0 12px;
}

.upload-area {
  width: 100%;
}

.upload-area :deep(.el-upload-dragger) {
  width: 100%;
  padding: 30px 20px;
}

.upload-text {
  font-size: 14px;
  color: var(--el-text-color-regular);
  margin-top: 8px;
}

.upload-hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
}

.video-preview {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: var(--el-fill-color-light);
  border-radius: 6px;
  border: 1px solid var(--el-border-color);
}

.video-info {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  flex: 1;
}

.video-name {
  font-size: 13px;
  color: var(--el-text-color-regular);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 200px;
}

.video-size {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  flex-shrink: 0;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  gap: 8px;
}

.loading-state p {
  margin: 0;
  color: var(--el-text-color-regular);
}

.loading-hint {
  font-size: 12px !important;
  color: var(--el-text-color-secondary) !important;
}

.spin {
  animation: spin 1.2s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
}

.result-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
}

.result-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.prompt-output {
  background: var(--el-fill-color-darker, #f5f7fa);
  border-radius: 6px;
  padding: 16px;
  font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 70vh;
  overflow-y: auto;
  margin: 0;
  color: var(--el-text-color-regular);
}
</style>
