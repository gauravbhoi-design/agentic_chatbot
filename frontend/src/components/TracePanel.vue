<template>
  <div class="trace-panel">
    <div class="trace-header">
      <h2>
        &#x1F50D; Agent Activity
        <span v-if="chatStore.traceCount > 0" class="trace-badge">
          {{ chatStore.traceCount }}
        </span>
      </h2>
      <button class="trace-close-btn" @click="$emit('close')">&#x2715;</button>
    </div>

    <div class="trace-list">
      <!-- Empty state -->
      <div v-if="chatStore.allTraces.length === 0" class="trace-empty">
        <span class="trace-empty-icon">&#x1F6E0;&#xFE0F;</span>
        <div>Tool calls will appear here in real-time as the agent queries Monday.com boards</div>
      </div>

      <!-- Trace cards (newest first) -->
      <TraceCard
        v-for="(trace, idx) in reversedTraces"
        :key="idx"
        :trace="trace"
      />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useChatStore } from '../stores/chat'
import TraceCard from './TraceCard.vue'

defineEmits(['close'])

const chatStore = useChatStore()

const reversedTraces = computed(() => {
  return [...chatStore.allTraces].reverse()
})
</script>
