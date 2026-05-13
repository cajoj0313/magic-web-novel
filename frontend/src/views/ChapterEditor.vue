<template>
  <div class="chapter-editor">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>第 {{ chapterNum }} 章 — {{ title }}</span>
          <div>
            <span class="word-count">字数: {{ wordCount }}</span>
            <el-button type="primary" @click="handleSave">保存</el-button>
          </div>
        </div>
      </template>
      <el-input
        v-model="content"
        type="textarea"
        :rows="30"
        placeholder="在此编辑章节正文..."
        resize="none"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useProjectStore } from '@/stores/project'
import { apiClient } from '@/api'
import { ElMessage } from 'element-plus'

const route = useRoute()
const projectStore = useProjectStore()
const content = ref('')
const title = ref('')
const wordCount = ref(0)

const chapterNum = computed(() => Number(route.params.num) || 1)

async function loadChapter() {
  if (!projectStore.activeProjectId) return
  try {
    const data = await apiClient.chapters.get(projectStore.activeProjectId, chapterNum.value)
    content.value = data.content || ''
    title.value = data.title || '未命名'
    wordCount.value = data.word_count || 0
  } catch (e: any) {
    ElMessage.error(`加载失败: ${e.message}`)
  }
}

async function handleSave() {
  if (!projectStore.activeProjectId) return
  try {
    const res = await apiClient.chapters.save(projectStore.activeProjectId, chapterNum.value, content.value)
    wordCount.value = res.word_count
    ElMessage.success('保存成功')
  } catch (e: any) {
    ElMessage.error(`保存失败: ${e.message}`)
  }
}

onMounted(() => {
  loadChapter()
})
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
.word-count { color: #999; margin-right: 12px; }
</style>
