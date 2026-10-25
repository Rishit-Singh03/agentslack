import { useEffect, useRef, useState } from 'react'
import type { LiveEvent } from '../api/types'

export function useSocket(onEvent: (event: LiveEvent) => void, onReconnect: () => void) {
  const handler = useRef(onEvent)
  const reconnect = useRef(onReconnect)
  handler.current = onEvent
  reconnect.current = onReconnect
  const [connected, setConnected] = useState(false)
  useEffect(() => {
    let disposed = false
    let socket: WebSocket
    let timer: ReturnType<typeof setTimeout>
    let attempts = 0
    const connect = () => {
      socket = new WebSocket(
        `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`,
      )
      socket.onopen = () => {
        if (disposed) return
        setConnected(true)
        attempts = 0
        reconnect.current()
      }
      socket.onmessage = (event) => {
        try {
          handler.current(JSON.parse(event.data) as LiveEvent)
        } catch {
          /* Ignore malformed events. */
        }
      }
      socket.onclose = () => {
        setConnected(false)
        if (!disposed) timer = setTimeout(connect, Math.min(1000 * 2 ** attempts++, 10000))
      }
      socket.onerror = () => socket.close()
    }
    connect()
    return () => {
      disposed = true
      clearTimeout(timer)
      socket.close()
    }
  }, [])
  return connected
}
