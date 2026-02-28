<template>
  <div v-if="rows.length > 0" class="data-table-wrapper">
    <table class="data-table">
      <thead>
        <tr>
          <th v-for="col in columns" :key="col">{{ col }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, idx) in rows" :key="idx">
          <td v-for="col in columns" :key="col">{{ row[col] ?? '-' }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  data: {
    type: Array,
    default: () => [],
  },
})

const columns = computed(() => {
  if (props.data.length === 0) return []
  return Object.keys(props.data[0])
})

const rows = computed(() => props.data)
</script>

<style scoped>
.data-table-wrapper {
  overflow-x: auto;
  margin: 8px 0;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.data-table th,
.data-table td {
  padding: 8px 12px;
  border: 1px solid var(--border);
  text-align: left;
}

.data-table th {
  background: #f5f5f5;
  font-weight: 600;
  white-space: nowrap;
}

.data-table tbody tr:hover {
  background: #fafafa;
}
</style>
