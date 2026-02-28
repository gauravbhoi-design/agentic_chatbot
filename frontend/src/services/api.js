import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || ''

const api = axios.create({
  baseURL: API_BASE,
  timeout: 120000,
})

/**
 * Send a chat message and get a full response (non-streaming).
 */
export async function sendMessage(message, conversationId = null) {
  const response = await api.post('/api/chat', {
    message,
    conversation_id: conversationId,
  })
  return response.data
}

/**
 * Send a chat message with SSE streaming for real-time tool traces.
 * Returns callbacks for tool_start, tool_end, token, done, and error events.
 */
export function streamMessage(message, conversationId, callbacks) {
  const { onToolStart, onToolEnd, onToken, onDone, onError } = callbacks

  const body = JSON.stringify({
    message,
    conversation_id: conversationId,
  })

  // Use fetch + ReadableStream for SSE from POST
  const controller = new AbortController()

  fetch(`${API_BASE}/api/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body,
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))

              switch (data.type) {
                case 'session':
                  // Store conversation ID
                  break
                case 'tool_start':
                  onToolStart?.(data)
                  break
                case 'tool_end':
                  onToolEnd?.(data)
                  break
                case 'token':
                  onToken?.(data.content)
                  break
                case 'done':
                  onDone?.()
                  break
                case 'error':
                  onError?.(data.message)
                  break
              }
            } catch (e) {
              // Skip malformed JSON lines
            }
          }
        }
      }

      // Process any remaining buffer
      if (buffer.startsWith('data: ')) {
        try {
          const data = JSON.parse(buffer.slice(6))
          if (data.type === 'done') onDone?.()
        } catch (e) {
          // ignore
        }
      }
    })
    .catch((err) => {
      if (err.name !== 'AbortError') {
        onError?.(err.message)
      }
    })

  return { abort: () => controller.abort() }
}

/**
 * Check API and board health status.
 */
export async function checkHealth() {
  const response = await api.get('/api/health')
  return response.data
}

/**
 * Get board connection status.
 */
export async function getBoardsStatus() {
  const response = await api.get('/api/boards/status')
  return response.data
}
