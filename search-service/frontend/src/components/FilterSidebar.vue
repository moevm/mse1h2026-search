<script setup>
const props = defineProps({
  selectedLangs: { type: Array, default: () => [] },
  sortBy: { type: String, default: 'relevance' },
  dateFilter: { type: String, default: null },
  fromDate: { type: String, default: null },
  toDate: { type: String, default: null },
})

const emit = defineEmits([
  'update:selectedLangs',
  'update:sortBy',
  'update:dateFilter',
  'update:fromDate',
  'update:toDate',
])

const languages = ['RU', 'EN', 'DE', 'ES', 'FR', 'PT', 'ZH', 'VI']

const dateOptions = [
  { label: 'За последний месяц', value: 'month' },
  { label: 'За год', value: 'year' },
  { label: 'За 3 года', value: '3years' },
]

function toggleLang(lang) {
  const newLangs = [...props.selectedLangs]
  const idx = newLangs.indexOf(lang)
  if (idx > -1) {
    newLangs.splice(idx, 1)
  } else {
    newLangs.push(lang)
  }
  emit('update:selectedLangs', newLangs)
}
</script>

<template>
  <aside class="results-sidebar">
    <div class="sidebar-block sidebar-langs">
      <button
        v-for="lang in languages"
        :key="lang"
        class="lang-btn"
        :class="{ active: selectedLangs.includes(lang) }"
        @click="toggleLang(lang)"
      >{{ lang }}</button>
    </div>

    <div class="sidebar-block">
      <div class="sidebar-label">Сортировка</div>
      <label class="sidebar-option">
        <input
          type="radio"
          :checked="sortBy === 'relevance'"
          value="relevance"
          @change="emit('update:sortBy', 'relevance')"
        />
        <span>По релевантности</span>
      </label>
      <label class="sidebar-option">
        <input
          type="radio"
          :checked="sortBy === 'date'"
          value="date"
          @change="emit('update:sortBy', 'date')"
        />
        <span>По дате</span>
      </label>
    </div>

    <div class="sidebar-block">
      <div class="sidebar-label">Период</div>
      <label v-for="opt in dateOptions" :key="opt.value" class="sidebar-option">
        <input
          type="radio"
          :checked="dateFilter === opt.value"
          :value="opt.value"
          @change="emit('update:dateFilter', opt.value)"
        />
        <span>{{ opt.label }}</span>
      </label>
      <div class="date-range-inputs">
        <div class="date-field">
          <span>От</span>
          <input
            type="date"
            :value="fromDate"
            @change="emit('update:fromDate', $event.target.value)"
          />
        </div>
        <div class="date-field">
          <span>До</span>
          <input
            type="date"
            :value="toDate"
            @change="emit('update:toDate', $event.target.value)"
          />
        </div>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.results-sidebar {
    width: 220px;
    flex-shrink: 0;
    background: var(--bg-sidebar);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px;
    position: sticky;
    top: 72px; /* below sticky header */
    font-size: 13px;
}

.sidebar-block {
    padding-bottom: 14px;
    margin-bottom: 14px;
    border-bottom: 1px solid var(--border);
}

.sidebar-block:last-child {
    border-bottom: none;
    margin-bottom: 0;
    padding-bottom: 0;
}

.sidebar-label {
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: .05em;
    color: var(--text-muted);
    margin-bottom: 8px;
}

.sidebar-langs {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    border-bottom: 1px solid var(--border);
    padding-bottom: 14px;
    margin-bottom: 14px;
}

.lang-btn {
    padding: 3px 8px;
    border: 1px solid var(--border);
    border-radius: 4px;
    font-size: 11.5px;
    font-weight: 600;
    color: var(--text-muted);
    background: var(--bg);
    cursor: pointer;
    transition: border-color .12s, color .12s, background .12s;
}

.lang-btn:hover {
    border-color: var(--blue);
    color: var(--blue);
}

.lang-btn.active {
    border-color: var(--blue);
    background: var(--blue);
    color: #fff;
}

.sidebar-option {
    display: flex;
    align-items: center;
    gap: 7px;
    padding: 4px 0;
    cursor: pointer;
    color: var(--text);
}

.sidebar-option input[type="radio"] {
    accent-color: var(--blue);
    cursor: pointer;
}

.sidebar-option span {
    font-size: 13px;
}

.date-range-inputs {
    margin-top: 12px;
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.date-field {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
    color: var(--text-muted);
}

.date-field span {
    min-width: 20px;
}

.date-field input[type="date"] {
    flex: 1;
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 4px 6px;
    font-family: var(--font);
    font-size: 13px;
    color: var(--text);
    outline: none;
    background: var(--bg);
}

.date-field input[type="date"]:focus {
    border-color: var(--blue);
}

@media (max-width: 700px) {
    .results-sidebar {
        display: none;
    }
}
</style>
