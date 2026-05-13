import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { apiClient } from '@/api'

interface ProjectInfo {
  id: string
  title: string
  genre: string
  progress: number
  last_updated: string | null
}

export const useProjectStore = defineStore('project', () => {
  const projects = ref<ProjectInfo[]>([])
  const activeProjectId = ref<string | null>(null)
  const loading = ref(false)

  const activeProject = computed(() =>
    projects.value.find((p) => p.id === activeProjectId.value) ?? null,
  )

  async function fetchProjects() {
    loading.value = true
    try {
      const data = await apiClient.projects.list()
      projects.value = data.projects || []
      activeProjectId.value = data.active_project_id ?? null
    } finally {
      loading.value = false
    }
  }

  async function createProject(data: { root_path: string; genre: string; target_words?: number; target_chapters?: number }) {
    const result = await apiClient.projects.create(data)
    await fetchProjects()
    activeProjectId.value = result.id
    return result
  }

  async function switchProject(id: string) {
    await apiClient.projects.switch(id)
    activeProjectId.value = id
  }

  async function deleteProject(id: string) {
    await apiClient.projects.delete(id)
    await fetchProjects()
    if (activeProjectId.value === id) {
      activeProjectId.value = projects.value[0]?.id ?? null
    }
  }

  async function getOverview(id: string) {
    return apiClient.projects.overview(id)
  }

  return { projects, activeProjectId, activeProject, loading, fetchProjects, createProject, switchProject, deleteProject, getOverview }
})
