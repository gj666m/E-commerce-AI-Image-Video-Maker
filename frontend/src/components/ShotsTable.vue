<!-- 分镜表 v-model：行可编辑 / 增删（续15 工坊 video_shots 模式）
     字段对齐 backend plan_video_shots 输出格式（VideoShot interface） -->
<template>
  <div class="shots-table-wrap">
    <div class="card-header">
      <span class="header-title">分镜表（{{ modelValue.length }}）</span>
      <span class="header-hint">改字段后下方 prompt 实时本地拼装；真实提交走后端权威拼装</span>
    </div>

    <div v-if="modelValue.length === 0" class="empty-hint">
      暂无分镜，请在「智能创意」时输入主题 + 设置时长，让 AI 帮你规划
    </div>

    <div v-for="(shot, idx) in modelValue" :key="idx" class="shot-row">
      <div class="shot-row-head">
        <span class="shot-no">分镜 {{ idx + 1 }}</span>
        <span class="shot-time">{{ shot.start_time }}-{{ shot.end_time }}s · {{ shot.duration }}s</span>
        <el-tag size="small" :type="purposeTagType(shot.purpose)" effect="plain">{{ shot.purpose }}</el-tag>
        <el-button
          class="shot-delete"
          size="small"
          type="danger"
          plain
          circle
          @click="deleteShot(idx)"
        >
          <el-icon><Close /></el-icon>
        </el-button>
      </div>
      <el-row :gutter="8">
        <el-col :span="6">
          <div class="cell">
            <label>用途</label>
            <el-select :model-value="shot.purpose" size="small" @update:model-value="update(idx, 'purpose', $event)">
              <el-option value="Hook" label="Hook（钩子）" />
              <el-option value="Detail" label="Detail（细节）" />
              <el-option value="Recall" label="Recall（回响）" />
            </el-select>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="cell">
            <label>时段</label>
            <el-input
              :model-value="`${shot.start_time}-${shot.end_time}`"
              size="small"
              placeholder="0-5"
              @update:model-value="updateRange(idx, $event)"
            />
          </div>
        </el-col>
        <el-col :span="6">
          <div class="cell">
            <label>时长（秒）</label>
            <el-input-number
              :model-value="shot.duration"
              size="small"
              :min="1"
              :max="15"
              controls-position="right"
              style="width: 100%"
              @update:model-value="update(idx, 'duration', Number($event) || 1)"
            />
          </div>
        </el-col>
        <el-col :span="6">
          <div class="cell">
            <label>视觉风格</label>
            <el-input
              :model-value="shot.visual_style"
              size="small"
              placeholder="整体视觉风格关键词"
              @update:model-value="update(idx, 'visual_style', $event)"
            />
          </div>
        </el-col>
      </el-row>
      <el-row :gutter="8">
        <el-col :span="12">
          <div class="cell">
            <label>人物动作</label>
            <el-input
              :model-value="shot.action"
              type="textarea"
              :rows="2"
              placeholder="模特/主体的具体动作描述"
              @update:model-value="update(idx, 'action', $event)"
            />
          </div>
        </el-col>
        <el-col :span="12">
          <div class="cell">
            <label>镜头语言</label>
            <el-input
              :model-value="shot.camera"
              type="textarea"
              :rows="2"
              placeholder="景别 + 运镜，如 近景 / 缓慢推近"
              @update:model-value="update(idx, 'camera', $event)"
            />
          </div>
        </el-col>
      </el-row>
      <el-row :gutter="8">
        <el-col :span="12">
          <div class="cell">
            <label>视觉焦点</label>
            <el-input
              :model-value="shot.focus"
              type="textarea"
              :rows="2"
              placeholder="画面视觉焦点（服装细节/配饰/动作）"
              @update:model-value="update(idx, 'focus', $event)"
            />
          </div>
        </el-col>
        <el-col :span="12">
          <div class="cell">
            <label>服装强调</label>
            <el-input
              :model-value="shot.garment_focus"
              type="textarea"
              :rows="2"
              placeholder="本镜要突出强调的服装细节"
              @update:model-value="update(idx, 'garment_focus', $event)"
            />
          </div>
        </el-col>
      </el-row>
    </div>

    <el-button class="add-shot" plain size="small" @click="addShot">
      <el-icon style="margin-right: 4px"><Plus /></el-icon>
      新增分镜
    </el-button>
  </div>
</template>

<script setup lang="ts">
import { Close, Plus } from '@element-plus/icons-vue'
import type { VideoShot } from '../api'

const props = defineProps<{
  modelValue: VideoShot[]
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: VideoShot[]): void
}>()

function purposeTagType(p: string): 'primary' | 'success' | 'warning' {
  if (p === 'Hook') return 'primary'
  if (p === 'Detail') return 'success'
  return 'warning'
}

function emitNext(next: VideoShot[]) {
  emit('update:modelValue', next)
}

function update<K extends keyof VideoShot>(idx: number, key: K, value: VideoShot[K]) {
  const next = props.modelValue.slice()
  next[idx] = { ...next[idx], [key]: value }
  emitNext(next)
}

function updateRange(idx: number, raw: string) {
  // 解析 "0-5" / "0~5" / "0,5" 格式
  const m = /^(\d+(?:\.\d+)?)[\-~,\s]+(\d+(?:\.\d+)?)$/.exec(raw.trim())
  const next = props.modelValue.slice()
  if (m) {
    const start = parseFloat(m[1])
    const end = parseFloat(m[2])
    next[idx] = {
      ...next[idx],
      start_time: start,
      end_time: end,
      duration: Math.max(1, Math.round(end - start)),
    }
  } else {
    // 解析失败时不动 start_time/end_time，仅保留输入文本（用户继续输）
    return
  }
  emitNext(next)
}

function deleteShot(idx: number) {
  const next = props.modelValue.slice()
  next.splice(idx, 1)
  // 重新分配 index
  next.forEach((s, i) => (s.index = i + 1))
  emitNext(next)
}

function addShot() {
  const last = props.modelValue[props.modelValue.length - 1]
  const start = last ? last.end_time : 0
  const dur = 4
  const newShot: VideoShot = {
    index: props.modelValue.length + 1,
    start_time: start,
    end_time: start + dur,
    duration: dur,
    purpose: 'Detail',
    action: '',
    camera: '',
    focus: '',
    garment_focus: '',
    visual_style: '',
  }
  emitNext([...props.modelValue, newShot])
}
</script>

<style scoped>
.shots-table-wrap {
  width: 100%;
}
.card-header {
  display: flex; align-items: baseline; gap: 10px;
  margin-bottom: 8px;
}
.header-title {
  font-weight: 600; font-size: 14px; color: #303133;
}
.header-hint {
  font-size: 12px; color: #909399;
}
.empty-hint {
  color: #909399; font-size: 13px; padding: 12px;
  background: #fafafa; border-radius: 4px;
  text-align: center;
}
.shot-row {
  padding: 10px;
  background: #fbfcfd;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  margin-bottom: 8px;
}
.shot-row-head {
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 8px;
}
.shot-no {
  font-weight: 600; color: #303133; font-size: 13px;
}
.shot-time {
  color: #909399; font-size: 12px;
}
.shot-delete {
  margin-left: auto;
}
.cell {
  display: flex; flex-direction: column; gap: 2px;
  padding: 0 2px;
}
.cell label {
  font-size: 11px; color: #909399; padding-left: 2px;
}
.cell :deep(.el-textarea__inner),
.cell :deep(.el-input__inner) {
  font-size: 12px;
}
.add-shot {
  width: 100%;
  border-style: dashed;
}
</style>
