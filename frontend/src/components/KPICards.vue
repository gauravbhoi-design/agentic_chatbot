<template>
  <div v-if="cards.length > 0" class="kpi-grid">
    <div v-for="(card, idx) in cards" :key="idx" class="kpi-card">
      <div class="kpi-label">{{ card.label }}</div>
      <div class="kpi-value">{{ card.value }}</div>
      <div v-if="card.sublabel" class="kpi-sublabel">{{ card.sublabel }}</div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  cards: {
    type: Array,
    default: () => [],
    // Each card: { label: string, value: string, sublabel?: string }
  },
})
</script>
