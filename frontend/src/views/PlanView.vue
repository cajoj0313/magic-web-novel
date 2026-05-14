<template>
  <div>
    <el-card>
      <template #header>
        <div class="card-header">
          <span>大纲规划</span>
        </div>
      </template>
      <el-tabs v-model="activeTab">
        <el-tab-pane label="总纲" name="master">
          <el-button @click="loadMasterOutline" style="margin-bottom: 12px">加载总纲</el-button>
          <el-input v-model="masterContent" type="textarea" :rows="20" placeholder="总纲内容..." />
          <div style="margin-top: 12px">
            <el-button type="primary" @click="saveMasterOutline">保存</el-button>
          </div>
        </el-tab-pane>
        <el-tab-pane label="卷规划" name="volume">
          <el-form inline>
            <el-form-item label="卷号">
              <el-input-number v-model="volumeId" :min="1" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="loadVolume">加载</el-button>
            </el-form-item>
          </el-form>
          <el-descriptions :column="2" border v-if="volumeData">
            <el-descriptions-item label="节拍表">{{ volumeData.beat_sheet ? '已生成' : '未生成' }}</el-descriptions-item>
            <el-descriptions-item label="时间线">{{ volumeData.timeline ? '已生成' : '未生成' }}</el-descriptions-item>
          </el-descriptions>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useProjectStore } from '@/stores/project'
import { apiClient } from '@/api'
import { ElMessage } from 'element-plus'

const projectStore = useProjectStore()
const activeTab = ref('master')
const masterContent = ref('')
const volumeId = ref(1)
const volumeData = ref<any>(null)

async function loadMasterOutline() {
  if (!projectStore.activeProjectId) return
  const data = await apiClient.plan.getMasterOutline(projectStore.activeProjectId)
  masterContent.value = data.content || ''
}

async function saveMasterOutline() {
  if (!projectStore.activeProjectId) return
  await apiClient.plan.saveMasterOutline(projectStore.activeProjectId, masterContent.value)
  ElMessage.success('保存成功')
}

async function loadVolume() {
  if (!projectStore.activeProjectId) return
  volumeData.value = await apiClient.plan.getVolume(projectStore.activeProjectId, volumeId.value)
}
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
