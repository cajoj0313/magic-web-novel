<template>
  <div class="review-report">
    <el-card>
      <template #header><span>审查报告</span></template>
      <el-empty v-if="!report" description="暂无审查报告" />
      <template v-else>
        <el-alert v-if="blockingCount > 0" type="error" :title="`发现 ${blockingCount} 个阻断问题，必须先修复`" show-icon />
        <el-table :data="issues" style="margin-top: 16px">
          <el-table-column label="严重度" width="100">
            <template #default="{ row }">
              <el-tag :type="severityColor(row.severity)" size="small">{{ row.severity }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="category" label="类别" width="100" />
          <el-table-column prop="description" label="描述" />
          <el-table-column prop="fix_hint" label="修复建议" show-overflow-tooltip />
          <el-table-column label="阻断" width="60">
            <template #default="{ row }">
              <el-icon v-if="row.blocking" color="red"><WarningFilled /></el-icon>
            </template>
          </el-table-column>
        </el-table>
      </template>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { WarningFilled } from '@element-plus/icons-vue'

const props = defineProps<{ report: any }>()
const issues = computed(() => props.report?.issues || props.report?.report?.issues || [])
const blockingCount = computed(() => issues.value.filter((i: any) => i.blocking).length)

function severityColor(s: string) {
  const map: Record<string, string> = { critical: 'danger', high: 'danger', medium: 'warning', low: 'info' }
  return map[s] || 'info'
}
</script>
