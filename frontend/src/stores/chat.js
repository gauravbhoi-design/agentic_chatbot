import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { sendMessage, streamMessage, checkHealth } from '../services/api'

export const useChatStore = defineStore('chat', () => {
  // State
  const messages = ref([])
  const isLoading = ref(false)
  const currentTraces = ref([])
  const allTraces = ref([]) // All traces across all messages
  const connectionStatus = ref('checking') // 'connected', 'disconnected', 'checking'
  const conversationId = ref(null)
  const streamingContent = ref('')
  const currentCaveats = ref([])

  // Getters
  const hasMessages = computed(() => messages.value.length > 0)
  const traceCount = computed(() => allTraces.value.length)

  // Actions
  async function send(text) {
    if (!text.trim() || isLoading.value) return

    // Add user message
    messages.value.push({
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    })

    isLoading.value = true
    streamingContent.value = ''
    currentTraces.value = []
    currentCaveats.value = []

    // Add a placeholder agent message for streaming
    const agentMsgIndex = messages.value.length
    messages.value.push({
      role: 'agent',
      content: '',
      traces: [],
      caveats: [],
      timestamp: new Date().toISOString(),
      isStreaming: true,
    })

    // Use streaming endpoint
    const streamCtrl = streamMessage(text, conversationId.value, {
      onToolStart(data) {
        const trace = {
          tool_name: data.tool,
          parameters: data.input || {},
          status: 'running',
          result_summary: '',
          items_returned: 0,
          cleaning_steps: [],
          duration_ms: 0,
          timestamp: new Date().toISOString(),
          run_id: data.run_id,
        }
        currentTraces.value.push(trace)
        allTraces.value.push(trace)
      },

      onToolEnd(data) {
        // Find the matching running trace and update it
        const trace = currentTraces.value.find(
          (t) => t.tool_name === data.tool && t.status === 'running'
        )
        if (trace) {
          trace.status = 'completed'
          trace.result_summary = data.summary || ''
          trace.items_returned = data.items || 0
        }
        // Also update in allTraces
        const globalTrace = allTraces.value.find(
          (t) => t.tool_name === data.tool && t.status === 'running'
        )
        if (globalTrace) {
          globalTrace.status = 'completed'
          globalTrace.result_summary = data.summary || ''
          globalTrace.items_returned = data.items || 0
        }
      },

      onToken(content) {
        streamingContent.value += content
        // Update the agent message in real-time
        if (messages.value[agentMsgIndex]) {
          messages.value[agentMsgIndex].content = streamingContent.value
        }
      },

      onDone() {
        if (messages.value[agentMsgIndex]) {
          messages.value[agentMsgIndex].isStreaming = false
          messages.value[agentMsgIndex].traces = [...currentTraces.value]
          messages.value[agentMsgIndex].caveats = [...currentCaveats.value]
        }
        isLoading.value = false
        streamingContent.value = ''
      },

      onError(errorMsg) {
        if (messages.value[agentMsgIndex]) {
          messages.value[agentMsgIndex].content =
            `Sorry, an error occurred: ${errorMsg}. Please try again.`
          messages.value[agentMsgIndex].isStreaming = false
        }
        isLoading.value = false
        streamingContent.value = ''
      },
    })
  }

  /**
   * Fallback: non-streaming send (used if SSE fails).
   */
  async function sendSync(text) {
    if (!text.trim() || isLoading.value) return

    messages.value.push({
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    })

    isLoading.value = true
    currentTraces.value = []

    try {
      const result = await sendMessage(text, conversationId.value)
      conversationId.value = result.conversation_id

      const traces = result.traces || []
      currentTraces.value = traces
      allTraces.value.push(...traces)

      messages.value.push({
        role: 'agent',
        content: result.response,
        traces,
        caveats: result.caveats || [],
        timestamp: new Date().toISOString(),
      })
    } catch (error) {
      messages.value.push({
        role: 'agent',
        content: `Sorry, an error occurred: ${error.message}. Please try again.`,
        traces: [],
        caveats: [],
        timestamp: new Date().toISOString(),
      })
    } finally {
      isLoading.value = false
    }
  }

  async function checkConnection() {
    connectionStatus.value = 'checking'
    try {
      const health = await checkHealth()
      connectionStatus.value = health.status === 'ok' ? 'connected' : 'disconnected'
    } catch {
      connectionStatus.value = 'disconnected'
    }
  }

  function clearChat() {
    messages.value = []
    currentTraces.value = []
    allTraces.value = []
    conversationId.value = null
    streamingContent.value = ''
  }

  return {
    messages,
    isLoading,
    currentTraces,
    allTraces,
    connectionStatus,
    conversationId,
    streamingContent,
    currentCaveats,
    hasMessages,
    traceCount,
    send,
    sendSync,
    checkConnection,
    clearChat,
  }
})
