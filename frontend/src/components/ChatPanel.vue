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
    <div v-else class="messages-container" ref="messagesRef" @scroll="onScroll">
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

      <!-- Scroll-to-bottom button -->
      <Transition name="scroll-btn">
        <button
          v-if="!isAtBottom && chatStore.hasMessages"
          class="scroll-to-bottom"
          @click="scrollToBottom"
        >
          &#x2193;
        </button>
      </Transition>
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
const isAtBottom = ref(true)

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

function onScroll(e) {
  const { scrollTop, scrollHeight, clientHeight } = e.target
  isAtBottom.value = scrollHeight - scrollTop - clientHeight < 80
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
    if (isAtBottom.value) {
      await nextTick()
      scrollToBottom()
    }
  }
)

function scrollToBottom() {
  if (messagesRef.value) {
    messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    isAtBottom.value = true
  }
}
</script>

<style scoped>
.scroll-to-bottom {
  position: sticky;
  bottom: 16px;
  left: 50%;
  transform: translateX(-50%);
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--bg-elevated);
  border: 1px solid var(--border-light);
  box-shadow: var(--shadow-lg);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-300);
  font-size: 16px;
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  z-index: 10;
  margin-left: auto;
  margin-right: auto;
}

.scroll-to-bottom:hover {
  background: var(--accent);
  color: white;
  border-color: var(--accent);
  box-shadow: 0 4px 16px var(--accent-glow);
  transform: translateX(-50%) scale(1.1);
}

.scroll-btn-enter-active {
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}
.scroll-btn-leave-active {
  transition: all 0.2s ease-in;
}
.scroll-btn-enter-from,
.scroll-btn-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(16px) scale(0.8);
}
</style>
