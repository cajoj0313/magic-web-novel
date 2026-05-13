<template>
  <div>
    <el-card>
      <template #header><span>设定集</span></template>
      <el-tabs v-model="activeType">
        <el-tab-pane v-for="t in settingTypes" :key="t.value" :label="t.label" :name="t.value" />
      </el-tabs>
      <el-button @click="loadSetting" style="margin: 12px 0">加载</el-button>
      <el-input v-model="content" type="textarea" :rows="25" />
      <div style="margin-top: 12px">
        <el-button type="primary" @click="saveSetting">保存</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useProjectStore } from '@/stores/project'
import { apiClient } from '@/api'
import { ElMessage } from 'element-plus'

const projectStore = useProjectStore()
const activeType = ref('world')
const content = ref('')
const settingTypes = [
  { label: '世界观', value: 'world' },
  { label: '力量体系', value: 'power-system' },
  { label: '主角卡', value: 'protagonist' },
  { label: '反派设计', value: 'antagonist' },
  { label: '金手指', value: 'golden-finger' },
  { label: '总纲', value: 'master-outline' },
]

async function loadSetting() {
  if (!projectStore.activeProjectId) return
  const data = await apiClient.settings.get(projectStore.activeProjectId, activeType.value)
  content.value = data.content || ''
}

async function saveSetting() {
  if (!projectStore.activeProjectId) return
  await apiClient.settings.save(projectStore.activeProjectId, activeType.value, content.value)
  ElMessage.success('保存成功')
}
</script>
