import { ref, watchEffect } from 'vue'

type Theme = 'light' | 'dark'

const STORAGE_KEY = 'ai-zw-theme'

const theme = ref<Theme>((localStorage.getItem(STORAGE_KEY) as Theme) || 'light')

function applyTheme(t: Theme) {
  if (t === 'dark') {
    document.documentElement.classList.add('dark')
  } else {
    document.documentElement.classList.remove('dark')
  }
}

// 初始化时立即应用
applyTheme(theme.value)

export function useTheme() {
  const isDark = ref(theme.value === 'dark')

  function toggleTheme() {
    theme.value = theme.value === 'dark' ? 'light' : 'dark'
    isDark.value = theme.value === 'dark'
    localStorage.setItem(STORAGE_KEY, theme.value)
    applyTheme(theme.value)
  }

  watchEffect(() => {
    isDark.value = theme.value === 'dark'
  })

  return { isDark, toggleTheme }
}
