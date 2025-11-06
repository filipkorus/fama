import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import App from '../App'

// Mock the useWebSocket hook
vi.mock('../hooks/useWebSocket', () => ({
  useWebSocket: vi.fn(() => ({
    isConnected: false,
    sendMessage: vi.fn(),
    messages: [],
    username: null,
    register: vi.fn(),
  })),
}))

describe('App', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the app title', () => {
    render(<App />)
    expect(screen.getByText(/Post-Quantum Cryptography - WebSocket Demo/i)).toBeInTheDocument()
  })

  it('shows connection status', () => {
    render(<App />)
    // Should show either connected or disconnected status
    const statusElement = screen.getByText(/Connected|Disconnected/i)
    expect(statusElement).toBeInTheDocument()
  })

  it('renders register section when no username', () => {
    render(<App />)
    expect(screen.getByRole('heading', { name: /Register/i })).toBeInTheDocument()
    const inputElement = screen.getByPlaceholderText(/Enter your username/i)
    expect(inputElement).toBeInTheDocument()
  })

  it('renders register button', () => {
    render(<App />)
    const registerButton = screen.getByRole('button', { name: /Register/i })
    expect(registerButton).toBeInTheDocument()
  })

  // Add your own tests here
  it('example placeholder test', () => {
    // TODO: Add your custom test here
    expect(true).toBe(true)
  })
})


