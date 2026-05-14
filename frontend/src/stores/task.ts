import { defineStore } from 'pinia'
import { ref } from 'vue'
import { apiClient } from '@/api'

export interface TaskEvent {
  task_id: string
  step_number?: number
  step_name?: string
  type?: string
  status?: string
  progress?: { current_step: number; total_steps: number; step_name: string; elapsed_ms: number }
  preview?: unknown
}

export const useTaskStore = defineStore('task', () => {
  const activeTaskId = ref<string | null>(null)
  const taskEvents = ref<TaskEvent[]>([])
  const taskStatus = ref<string>('idle')

  function connectSSE(taskId: string): EventSource {
    activeTaskId.value = taskId
    taskEvents.value = []
    taskStatus.value = 'running'
    const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
    const es = new EventSource(`${baseURL}/api/events?task_id=${taskId}`)

    es.addEventListener('step_start', (e) => {
      taskEvents.value.push(JSON.parse(e.data))
    })
    es.addEventListener('step_progress', (e) => {
      taskEvents.value.push(JSON.parse(e.data))
    })
    es.addEventListener('step_complete', (e) => {
      taskEvents.value.push(JSON.parse(e.data))
    })
    es.addEventListener('step_failed', (e) => {
      taskEvents.value.push(JSON.parse(e.data))
    })
    es.addEventListener('task_complete', () => {
      taskStatus.value = 'completed'
      es.close()
    })
    es.addEventListener('task_failed', () => {
      taskStatus.value = 'failed'
      es.close()
    })
    es.addEventListener('task_cancelled', () => {
      taskStatus.value = 'cancelled'
      es.close()
    })
    es.onerror = () => {
      es.close()
    }
    return es
  }

  function pauseTask(taskId: string) {
    return apiClient.tasks.pause(taskId)
  }

  function resumeTask(taskId: string) {
    return apiClient.tasks.resume(taskId)
  }

  function cancelTask(taskId: string) {
    return apiClient.tasks.cancel(taskId)
  }

  return { activeTaskId, taskEvents, taskStatus, connectSSE, pauseTask, resumeTask, cancelTask }
})
