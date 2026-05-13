<template>
  <div class="chapter-list">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>章节列表</span>
          <span v-if="projectStore.activeProject" class="project-name">
            {{ projectStore.activeProject.title }}
          </span>
        </div>
      </template>
      <el-table :data="chapters" v-loading="loading">
        <el-table-column prop="chapter_num" label="章节" width="80" />
        <el-table-column prop="title" label="标题" />
        <el-table-column prop="word_count" label="字数" width="80" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280">
          <template #default="{ row }">
            <el-button size="small" @click="editChapter(row)">编辑</el-button>
            <el-button size="small" type="primary" @click="draftChapter(row)">起草</el-button>
            <el-button size="small" type="warning" @click="reviewChapter(row)"
              :disabled="row.status !== 'written'">审查</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card v-if="taskStore.activeTaskId" style="margin-top: 20px">
      <template #header>
        <div class="card-header">
          <span>执行进度</span>
          <div>
            <el-button size="small" @click="taskStore.pauseTask(taskStore.activeTaskId!)">暂停</el-button>
            <el-button size="small" type="primary" @click="taskStore.resumeTask(taskStore.activeTaskId!)">恢复</el-button>
            <el-button size="small" type="danger" @click="taskStore.cancelTask(taskStore.activeTaskId!)">取消</el-button>
          </div>
        </div>
      </template>
      <div v-for="(evt, i) in taskStore.taskEvents" :key="i" class="event-item">
        <el-tag size="small" :type="eventTypeColor(evt)">{{ evt.step_name || evt.type }}</el-tag>
        <span class="event-time">{{ new Date().toLocaleTimeString() }}</span>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useProjectStore } from '@/stores/project'
import { useTaskStore } from '@/stores/task'
import { apiClient } from '@/api'
import { ElMessage } from 'element-plus'

const router = useRouter()
const projectStore = useProjectStore()
const taskStore = useTaskStore()
const chapters = ref<any[]>([])
const loading = ref(false)

function statusType(status: string) {
  const map: Record<string, string> = { written: 'success', unwritten: 'info', drafting: 'warning' }
  return map[status] || 'info'
}

function statusLabel(status: string) {
  const map: Record<string, string> = { written: '已写', unwritten: '未写', drafting: '起草中' }
  return map[status] || status
}

function eventTypeColor(evt: any) {
  if (evt.step_name?.includes('失败')) return 'danger'
  if (evt.step_name?.includes('完成')) return 'success'
  return ''
}

async function loadChapters() {
  if (!projectStore.activeProjectId) return
  loading.value = true
  try {
    const data = await apiClient.chapters.list(projectStore.activeProjectId)
    chapters.value = data.chapters || []
  } catch (e: any) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}

function editChapter(row: any) {
  router.push({ name: 'chapter-editor', params: { num: String(row.chapter_num) } })
}

async function draftChapter(row: any) {
  if (!projectStore.activeProjectId) return
  try {
    const res = await apiClient.chapters.draft(projectStore.activeProjectId, row.chapter_num)
    taskStore.connectSSE(res.task_id)
    ElMessage.info(`起草任务已启动`)
  } catch (e: any) {
    ElMessage.error(e.message)
  }
}

async function reviewChapter(row: any) {
  if (!projectStore.activeProjectId) return
  try {
    const res = await apiClient.review.start(projectStore.activeProjectId, row.chapter_num)
    taskStore.connectSSE(res.task_id)
    ElMessage.info(`审查任务已启动`)
  } catch (e: any) {
    ElMessage.error(e.message)
  }
}

onMounted(() => {
  loadChapters()
})
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
.project-name { color: #999; font-size: 14px; }
.event-item { padding: 4px 0; display: flex; justify-content: space-between; }
.event-time { color: #999; font-size: 12px; }
</style>
