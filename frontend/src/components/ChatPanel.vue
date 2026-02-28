<template>
  <div class="chat-panel">
    <!-- Empty state with suggested queries -->
    <div v-if="!chatStore.hasMessages && !chatStore.isLoading" class="messages-container">
      <div class="empty-state">
        <span class="empty-icon">&#x1F916;</span>
        <h2 class="empty-title">Ask me anything about your business</h2>
        <p class="empty-subtitle">
          I query your Monday.com boards in real-time to deliver live insights
          about deals, work orders, billing, and more.
        </p>
        <div class="suggested-queries">
          <button
            v-for="q in suggestedQueries"
            :key="q"
            class="suggested-btn"
            @click="handleSuggested(q)"
          >
            {{ q }}
          </button>
        </div>
      </div>
    </div>

    <!-- Messages list -->
    <div v-else class="messages-container" ref="messagesRef">
      <MessageBubble
        v-for="(msg, idx) in chatStore.messages"
        :key="idx"
        :message="msg"
      />
      <!-- Typing indicator -->
      <div v-if="chatStore.isLoading && !latestAgentContent" class="message agent">
        <div class="message-bubble">
          <div class="typing-indicator">
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
          </div>
        </div>
      </div>
    </div>

    <!-- Chat input -->
    <div class="chat-input-wrapper">
      <div class="chat-input-box">
        <input
          ref="inputRef"
          v-model="inputText"
          class="chat-input"
          type="text"
          placeholder="Ask about your pipeline, win rates, billing..."
          @keydown.enter="handleSend"
          :disabled="chatStore.isLoading"
        />
        <button
          class="send-btn"
          @click="handleSend"
          :disabled="!inputText.trim() || chatStore.isLoading"
        >
          &#x27A4;
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick, computed } from 'vue'
import { useChatStore } from '../stores/chat'
import MessageBubble from './MessageBubble.vue'

const chatStore = useChatStore()
const inputText = ref('')
const messagesRef = ref(null)
const inputRef = ref(null)

const suggestedQueries = [
  "How's our pipeline looking?",
  "What's our win rate by sector?",
  "Which owners are performing best?",
  "How much revenue is stuck in collections?",
  "Show me the mining sector overview",
]

const latestAgentContent = computed(() => {
  const msgs = chatStore.messages
  if (msgs.length === 0) return ''
  const last = msgs[msgs.length - 1]
  return last.role === 'agent' ? last.content : ''
})

function handleSend() {
  if (!inputText.value.trim() || chatStore.isLoading) return
  chatStore.send(inputText.value.trim())
  inputText.value = ''
}

function handleSuggested(query) {
  chatStore.send(query)
}

// Auto-scroll on new messages
watch(
  () => chatStore.messages.length,
  async () => {
    await nextTick()
    scrollToBottom()
  }
)

// Also scroll when streaming content updates
watch(
  () => latestAgentContent.value,
  async () => {
    await nextTick()
    scrollToBottom()
  }
)

function scrollToBottom() {
  if (messagesRef.value) {
    messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  }
}
</script>
