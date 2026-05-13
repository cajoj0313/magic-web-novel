<template>
  <div class="project-home">
    <el-row :gutter="20">
      <el-col :span="16">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>项目列表</span>
              <el-button type="primary" @click="showCreateDialog = true">新建项目</el-button>
            </div>
          </template>
          <el-table :data="projectStore.projects" v-loading="projectStore.loading">
            <el-table-column prop="title" label="书名" />
            <el-table-column prop="genre" label="题材" width="100" />
            <el-table-column prop="progress" label="字数" width="100" />
            <el-table-column prop="last_updated" label="最后更新" width="180" />
            <el-table-column label="操作" width="150">
              <template #default="{ row }">
                <el-button size="small" @click="projectStore.switchProject(row.id); loadOverview(row.id)">切换</el-button>
                <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!projectStore.loading && projectStore.projects.length === 0" description="暂无项目" />
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <template #header><span>项目概览</span></template>
          <template v-if="overview">
            <el-descriptions :column="1" border>
              <el-descriptions-item label="书名">{{ overview.title }}</el-descriptions-item>
              <el-descriptions-item label="题材">{{ overview.genre }}</el-descriptions-item>
              <el-descriptions-item label="已写章节">{{ overview.current_chapter }} / {{ overview.total_chapters }}</el-descriptions-item>
              <el-descriptions-item label="总字数">{{ overview.total_words }}</el-descriptions-item>
              <el-descriptions-item label="审查状态">{{ overview.review_status }}</el-descriptions-item>
            </el-descriptions>
          </template>
          <el-empty v-else description="请选择或创建项目" />
        </el-card>
      </el-col>
    </el-row>

    <!-- Create Project Dialog -->
    <el-dialog v-model="showCreateDialog" title="新建项目" width="500px">
      <el-form :model="createForm" label-width="100px">
        <el-form-item label="项目根目录">
          <el-input v-model="createForm.root_path" placeholder="/path/to/project" />
        </el-form-item>
        <el-form-item label="题材">
          <el-select v-model="createForm.genre" placeholder="选择题材">
            <el-option label="玄幻" value="玄幻" />
            <el-option label="都市" value="都市" />
            <el-option label="仙侠" value="仙侠" />
            <el-option label="科幻" value="科幻" />
            <el-option label="历史" value="历史" />
            <el-option label="悬疑" value="悬疑" />
            <el-option label="古言" value="古言" />
            <el-option label="现言" value="现言" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标章节">
          <el-input-number v-model="createForm.target_chapters" :min="0" />
        </el-form-item>
        <el-form-item label="目标字数">
          <el-input-number v-model="createForm.target_words" :min="0" :step="10000" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useProjectStore } from '@/stores/project'
import { ElMessage, ElMessageBox } from 'element-plus'

const projectStore = useProjectStore()
const showCreateDialog = ref(false)
const overview = ref<any>(null)
const createForm = ref({
  root_path: '',
  genre: '玄幻',
  target_words: 0,
  target_chapters: 0,
})

async function loadOverview(id: string) {
  try {
    overview.value = await projectStore.getOverview(id)
  } catch {
    overview.value = null
  }
}

async function handleCreate() {
  try {
    await projectStore.createProject(createForm.value)
    showCreateDialog.value = false
    ElMessage.success('项目创建成功')
  } catch (e: any) {
    ElMessage.error(e.message)
  }
}

async function handleDelete(row: any) {
  try {
    await ElMessageBox.confirm(`确定删除项目「${row.title}」吗？（不会删除文件）`, '确认', { type: 'warning' })
    await projectStore.deleteProject(row.id)
    ElMessage.success('已删除')
  } catch {
    // cancelled
  }
}

onMounted(() => {
  projectStore.fetchProjects()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
