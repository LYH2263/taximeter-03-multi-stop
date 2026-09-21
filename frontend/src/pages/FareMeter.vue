<script setup>
import { ref } from 'vue'
import { postJSON } from '../api'
const segments = ref([
  { distance_km: 5, slow_min: 2 },
  { distance_km: 4, slow_min: 1 },
])
const night = ref(false)
const out = ref(null)
const error = ref('')
const addStop = () => segments.value.push({ distance_km: 1, slow_min: 0 })
const removeStop = (i) => { if (segments.value.length > 2) segments.value.splice(i, 1) }
const run = async (persist) => {
  error.value = ''
  try {
    out.value = await postJSON('/api/fare/multi', { segments: segments.value, night: night.value, persist })
  } catch (e) {
    out.value = null
    error.value = '整单被拒绝：至少两段，且各段公里与低速分钟不得为负'
  }
}
</script>
<template>
  <div class="page"><h1>打表试算</h1>
    <div class="panel">
      <table>
        <tr><th>段</th><th>本段公里</th><th>本段低速分钟</th><th></th></tr>
        <tr v-for="(seg, i) in segments" :key="i">
          <td>{{ i + 1 }}</td>
          <td><input type="number" step="0.1" v-model.number="seg.distance_km" /></td>
          <td><input type="number" step="0.5" v-model.number="seg.slow_min" /></td>
          <td><button @click="removeStop(i)" :disabled="segments.length <= 2">删除</button></td>
        </tr>
      </table>
      <button @click="addStop">添加停点</button>
      <label><input type="checkbox" v-model="night" /> 夜间</label>
      <button @click="run(false)">试算(不记录)</button>
      <button @click="run(true)">计算并记录</button>
    </div>
    <p v-if="error" class="error">{{ error }}</p>
    <template v-if="out">
      <p class="hero-num">¥{{ out.total }}</p>
      <div class="panel">
        <p>段数 {{ out.segment_count }} · 合计公里 {{ out.distance_km }} · 合计低速 {{ out.slow_min }} 分钟</p>
        <p>起步 {{ out.start }} · 里程 {{ out.mileage }} · 低速 {{ out.slow_fee }}</p>
        <table>
          <tr><th>段</th><th>公里</th><th>低速分钟</th></tr>
          <tr v-for="seg in out.segments" :key="seg.seq">
            <td>{{ seg.seq }}</td><td>{{ seg.distance_km }}</td><td>{{ seg.slow_min }}</td>
          </tr>
        </table>
        <p v-if="out.run_id">已记录 #{{ out.run_id }}</p>
      </div>
    </template>
  </div>
</template>
