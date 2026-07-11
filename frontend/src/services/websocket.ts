import type { WSMessage } from '../types'

type Handler = (msg: WSMessage) => void

class WebSocketManager {
  private ws: WebSocket | null = null
  private handlers: Set<Handler> = new Set()
  private retryDelay = 1000
  private maxDelay = 30000
  private token: string | null = null
  private shouldReconnect = false

  connect(token: string): void {
    this.token = token
    this.shouldReconnect = true
    this._connect()
  }

  private _connect(): void {
    if (!this.token) return

    const wsBase = import.meta.env.VITE_WS_URL || `ws://${window.location.host}`
    const url = `${wsBase}/ws/dashboard?token=${encodeURIComponent(this.token)}`

    try {
      this.ws = new WebSocket(url)
    } catch {
      this._scheduleReconnect()
      return
    }

    this.ws.onopen = () => {
      this.retryDelay = 1000 // Reset on successful connect
      console.info('[WS] Connected')
    }

    this.ws.onmessage = (event) => {
      try {
        const msg: WSMessage = JSON.parse(event.data)
        this.handlers.forEach(h => h(msg))
      } catch {
        // ignore parse errors
      }
    }

    this.ws.onclose = (event) => {
      console.info(`[WS] Closed (code=${event.code})`)
      if (this.shouldReconnect && event.code !== 4401) {
        this._scheduleReconnect()
      }
    }

    this.ws.onerror = () => {
      this.ws?.close()
    }
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
    this.ws?.close()
    this.ws = null
    this.handlers.clear()
  }

  subscribe(handler: Handler): () => void {
    this.handlers.add(handler)
    return () => this.handlers.delete(handler)
  }

  send(data: unknown): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    }
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }
}

export const wsManager = new WebSocketManager()
