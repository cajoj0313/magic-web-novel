/** Task store unit tests. */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('@/api', () => ({
  apiClient: {
    tasks: {
      status: vi.fn(),
      pause: vi.fn(),
      resume: vi.fn(),
      cancel: vi.fn(),
    },
    projects: { list: vi.fn(), create: vi.fn(), switch: vi.fn(), delete: vi.fn(), overview: vi.fn() },
    chapters: { list: vi.fn(), get: vi.fn(), save: vi.fn(), draft: vi.fn() },
    review: { start: vi.fn(), history: vi.fn(), report: vi.fn() },
    plan: { getMasterOutline: vi.fn(), saveMasterOutline: vi.fn(), startVolume: vi.fn(), getVolume: vi.fn() },
    query: { entity: vi.fn(), powerSystem: vi.fn(), foreshadowing: vi.fn(), goldenFinger: vi.fn() },
    settings: { get: vi.fn(), save: vi.fn() },
    llmConfigs: { list: vi.fn(), add: vi.fn(), update: vi.fn(), delete: vi.fn(), setDefault: vi.fn(), test: vi.fn() },
    learn: { list: vi.fn(), add: vi.fn() },
  },
}))

describe('useTaskStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('initial state is idle with no events', async () => {
    const { useTaskStore } = await import('@/stores/task')
    const store = useTaskStore()
    expect(store.activeTaskId).toBeNull()
    expect(store.taskEvents).toEqual([])
    expect(store.taskStatus).toBe('idle')
  })

  it('connectSSE initializes state and returns EventSource', async () => {
    const { useTaskStore } = await import('@/stores/task')

    // Mock EventSource as a proper class
    const mockESInstance = {
      addEventListener: vi.fn(),
      close: vi.fn(),
    }
    class MockEventSource {
      constructor(_url: string) {}
      addEventListener = mockESInstance.addEventListener
      close = mockESInstance.close
    }
    vi.stubGlobal('EventSource', MockEventSource)

    const store = useTaskStore()
    const es = store.connectSSE('task-123')

    expect(store.activeTaskId).toBe('task-123')
    expect(store.taskEvents).toEqual([])
    expect(store.taskStatus).toBe('running')
    expect(es).toBeInstanceOf(MockEventSource)

    vi.unstubAllGlobals()
  })

  it('pauseTask calls API', async () => {
    const { useTaskStore } = await import('@/stores/task')
    const { apiClient } = await import('@/api')

    vi.mocked(apiClient.tasks.pause).mockResolvedValue({})

    const store = useTaskStore()
    await store.pauseTask('task-1')

    expect(apiClient.tasks.pause).toHaveBeenCalledWith('task-1')
  })

  it('resumeTask calls API', async () => {
    const { useTaskStore } = await import('@/stores/task')
    const { apiClient } = await import('@/api')

    vi.mocked(apiClient.tasks.resume).mockResolvedValue({})

    const store = useTaskStore()
    await store.resumeTask('task-1')

    expect(apiClient.tasks.resume).toHaveBeenCalledWith('task-1')
  })

  it('cancelTask calls API', async () => {
    const { useTaskStore } = await import('@/stores/task')
    const { apiClient } = await import('@/api')

    vi.mocked(apiClient.tasks.cancel).mockResolvedValue({})

    const store = useTaskStore()
    await store.cancelTask('task-2')

    expect(apiClient.tasks.cancel).toHaveBeenCalledWith('task-2')
  })
})
