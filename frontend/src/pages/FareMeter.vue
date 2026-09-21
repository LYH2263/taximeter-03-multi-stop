<script setup>
import { ref } from 'vue'
import { postJSON } from '../api'
const stops = ref([{ distance_km: 5, slow_min: 2 }, { distance_km: 3, slow_min: 1 }])
const night = ref(false)
const out = ref(null)
const err = ref(null)
const add = () => stops.value.push({ distance_km: 1, slow_min: 0 })
const remove = (i) => { if (stops.value.length > 2) stops.value.splice(i, 1) }
const run = async () => {
  out.value = null; err.value = null
  try {
    out.value = await postJSON('/api/fare/multi', { segments: stops.value, night: night.value, persist: true })
  } catch (e) {
    try { err.value = JSON.parse(e.message).detail } catch { err.value = '整单被拒绝' }
  }
}
</script>
<template>
  <div class="page"><h1>打表试算</h1>
    <div class="panel">
      <div v-for="(s, i) in stops" :key="i" class="stop-row">
        <span>第{{ i + 1 }}段</span>
        <label>公里 <input type="number" step="0.1" v-model.number="s.distance_km" /></label>
        <label>低速分钟 <input type="number" step="1" v-model.number="s.slow_min" /></label>
        <button @click="remove(i)" :disabled="stops.length <= 2">删除</button>
      </div>
      <button @click="add">增加停点</button>
      <label><input type="checkbox" v-model="night" /> 夜间</label>
      <button @click="run">计算</button>
    </div>
    <p v-if="err" class="reject">{{ err }}</p>
    <template v-if="out">
      <p class="hero-num">¥{{ out.total }}</p>
      <table>
        <tr><th>段序</th><th>本段公里</th><th>本段低速分钟</th></tr>
        <tr v-for="s in out.segments" :key="s.seq"><td>{{ s.seq }}</td><td>{{ s.distance_km }}</td><td>{{ s.slow_min }}</td></tr>
      </table>
      <p>共 {{ out.segment_count }} 段 · 合计 {{ out.distance_km }} 公里 · 低速 {{ out.slow_min }} 分钟</p>
      <p>起步 {{ out.start }} · 里程 {{ out.mileage }} · 低速 {{ out.slow_fee }}</p>
    </template>
  </div>
</template>
