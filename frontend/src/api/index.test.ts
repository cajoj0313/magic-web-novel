/** API client unit tests — verifying endpoint mapping. */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

vi.mock('axios', () => {
  const mockPost = vi.fn()
  const mockGet = vi.fn()
  const mockInstance = {
    post: mockPost,
    get: mockGet,
    interceptors: {
      response: { use: vi.fn() },
    },
  }
  const create = vi.fn(() => mockInstance)
  return { default: { create, post: mockPost, get: mockGet } }
})

describe('apiClient', () => {
  let apiClient: typeof import('@/api/index').apiClient
  let mockedAxios: any

  beforeEach(async () => {
    vi.resetModules()
    const mod = await import('@/api/index')
    apiClient = mod.apiClient
    mockedAxios = (await import('axios')).default
  })

  afterEach(() => {
    mockedAxios.create().post.mockClear()
    mockedAxios.create().get.mockClear()
  })

  it('projects list calls POST /api/projects/list', async () => {
    mockedAxios.create().post.mockResolvedValue({ data: { projects: [] } })
    await apiClient.projects.list()
    expect(mockedAxios.create().post).toHaveBeenCalledWith('/api/projects/list', {})
  })

  it('chapters get passes correct params', async () => {
    mockedAxios.create().post.mockResolvedValue({ data: { content: 'test' } })
    await apiClient.chapters.get('proj-1', 5)
    expect(mockedAxios.create().post).toHaveBeenCalledWith('/api/chapters/get', {
      project_id: 'proj-1',
      chapter_num: 5,
    })
  })

  it('chapters save passes content', async () => {
    mockedAxios.create().post.mockResolvedValue({ data: { ok: true } })
    await apiClient.chapters.save('proj-1', 3, 'chapter content')
    expect(mockedAxios.create().post).toHaveBeenCalledWith('/api/chapters/save', {
      project_id: 'proj-1',
      chapter_num: 3,
      content: 'chapter content',
    })
  })

  it('llmConfigs test passes config id', async () => {
    mockedAxios.create().post.mockResolvedValue({ data: { ok: true } })
    await apiClient.llmConfigs.test('config-123')
    expect(mockedAxios.create().post).toHaveBeenCalledWith('/api/llm-configs/test', { id: 'config-123' })
  })

  it('tasks pause/resume/cancel use correct endpoints', async () => {
    mockedAxios.create().post.mockResolvedValue({ data: {} })
    await apiClient.tasks.pause('task-1')
    await apiClient.tasks.resume('task-1')
    await apiClient.tasks.cancel('task-1')

    const calls = mockedAxios.create().post.mock.calls
    expect(calls).toContainEqual(['/api/tasks/pause', { task_id: 'task-1' }])
    expect(calls).toContainEqual(['/api/tasks/resume', { task_id: 'task-1' }])
    expect(calls).toContainEqual(['/api/tasks/cancel', { task_id: 'task-1' }])
  })

  it('settings get/save pass setting_type', async () => {
    mockedAxios.create().post.mockResolvedValue({ data: { content: 'world' } })
    await apiClient.settings.get('proj-1', 'worldview')
    expect(mockedAxios.create().post).toHaveBeenCalledWith('/api/settings/get', {
      project_id: 'proj-1',
      setting_type: 'worldview',
    })

    mockedAxios.create().post.mockClear()
    mockedAxios.create().post.mockResolvedValue({ data: {} })
    await apiClient.settings.save('proj-1', 'worldview', 'new content')
    expect(mockedAxios.create().post).toHaveBeenCalledWith('/api/settings/save', {
      project_id: 'proj-1',
      setting_type: 'worldview',
      content: 'new content',
    })
  })
})
