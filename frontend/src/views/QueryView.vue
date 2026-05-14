<template>
  <div>
    <el-card>
      <template #header><span>设定查询</span></template>
      <el-space wrap>
        <el-button @click="queryType('powerSystem')">力量体系</el-button>
        <el-button @click="queryType('foreshadowing')">伏笔</el-button>
        <el-button @click="queryType('goldenFinger')">金手指</el-button>
      </el-space>
      <div v-if="result" style="margin-top: 20px">
        <pre class="result-block">{{ result }}</pre>
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
const result = ref<string | null>(null)

async function queryType(type: string) {
  if (!projectStore.activeProjectId) return
  try {
    let data: any
    if (type === 'powerSystem') data = await apiClient.query.powerSystem(projectStore.activeProjectId)
    else if (type === 'foreshadowing') data = await apiClient.query.foreshadowing(projectStore.activeProjectId)
    else if (type === 'goldenFinger') data = await apiClient.query.goldenFinger(projectStore.activeProjectId)
    result.value = typeof data === 'string' ? data : JSON.stringify(data, null, 2)
  } catch (e: any) {
    ElMessage.error(e.message)
  }
}
</script>

<style scoped>
.result-block {
  background: #f5f5f5;
  padding: 16px;
  border-radius: 4px;
  white-space: pre-wrap;
  font-family: inherit;
}
</style>
