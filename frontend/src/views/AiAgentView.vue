<template>
  <div class="agent-view">
    <header class="agent-header">
      <div class="title">
        <el-icon><ChatDotSquare /></el-icon>
        <h2>AI 对话助手</h2>
        <el-tooltip content="查看使用说明" placement="top">
          <el-icon class="help-icon" @click="goGuide('agent')"><QuestionFilled /></el-icon>
        </el-tooltip>
      </div>
      <el-button :icon="Plus" @click="newConversation" size="small">新对话</el-button>
    </header>

    <div ref="scrollRef" class="messages">
      <div v-if="!messages.length" class="empty">
        <el-icon :size="48"><ChatDotSquare /></el-icon>
        <h3>和 AI 对话生成电商图片</h3>
        <p>描述你想要的效果，AI 会理解需求、选择模型、自动出图。</p>
        <div class="examples">
          <el-button v-for="ex in examples" :key="ex" size="small" round @click="fillExample(ex)">{{ ex }}</el-button>
        </div>
      </div>

      <ChatMessage v-for="msg in messages" :key="msg.id" :msg="msg" />
    </div>

    <ChatInput
      :refs="uploadedRefs"
      :loading="loading"
      @send="sendMessage"
      @stop="stop"
      @upload="onUpload"
      @remove-ref="removeRef"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ChatDotSquare, Plus, QuestionFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import ChatMessage from '../components/agent/ChatMessage.vue'
import ChatInput from '../components/agent/ChatInput.vue'
import { useAgentChat } from '../composables/useAgentChat'

const router = useRouter()
function goGuide(anchor: string) {
  router.push({ path: '/user-guide', hash: `#${anchor}` })
}

const scrollRef = ref<HTMLElement | null>(null)

const { messages, loading, uploadedRefs, sendMessage, stop, newConversation, uploadImages, removeRef, restoreHistory } =
  useAgentChat({ scrollFn: scrollToBottom })

const examples = [
  '帮我生成一张红色连衣裙的小红书种草图，3:4',
  '用 Seedream 4.5 生成一张亚马逊主图，白底 1:1',
  '生成一张赛博朋克风格的卫衣宣传图',
]

function fillExample(text: string) {
  // 直接发送示例
  sendMessage(text)
}

async function onUpload(files: File[]) {
  try {
    const refs = await uploadImages(files)
    if (refs.length) ElMessage.success(`已上传 ${refs.length} 张参考图`)
  } catch (e) {
    ElMessage.error((e as Error).message || '上传失败')
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (scrollRef.value) scrollRef.value.scrollTop = scrollRef.value.scrollHeight
  })
}

onMounted(async () => {
  await restoreHistory()
  scrollToBottom()
})
</script>

<style scoped>
.agent-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}
.agent-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  border-bottom: 1px solid var(--el-border-color-light);
  background: var(--el-bg-color);
}
.title {
  display: flex;
  align-items: center;
  gap: 8px;
}
.title h2 {
  margin: 0;
  font-size: 16px;
}
.messages {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}
.empty {
  text-align: center;
  padding: 60px 20px;
  color: var(--el-text-color-secondary);
}
.empty h3 {
  margin: 12px 0 6px;
  color: var(--el-text-color-primary);
}
.empty p {
  margin: 0 0 20px;
}
.examples {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  max-width: 600px;
  margin: 0 auto;
}
</style>
