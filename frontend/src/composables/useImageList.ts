import { ref, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import type { UploadFile } from 'element-plus'

/**
 * 管理一组图片文件 + 对应的 Blob URL 预览
 * 自动在组件卸载时释放所有 Blob URL
 */
export function useImageList(maxCount: number, label = '图片') {
  const files = ref<File[]>([])
  const previews = ref<string[]>([])

  onUnmounted(() => {
    previews.value.forEach(url => URL.revokeObjectURL(url))
  })

  function add(uploadFile: UploadFile) {
    const file = uploadFile.raw
    if (!file) return
    if (files.value.length >= maxCount) {
      ElMessage.warning(`最多上传 ${maxCount} 张${label}`)
      return
    }
    files.value.push(file)
    previews.value.push(URL.createObjectURL(file))
  }

  function addFile(file: File) {
    if (files.value.length >= maxCount) {
      ElMessage.warning(`最多上传 ${maxCount} 张${label}`)
      return
    }
    files.value.push(file)
    previews.value.push(URL.createObjectURL(file))
  }

  function remove(index: number) {
    URL.revokeObjectURL(previews.value[index])
    files.value.splice(index, 1)
    previews.value.splice(index, 1)
  }

  function clear() {
    previews.value.forEach(url => URL.revokeObjectURL(url))
    files.value = []
    previews.value = []
  }

  return { files, previews, add, addFile, remove, clear }
}
