<template>
  <div class="trace-card" :class="trace.status">
    <!-- Header: tool name + status badge -->
    <div class="trace-card-header">
      <span class="trace-tool-name">
        <span class="trace-tool-icon">&#x1F527;</span>
        {{ formatToolName(trace.tool_name) }}
      </span>
      <span class="trace-status" :class="trace.status">
        <template v-if="trace.status === 'running'">
          &#x23F3; Running
        </template>
        <template v-else-if="trace.status === 'completed'">
          &#x2705; {{ trace.duration_ms ? trace.duration_ms + 'ms' : 'Done' }}
        </template>
        <template v-else-if="trace.status === 'error'">
          &#x274C; Failed
        </template>
      </span>
    </div>

    <!-- Parameters -->
    <div class="trace-params" v-if="hasParams">
      <div class="trace-params-title">Parameters</div>
      <pre class="trace-params-content">{{ formattedParams }}</pre>
    </div>

    <!-- Loading bar for running state -->
    <div v-if="trace.status === 'running'" class="trace-loading-bar">
      <div class="trace-loading-bar-inner"></div>
    </div>

    <!-- Result summary -->
    <div v-if="trace.result_summary && trace.status !== 'running'" class="trace-result">
      <span class="trace-result-icon">&#x1F4CB;</span>
      {{ trace.result_summary }}
    </div>

    <!-- Items count badge -->
    <div v-if="trace.items_returned > 0 && trace.status === 'completed'" class="trace-result">
      <span class="trace-result-icon">&#x1F4CA;</span>
      {{ trace.items_returned }} records processed
    </div>

    <!-- Cleaning steps -->
    <div
      v-if="trace.cleaning_steps && trace.cleaning_steps.length > 0"
      class="trace-cleaning"
    >
      <div class="trace-cleaning-title">&#x1F9F9; Data Cleaning Applied</div>
      <div
        v-for="(step, idx) in trace.cleaning_steps"
        :key="idx"
        class="trace-cleaning-item"
      >
        {{ step }}
      </div>
    </div>

    <!-- Expand/collapse raw data -->
    <button
      v-if="trace.status === 'completed'"
      class="trace-toggle"
      @click="expanded = !expanded"
    >
      {{ expanded ? '&#x25B2; Hide raw details' : '&#x25BC; Show raw details' }}
    </button>

    <div v-if="expanded" class="trace-params" style="margin-top: 6px;">
      <pre class="trace-params-content">{{ fullTrace }}</pre>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  trace: {
    type: Object,
    required: true,
  },
})

const expanded = ref(false)

const hasParams = computed(() => {
  return (
    props.trace.parameters &&
    Object.keys(props.trace.parameters).length > 0
  )
})

const formattedParams = computed(() => {
  if (!props.trace.parameters) return ''
  const filtered = Object.entries(props.trace.parameters)
    .filter(([, v]) => v != null)
    .reduce((acc, [k, v]) => ({ ...acc, [k]: v }), {})
  return JSON.stringify(filtered, null, 2)
})

const fullTrace = computed(() => {
  return JSON.stringify(props.trace, null, 2)
})

function formatToolName(name) {
  if (!name) return 'Unknown Tool'
  return name
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}
</script>
