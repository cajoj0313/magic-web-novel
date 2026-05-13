<template>
  <div class="execution-progress">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>执行进度</span>
          <el-tag :type="statusColor">{{ taskStore.taskStatus }}</el-tag>
        </div>
      </template>
      <el-steps :active="currentStep" finish-status="success" align-center>
        <el-step v-for="i in totalSteps" :key="i" :title="stepName(i - 1)" />
      </el-steps>
      <div class="event-log">
        <div v-for="(evt, i) in taskStore.taskEvents" :key="i" class="event-item">
          <el-tag size="small" :type="eventTypeColor(evt)">{{ evt.step_name || evt.type }}</el-tag>
          <span class="event-detail">{{ JSON.stringify(evt) }}</span>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useTaskStore } from '@/stores/task'

const taskStore = useTaskStore()
const totalSteps = 6
const stepNames = ['上下文构建', '正文起草', '审查', '润色', '事实提取', '提交落库']

const currentStep = computed(() => {
  const events = taskStore.taskEvents
  for (let i = events.length - 1; i >= 0; i--) {
    if (events[i].step_number !== undefined) return events[i].step_number
  }
  return 0
})

function stepName(idx: number) {
  return stepNames[idx] || `步骤 ${idx + 1}`
}

const statusColor = computed(() => {
  const map: Record<string, string> = { completed: 'success', failed: 'danger', cancelled: 'warning' }
  return map[taskStore.taskStatus] || ''
})

function eventTypeColor(evt: any) {
  if (evt.type?.includes('failed')) return 'danger'
  if (evt.type?.includes('complete')) return 'success'
  return ''
}
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
.event-log { margin-top: 16px; max-height: 300px; overflow-y: auto; }
.event-item { padding: 4px 0; }
.event-detail { margin-left: 8px; font-size: 12px; color: #999; }
</style>
