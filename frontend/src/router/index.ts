import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('../views/HomeView.vue'),
    },
    {
      path: '/video',
      name: 'video',
      component: () => import('../views/VideoGenView.vue'),
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
  ],
})

export default router
