/** Project store unit tests. */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

// Mock the API client
vi.mock('@/api', () => ({
  apiClient: {
    projects: {
      list: vi.fn(),
      create: vi.fn(),
      switch: vi.fn(),
      delete: vi.fn(),
      overview: vi.fn(),
    },
    chapters: { list: vi.fn() },
    review: { start: vi.fn(), history: vi.fn(), report: vi.fn() },
    plan: { getMasterOutline: vi.fn(), saveMasterOutline: vi.fn(), startVolume: vi.fn(), getVolume: vi.fn() },
    query: { entity: vi.fn(), powerSystem: vi.fn(), foreshadowing: vi.fn(), goldenFinger: vi.fn() },
    settings: { get: vi.fn(), save: vi.fn() },
    llmConfigs: { list: vi.fn(), add: vi.fn(), update: vi.fn(), delete: vi.fn(), setDefault: vi.fn(), test: vi.fn() },
    learn: { list: vi.fn(), add: vi.fn() },
    tasks: { status: vi.fn(), pause: vi.fn(), resume: vi.fn(), cancel: vi.fn() },
  },
}))

describe('useProjectStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('initial state has empty projects', async () => {
    const { useProjectStore } = await import('@/stores/project')
    const store = useProjectStore()
    expect(store.projects).toEqual([])
    expect(store.activeProjectId).toBeNull()
    expect(store.activeProject).toBeNull()
  })

  it('fetchProjects loads from API', async () => {
    const { useProjectStore } = await import('@/stores/project')
    const { apiClient } = await import('@/api')

    vi.mocked(apiClient.projects.list).mockResolvedValue({
      projects: [
        { id: 'p1', title: '小说 A', genre: '玄幻', progress: 10 },
        { id: 'p2', title: '小说 B', genre: '都市', progress: 25 },
      ],
    })

    const store = useProjectStore()
    await store.fetchProjects()

    expect(store.projects).toHaveLength(2)
    expect(store.projects[0].title).toBe('小说 A')
  })

  it('createProject adds and switches to new project', async () => {
    const { useProjectStore } = await import('@/stores/project')
    const { apiClient } = await import('@/api')

    vi.mocked(apiClient.projects.create).mockResolvedValue({ id: 'new-proj' })
    vi.mocked(apiClient.projects.list).mockResolvedValue({ projects: [] })

    const store = useProjectStore()
    await store.createProject({
      root_path: '/tmp/test',
      genre: '玄幻',
      target_words: 300000,
      target_chapters: 200,
    })

    expect(apiClient.projects.create).toHaveBeenCalledWith({
      root_path: '/tmp/test',
      genre: '玄幻',
      target_words: 300000,
      target_chapters: 200,
    })
    expect(store.activeProjectId).toBe('new-proj')
  })

  it('switchProject updates activeProjectId', async () => {
    const { useProjectStore } = await import('@/stores/project')
    const { apiClient } = await import('@/api')

    vi.mocked(apiClient.projects.switch).mockResolvedValue({})

    const store = useProjectStore()
    store.projects = [
      { id: 'p1', title: 'A', genre: '玄幻', progress: 0, last_updated: null },
      { id: 'p2', title: 'B', genre: '都市', progress: 0, last_updated: null },
    ]
    await store.switchProject('p2')

    expect(store.activeProjectId).toBe('p2')
    expect(store.activeProject!.title).toBe('B')
  })

  it('deleteProject removes from list and reselects', async () => {
    const { useProjectStore } = await import('@/stores/project')
    const { apiClient } = await import('@/api')

    vi.mocked(apiClient.projects.delete).mockResolvedValue({})
    vi.mocked(apiClient.projects.list).mockResolvedValue({
      projects: [{ id: 'p2', title: 'B', genre: '都市', progress: 0 }],
      active_project_id: 'p2',
    })

    const store = useProjectStore()
    store.projects = [
      { id: 'p1', title: 'A', genre: '玄幻', progress: 0, last_updated: null },
      { id: 'p2', title: 'B', genre: '都市', progress: 0, last_updated: null },
    ]
    store.activeProjectId = 'p1'

    await store.deleteProject('p1')

    expect(store.projects).toHaveLength(1)
    expect(store.activeProjectId).toBe('p2')
  })

  it('getOverview calls API with project_id', async () => {
    const { useProjectStore } = await import('@/stores/project')
    const { apiClient } = await import('@/api')

    vi.mocked(apiClient.projects.overview).mockResolvedValue({ chapters_done: 5 })

    const store = useProjectStore()
    const result = await store.getOverview('proj-1')

    expect(apiClient.projects.overview).toHaveBeenCalledWith('proj-1')
    expect(result).toEqual({ chapters_done: 5 })
  })

  it('fetchProjects sets loading state', async () => {
    const { useProjectStore } = await import('@/stores/project')
    const { apiClient } = await import('@/api')

    let resolveList: (v: any) => void
    vi.mocked(apiClient.projects.list).mockReturnValue(
      new Promise((r) => { resolveList = r }),
    )

    const store = useProjectStore()
    const fetchPromise = store.fetchProjects()

    // Loading should be true while API call is in flight
    expect(store.loading).toBe(true)

    // Resolve the promise
    resolveList!({ projects: [] })
    await fetchPromise

    // Loading should be false after completion
    expect(store.loading).toBe(false)
  })
})
