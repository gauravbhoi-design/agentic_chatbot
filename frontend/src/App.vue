<template>
  <div class="app">
    <header class="app-header">
      <div class="header-left">
        <div class="header-logo">&#x1F4CA;</div>
        <div>
          <div class="header-title">Monday.com BI Agent</div>
          <div class="header-subtitle">AI-Powered Business Intelligence</div>
        </div>
      </div>

      <div class="header-right">
        <div class="connection-status">
          <span
            class="status-dot"
            :class="{
              disconnected: chatStore.connectionStatus === 'disconnected',
              checking: chatStore.connectionStatus === 'checking',
            }"
          ></span>
          <span>{{
            chatStore.connectionStatus === 'connected'
              ? 'Connected'
              : chatStore.connectionStatus === 'checking'
                ? 'Checking...'
                : 'Disconnected'
          }}</span>
        </div>

        <!-- Trace toggle button -->
        <button class="trace-toggle-btn" :class="{ active: traceOpen }" @click="traceOpen = !traceOpen">
          <span class="trace-toggle-icon">&#x1F50D;</span>
          <span>Agent Trace</span>
          <span v-if="chatStore.traceCount > 0" class="trace-toggle-badge">{{ chatStore.traceCount }}</span>
        </button>
      </div>
    </header>

    <div class="main-layout">
      <ChatPanel />

      <!-- Floating trace overlay -->
      <Transition name="trace-slide">
        <div v-if="traceOpen" class="trace-overlay-backdrop" @click.self="traceOpen = false">
          <div class="trace-overlay">
            <TracePanel @close="traceOpen = false" />
          </div>
        </div>
      </Transition>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useChatStore } from './stores/chat'
import ChatPanel from './components/ChatPanel.vue'
import TracePanel from './components/TracePanel.vue'

const chatStore = useChatStore()
const traceOpen = ref(false)

onMounted(() => {
  chatStore.checkConnection()
})
</script>
