import axios from 'axios'

const axiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 120000,
  headers: { 'Content-Type': 'application/json' },
})

axiosInstance.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const detail = err.response?.data?.detail ?? err.message
    return Promise.reject(new Error(detail))
  },
)

// Typed wrapper: the interceptor returns res.data, so we cast to unknown then to T
async function request<T>(method: 'get' | 'post', url: string, data?: unknown): Promise<T> {
  if (method === 'get') {
    return (await axiosInstance.get(url, { params: data })) as unknown as T
  }
  return (await axiosInstance.post(url, data)) as unknown as T
}

export const apiClient = {
  projects: {
    list: () => request<any>('post', '/api/projects/list', {}),
    create: (data: { root_path: string; genre: string; target_words?: number; target_chapters?: number }) =>
      request<any>('post', '/api/projects/create', data),
    delete: (project_id: string) => request<any>('post', '/api/projects/delete', { project_id }),
    overview: (project_id: string) => request<any>('post', '/api/projects/overview', { project_id }),
    switch: (project_id: string) => request<any>('post', '/api/projects/switch', { project_id }),
  },
  chapters: {
    list: (project_id: string, volume?: number) => request<any>('post', '/api/chapters/list', { project_id, volume }),
    get: (project_id: string, chapter_num: number) =>
      request<any>('post', '/api/chapters/get', { project_id, chapter_num }),
    save: (project_id: string, chapter_num: number, content: string) =>
      request<any>('post', '/api/chapters/save', { project_id, chapter_num, content }),
    draft: (project_id: string, chapter_num: number, mode = 'default') =>
      request<any>('post', '/api/chapters/draft', { project_id, chapter_num, mode }),
  },
  review: {
    start: (project_id: string, chapter_num: number) =>
      request<any>('post', '/api/review/start', { project_id, chapter_num }),
    history: (project_id: string, chapter_num: number) =>
      request<any>('post', '/api/review/history', { project_id, chapter_num }),
    report: (project_id: string, report_id: string) =>
      request<any>('post', '/api/review/report', { project_id, report_id }),
  },
  plan: {
    getMasterOutline: (project_id: string) => request<any>('post', '/api/plan/master-outline/get', { project_id }),
    saveMasterOutline: (project_id: string, content: string) =>
      request<any>('post', '/api/plan/master-outline/save', { project_id, content }),
    startVolume: (project_id: string, volume_id: number) =>
      request<any>('post', '/api/plan/volume/start', { project_id, volume_id }),
    getVolume: (project_id: string, volume_id: number) =>
      request<any>('post', '/api/plan/volume/get', { project_id, volume_id }),
  },
  query: {
    entity: (project_id: string, entity_id: string) =>
      request<any>('post', '/api/query/entity', { project_id, entity_id }),
    powerSystem: (project_id: string) => request<any>('post', '/api/query/power-system', { project_id }),
    foreshadowing: (project_id: string) => request<any>('post', '/api/query/foreshadowing', { project_id }),
    goldenFinger: (project_id: string) => request<any>('post', '/api/query/golden-finger', { project_id }),
  },
  settings: {
    get: (project_id: string, setting_type: string) =>
      request<any>('post', '/api/settings/get', { project_id, setting_type }),
    save: (project_id: string, setting_type: string, content: string) =>
      request<any>('post', '/api/settings/save', { project_id, setting_type, content }),
  },
  llmConfigs: {
    list: () => request<any>('post', '/api/llm-configs/list', {}),
    add: (data: { name: string; provider: string; model: string; url: string; api_key: string }) =>
      request<any>('post', '/api/llm-configs/add', data),
    update: (data: Record<string, string | undefined>) =>
      request<any>('post', '/api/llm-configs/update', data),
    delete: (id: string) => request<any>('post', '/api/llm-configs/delete', { id }),
    setDefault: (id: string) => request<any>('post', '/api/llm-configs/set-default', { id }),
    test: (id: string) => request<any>('post', '/api/llm-configs/test', { id }),
  },
  learn: {
    list: (project_id: string) => request<any>('post', '/api/learn/list', { project_id }),
    add: (data: { project_id: string; pattern_type: string; description: string }) =>
      request<any>('post', '/api/learn/add', data),
  },
  tasks: {
    status: (task_id: string) => request<any>('post', '/api/tasks/status', { task_id }),
    pause: (task_id: string) => request<any>('post', '/api/tasks/pause', { task_id }),
    resume: (task_id: string) => request<any>('post', '/api/tasks/resume', { task_id }),
    cancel: (task_id: string) => request<any>('post', '/api/tasks/cancel', { task_id }),
  },
}

export default apiClient
