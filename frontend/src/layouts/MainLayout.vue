<template>
  <el-container class="main-layout">
    <el-aside width="220px">
      <div class="logo">网文创作</div>
      <el-menu :default-active="activeMenu" router>
        <el-menu-item index="/">概览</el-menu-item>
        <el-menu-item index="/chapters">章节管理</el-menu-item>
        <el-menu-item index="/plan">大纲规划</el-menu-item>
        <el-menu-item index="/settings">设定集</el-menu-item>
        <el-menu-item index="/query">查询</el-menu-item>
        <el-menu-item index="/llm-configs">模型配置</el-menu-item>
        <el-menu-item index="/learn">学习模式</el-menu-item>
      </el-menu>
    </el-aside>
    <el-main>
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const activeMenu = computed(() => route.path)
</script>

<style scoped>
.main-layout {
  min-height: 100vh;
}
.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: bold;
  border-bottom: 1px solid #eee;
}
</style>
