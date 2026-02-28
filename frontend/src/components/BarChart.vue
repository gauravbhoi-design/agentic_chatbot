<template>
  <div v-if="hasData" class="chart-wrapper">
    <Bar :data="chartData" :options="chartOptions" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js'
import { Bar } from 'vue-chartjs'

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend)

const props = defineProps({
  labels: {
    type: Array,
    default: () => [],
  },
  values: {
    type: Array,
    default: () => [],
  },
  title: {
    type: String,
    default: '',
  },
  color: {
    type: String,
    default: '#6c5ce7',
  },
})

const hasData = computed(() => props.labels.length > 0 && props.values.length > 0)

const chartData = computed(() => ({
  labels: props.labels,
  datasets: [
    {
      label: props.title,
      data: props.values,
      backgroundColor: props.color + '99',
      borderColor: props.color,
      borderWidth: 1,
      borderRadius: 4,
    },
  ],
}))

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    title: {
      display: false,
    },
  },
  scales: {
    y: {
      beginAtZero: true,
      grid: { color: '#f0f0f0' },
    },
    x: {
      grid: { display: false },
    },
  },
}
</script>

<style scoped>
.chart-wrapper {
  height: 250px;
  margin: 12px 0;
}
</style>
