<template>
  <div>
    <el-card>
      <template #header>
        <div class="card-header">
          <span>模型配置</span>
          <el-button type="primary" @click="showAdd = true">添加模型</el-button>
        </div>
      </template>
      <el-table :data="configs" v-loading="loading">
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="provider" label="供应商" width="120" />
        <el-table-column prop="model" label="模型" />
        <el-table-column prop="url" label="URL" show-overflow-tooltip />
        <el-table-column label="默认" width="60">
          <template #default="{ row }">
            <el-tag v-if="row.is_default" size="small">默认</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220">
          <template #default="{ row }">
            <el-button size="small" @click="testConn(row)">测试</el-button>
            <el-button size="small" @click="setDefault(row)">设为默认</el-button>
            <el-button size="small" type="danger" @click="deleteConfig(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="showAdd" title="添加模型" width="500px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="供应商">
          <el-select v-model="form.provider">
            <el-option label="Anthropic" value="anthropic" />
            <el-option label="OpenAI兼容" value="openai_compatible" />
          </el-select>
        </el-form-item>
        <el-form-item label="模型"><el-input v-model="form.model" /></el-form-item>
        <el-form-item label="URL"><el-input v-model="form.url" /></el-form-item>
        <el-form-item label="API Key"><el-input v-model="form.api_key" type="password" show-password /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAdd = false">取消</el-button>
        <el-button type="primary" @click="handleAdd">添加</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { apiClient } from '@/api'
import { ElMessage } from 'element-plus'

const configs = ref<any[]>([])
const loading = ref(false)
const showAdd = ref(false)
const form = ref({ name: '', provider: 'anthropic', model: '', url: '', api_key: '' })

async function loadConfigs() {
  loading.value = true
  try {
    const data = await apiClient.llmConfigs.list()
    configs.value = data.configs || []
  } catch (e: any) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}

async function handleAdd() {
  try {
    await apiClient.llmConfigs.add(form.value)
    showAdd.value = false
    ElMessage.success('添加成功')
    await loadConfigs()
  } catch (e: any) {
    ElMessage.error(e.message)
  }
}

async function testConn(row: any) {
  const res = await apiClient.llmConfigs.test(row.id)
  res.ok ? ElMessage.success(`连接成功 (${res.latency_ms}ms)`) : ElMessage.error(res.error)
}

async function setDefault(row: any) {
  await apiClient.llmConfigs.setDefault(row.id)
  ElMessage.success('已设为默认')
  await loadConfigs()
}

async function deleteConfig(row: any) {
  await apiClient.llmConfigs.delete(row.id)
  ElMessage.success('已删除')
  await loadConfigs()
}

onMounted(() => { loadConfigs() })
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
