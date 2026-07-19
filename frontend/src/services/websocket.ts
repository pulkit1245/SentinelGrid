import type { WSMessage } from '../types'

type Handler = (msg: WSMessage) => void

class WebSocketManager {
  private ws: WebSocket | null = null
  private handlers: Set<Handler> = new Set()
  private retryDelay = 1000
  private maxDelay = 30000
  private token: string | null = null
  private shouldReconnect = false
  private _connected = false
  private _connectedHandlers: Set<(connected: boolean) => void> = new Set()

  connect(token: string): void {
    this.token = token
    this.shouldReconnect = true
    this._connect()
  }

  private _connect(): void {
    if (!this.token) return

    // Vite proxy: /ws → ws://localhost:8000/api/v1/ws (see vite.config.ts)
    // In production, use VITE_WS_URL env var
    const wsBase = import.meta.env.VITE_WS_URL
      ? `${import.meta.env.VITE_WS_URL}`
      : `ws://${window.location.host}`
    const url = `${wsBase}/ws/dashboard?token=${encodeURIComponent(this.token)}`

    console.info('[WS] Connecting to', url)
    try {
      this.ws = new WebSocket(url)
    } catch {
      this._scheduleReconnect()
      return
    }

    this.ws.onopen = () => {
      this.retryDelay = 1000
      this._setConnected(true)
      console.info('[WS] Connected')
    }

    this.ws.onmessage = (event) => {
      try {
        const msg: WSMessage = JSON.parse(event.data)
        // Heartbeat also signals connectivity
        if (msg.type === 'heartbeat') this._setConnected(true)
        this.handlers.forEach(h => h(msg))
      } catch {
        // ignore parse errors
      }
    }

    this.ws.onclose = (event) => {
      console.info(`[WS] Closed (code=${event.code})`)
      this._setConnected(false)
      if (this.shouldReconnect && event.code !== 4401) {
        this._scheduleReconnect()
      }
    }

    this.ws.onerror = () => {
      this.ws?.close()
    }
  }

  private _setConnected(v: boolean): void {
    if (this._connected === v) return
    this._connected = v
    this._connectedHandlers.forEach(h => h(v))
  }

  private _scheduleReconnect(): void {
    setTimeout(() => {
      if (this.shouldReconnect) {
        this.retryDelay = Math.min(this.retryDelay * 2, this.maxDelay)
        this._connect()
      }
    }, this.retryDelay)
  }

  disconnect(): void {
    this.shouldReconnect = false
    this._setConnected(false)
    this.ws?.close()
    this.ws = null
    this.handlers.clear()
  }

  subscribe(handler: Handler): () => void {
    this.handlers.add(handler)
    return () => this.handlers.delete(handler)
  }

  onConnectionChange(handler: (connected: boolean) => void): () => void {
    this._connectedHandlers.add(handler)
    // Immediately emit current state
    handler(this._connected)
    return () => this._connectedHandlers.delete(handler)
  }

  send(data: unknown): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    }
  }

  get isConnected(): boolean {
    return this._connected
  }
}

export const wsManager = new WebSocketManager()
