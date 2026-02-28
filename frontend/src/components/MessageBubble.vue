<template>
  <div class="message" :class="message.role === 'user' ? 'user' : 'agent'">
    <div class="message-bubble">
      <!-- User message: plain text -->
      <template v-if="message.role === 'user'">
        {{ message.content }}
      </template>

      <!-- Agent message: rendered markdown + caveats -->
      <template v-else>
        <div class="message-content" v-html="renderedContent"></div>

        <!-- Streaming cursor -->
        <span v-if="message.isStreaming" class="streaming-cursor"></span>

        <!-- Data quality caveats -->
        <CaveatBanner
          v-if="message.caveats && message.caveats.length > 0"
          :caveats="message.caveats"
        />
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { marked } from 'marked'
import CaveatBanner from './CaveatBanner.vue'

const props = defineProps({
  message: {
    type: Object,
    required: true,
  },
})

// Configure marked for safe rendering
marked.setOptions({
  breaks: true,
  gfm: true,
})

const renderedContent = computed(() => {
  if (!props.message.content) return ''
  try {
    return marked(props.message.content)
  } catch {
    return props.message.content
  }
})
</script>

<style scoped>
.streaming-cursor {
  display: inline-block;
  width: 2px;
  height: 1.1em;
  background: var(--accent-light);
  margin-left: 2px;
  vertical-align: text-bottom;
  animation: cursorBlink 1s step-end infinite;
  border-radius: 1px;
}

@keyframes cursorBlink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
</style>
