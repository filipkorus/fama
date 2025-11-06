import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useWebSocket } from '../hooks/useWebSocket'
import { socket } from '../services/socket'

// Mock socket.io-client
vi.mock('../services/socket', () => ({
  socket: {
    on: vi.fn(),
    off: vi.fn(),
    emit: vi.fn(),
    connected: false,
  },
}))

describe('useWebSocket', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('should initialize with disconnected state', () => {
    const { result } = renderHook(() => useWebSocket())

    expect(result.current.isConnected).toBe(false)
    expect(result.current.messages).toEqual([])
    expect(result.current.username).toBeNull()
  })

  it('should register socket event listeners on mount', () => {
    renderHook(() => useWebSocket())

    expect(socket.on).toHaveBeenCalledWith('connect', expect.any(Function))
    expect(socket.on).toHaveBeenCalledWith('disconnect', expect.any(Function))
    expect(socket.on).toHaveBeenCalledWith('message', expect.any(Function))
    expect(socket.on).toHaveBeenCalledWith('registered', expect.any(Function))
  })

  it('should provide sendMessage and register functions', () => {
    const { result } = renderHook(() => useWebSocket())

    expect(result.current.sendMessage).toBeDefined()
    expect(typeof result.current.sendMessage).toBe('function')
    expect(result.current.register).toBeDefined()
    expect(typeof result.current.register).toBe('function')
  })

  it('should send message when sendMessage is called', () => {
    const { result } = renderHook(() => useWebSocket())

    act(() => {
      result.current.sendMessage('Hello, server!')
    })

    expect(socket.emit).toHaveBeenCalledWith('message', { message: 'Hello, server!' })
  })

  it('should not send empty messages', () => {
    const { result } = renderHook(() => useWebSocket())

    act(() => {
      result.current.sendMessage('   ')
    })

    expect(socket.emit).not.toHaveBeenCalled()
  })

  it('should register user when register is called', () => {
    const { result } = renderHook(() => useWebSocket())

    act(() => {
      result.current.register('testuser')
    })

    expect(socket.emit).toHaveBeenCalledWith('register', { username: 'testuser' })
  })

  // Add your own tests here
  it('example placeholder test', () => {
    // TODO: Add more custom tests for your WebSocket logic
    expect(true).toBe(true)
  })
})
