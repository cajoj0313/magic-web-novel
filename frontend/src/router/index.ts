import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: () => import('../layouts/MainLayout.vue'),
      children: [
        {
          path: '',
          name: 'home',
          component: () => import('../views/ProjectHome.vue'),
        },
        {
          path: 'chapters',
          name: 'chapters',
          component: () => import('../views/ChapterList.vue'),
        },
        {
          path: 'chapters/:num',
          name: 'chapter-editor',
          component: () => import('../views/ChapterEditor.vue'),
        },
        {
          path: 'plan',
          name: 'plan',
          component: () => import('../views/PlanView.vue'),
        },
        {
          path: 'settings',
          name: 'settings',
          component: () => import('../views/SettingView.vue'),
        },
        {
          path: 'query',
          name: 'query',
          component: () => import('../views/QueryView.vue'),
        },
        {
          path: 'llm-configs',
          name: 'llm-configs',
          component: () => import('../views/LLMConfigView.vue'),
        },
        {
          path: 'learn',
          name: 'learn',
          component: () => import('../views/LearnView.vue'),
        },
      ],
    },
  ],
})

export default router
