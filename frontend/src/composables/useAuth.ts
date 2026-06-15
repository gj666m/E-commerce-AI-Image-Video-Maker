// 认证状态管理 composable
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import type { UserInfo } from '../types'
import { login as apiLogin } from '../api'

const TOKEN_KEY = 'ai-zw-token'
const USER_KEY = 'ai-zw-user'

// 全局响应式状态
const token = ref(localStorage.getItem(TOKEN_KEY) || '')
const user = ref<{ id: number; username: string; role: string } | null>(
  JSON.parse(localStorage.getItem(USER_KEY) || 'null')
)

export function useAuth() {
  const router = useRouter()

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const username = computed(() => user.value?.username || '')

  function setAuth(data: { token: string; user: UserInfo }) {
    token.value = data.token
    user.value = data.user
    localStorage.setItem(TOKEN_KEY, data.token)
    localStorage.setItem(USER_KEY, JSON.stringify(data.user))
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    router.push('/login')
  }

  async function login(username: string, password: string) {
    const data = await apiLogin(username, password)
    setAuth(data)
    return data
  }

  return {
    token,
    user,
    isLoggedIn,
    isAdmin,
    username,
    login,
    logout,
  }
}
