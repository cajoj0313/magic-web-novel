<template>
  <div>
    <el-card>
      <template #header><span>学习模式</span></template>
      <el-form :model="form" label-width="100px" style="max-width: 600px">
        <el-form-item label="模式类型">
          <el-select v-model="form.pattern_type">
            <el-option label="hook" value="hook" />
            <el-option label="pacing" value="pacing" />
            <el-option label="dialogue" value="dialogue" />
            <el-option label="payoff" value="payoff" />
            <el-option label="emotion" value="emotion" />
            <el-option label="format" value="format" />
            <el-option label="other" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="4" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleAdd">添加</el-button>
        </el-form-item>
      </el-form>
      <el-divider>已学习模式</el-divider>
      <el-empty v-if="patterns.length === 0" description="暂无学习记录" />
      <el-timeline v-else>
        <el-timeline-item v-for="(p, i) in patterns" :key="i" :timestamp="p.learned_at">
          <el-tag size="small">{{ p.pattern_type }}</el-tag>
          <span style="margin-left: 8px">{{ p.description }}</span>
        </el-timeline-item>
      </el-timeline>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useProjectStore } from '@/stores/project'
import { apiClient } from '@/api'
import { ElMessage } from 'element-plus'

const projectStore = useProjectStore()
const patterns = ref<any[]>([])
const form = ref({ pattern_type: 'other', description: '' })

async function loadPatterns() {
  if (!projectStore.activeProjectId) return
  const data = await apiClient.learn.list(projectStore.activeProjectId)
  patterns.value = data.patterns || []
}

async function handleAdd() {
  if (!projectStore.activeProjectId) return
  const res = await apiClient.learn.add({ ...form.value, project_id: projectStore.activeProjectId })
  if (res.duplicated) {
    ElMessage.warning('该模式已存在（重复）')
  } else {
    ElMessage.success('添加成功')
  }
  await loadPatterns()
}

onMounted(() => { loadPatterns() })
</script>
