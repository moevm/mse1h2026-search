<script setup>
import { inject } from 'vue'

defineProps({
  item: { type: Object, required: true },
})

const highlight = inject('highlight')
</script>

<template>
  <article class="result-card">
    <div class="result-top">
      <a
        v-if="item.url"
        :href="item.url"
        class="result-title"
        target="_blank"
        rel="noopener noreferrer"
        v-html="highlight(item.title)"
      ></a>
      <span v-else class="result-title" v-html="highlight(item.title)"></span>
      <span class="result-meta">{{ item.lang }} &middot; {{ item.date }}</span>
    </div>
    <p v-if="item.abstract" class="result-abstract" v-html="highlight(item.abstract)"></p>
  </article>
</template>

<style scoped>
.result-card {
    padding: 16px 0;
    border-bottom: 1px solid var(--border);
}

.result-card:first-child {
    padding-top: 0;
}

.result-card:last-child {
    border-bottom: none;
}

.result-top {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 6px;
}

.result-title {
    font-size: 16px;
    font-weight: 600;
    color: var(--link);
    text-decoration: none;
    line-height: 1.35;
}

.result-title:hover {
    color: var(--link-hover);
    text-decoration: underline;
}

.result-title :deep(strong) {
    font-weight: 700;
}

.result-meta {
    font-size: 12px;
    color: var(--text-muted);
    white-space: nowrap;
    flex-shrink: 0;
}

.result-abstract {
    font-size: 14px;
    line-height: 1.55;
    color: #333;
    margin-bottom: 4px;
}

.result-abstract :deep(strong) {
    font-weight: 700;
    color: var(--text);
}
</style>
