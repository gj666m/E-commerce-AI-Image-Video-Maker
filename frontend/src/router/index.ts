import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      name: 'home',
      component: () => import('../views/HomeView.vue'),
    },
    {
      path: '/agent',
      name: 'agent',
      component: () => import('../views/AiAgentView.vue'),
    },
    {
      path: '/quick-image',
      name: 'quick-image',
      component: () => import('../views/QuickImageView.vue'),
    },
    {
      path: '/video',
      name: 'video',
      component: () => import('../views/VideoGenView.vue'),
    },
    {
      path: '/video-prompt',
      name: 'video-prompt',
      component: () => import('../views/VideoPromptView.vue'),
    },
    {
      path: '/replicate',
      name: 'replicate',
      component: () => import('../views/ViralReplicateView.vue'),
    },
    {
      path: '/tiktok-script',
      name: 'tiktok-script',
      component: () => import('../views/TiktokScriptView.vue'),
    },
    {
      path: '/outfit-scrape',
      name: 'outfit-scrape',
      component: () => import('../views/OutfitScraperView.vue'),
    },
    {
      path: '/video-shots',
      name: 'video-shots',
      component: () => import('../views/VideoShotView.vue'),
    },
    {
      path: '/model-gen',
      name: 'model-gen',
      component: () => import('../views/ModelGenView.vue'),
    },
    {
      path: '/outfit',
      name: 'outfit',
      component: () => import('../views/OutfitGenView.vue'),
    },
    {
      path: '/analysis',
      name: 'analysis',
      component: () => import('../views/ProductAnalysisView.vue'),
    },
    {
      path: '/seed-grass',
      name: 'seed-grass',
      component: () => import('../views/SeedGrassView.vue'),
    },
    {
      path: '/product-image',
      name: 'product-image',
      component: () => import('../views/ProductImageView.vue'),
    },
    {
      path: '/history',
      name: 'history',
      component: () => import('../views/HistoryView.vue'),
    },
    {
      path: '/video-history',
      name: 'video-history',
      component: () => import('../views/VideoHistoryView.vue'),
    },
    {
      path: '/prompt-library',
      name: 'prompt-library',
      component: () => import('../views/PromptLibraryView.vue'),
    },
    {
      path: '/prompt-workshop',
      name: 'prompt-workshop',
      component: () => import('../views/PromptWorkshopView.vue'),
    },
    {
      path: '/admin/users',
      name: 'admin-users',
      component: () => import('../views/AdminUsersView.vue'),
      meta: { admin: true },
    },
    {
      path: '/user-guide',
      name: 'user-guide',
      component: () => import('../views/UserGuideView.vue'),
    },
  ],
})

// 路由守卫：未登录跳转登录页，非管理员拦截
router.beforeEach((to) => {
  const token = localStorage.getItem('ai-zw-token')
  const userStr = localStorage.getItem('ai-zw-user')

  // 公开页面不需要鉴权
  if (to.meta.public) return true

  if (!token || !userStr) {
    return { name: 'login' }
  }

  // 管理员页面检查角色
  if (to.meta.admin) {
    try {
      const user = JSON.parse(userStr)
      if (user.role !== 'admin') return { name: 'home' }
    } catch {
      return { name: 'login' }
    }
  }

  return true
})

export default router
