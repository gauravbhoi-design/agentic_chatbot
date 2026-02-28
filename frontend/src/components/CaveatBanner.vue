<template>
  <div v-if="caveats.length > 0" class="caveat-banner">
    <span class="caveat-icon">⚠️</span>
    <div>
      <strong style="font-size: 12px; display: block; margin-bottom: 2px;">Data Quality Notes</strong>
      <ul class="caveat-list">
        <li v-for="(caveat, idx) in caveats" :key="idx">{{ caveat }}</li>
      </ul>
    </div>
  </div>
</template>

<script setup>
defineProps({
  caveats: {
    type: Array,
    default: () => [],
  },
})
</script>
