<template>
  <component :is="isLoginPage ? LoginView : MainLayout" />
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent } from 'vue'
import { useRoute } from 'vue-router'
import MainLayout from './layouts/MainLayout.vue'

const LoginView = defineAsyncComponent(() => import('./views/LoginView.vue'))

const route = useRoute()
const isLoginPage = computed(() => route.path === '/login')
</script>
