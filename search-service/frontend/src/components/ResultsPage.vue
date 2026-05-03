<script setup>
import SearchBar from './SearchBar.vue'
import ResultCard from './ResultCard.vue'
import FilterSidebar from './FilterSidebar.vue'
import logo from '../assets/etu-ru-logo.svg'

defineProps({
  query: { type: String, required: true },
  lastQuery: { type: String, default: '' },
  results: { type: Array, default: () => [] },
  resultStatus: { type: String, default: 'loading' },
  isEmbed: { type: Boolean, default: false },
  dropdownOpen: { type: Boolean, default: false },
  dropdownItems: { type: Array, default: () => [] },
  dropdownMode: { type: String, default: 'recent' },
  selectedLangs: { type: Array, default: () => [] },
  sortBy: { type: String, default: 'relevance' },
  dateFilter: { type: String, default: null },
  fromDate: { type: String, default: null },
  toDate: { type: String, default: null },
})

const emit = defineEmits([
  'update:query',
  'search',
  'focus',
  'blur',
  'input',
  'clear',
  'select-item',
  'go-home',
  'update:selectedLangs',
  'update:sortBy',
  'update:dateFilter',
  'update:fromDate',
  'update:toDate',
])
</script>

<template>
  <div class="page-results">

    <header v-if="!isEmbed" class="results-header">
      <div class="header-brand" title="На главную" @click="emit('go-home')">
        <img class="logo-svg-sm" :src="logo" alt="ЛЭТИ" />
        <div class="header-brand-text">
          <span class="brand-short">СПбГЭТУ «ЛЭТИ»</span>
          <span class="brand-full">Первый электротехнический</span>
        </div>
      </div>

      <div class="header-search">
        <SearchBar
          :model-value="query"
          :show-buttons="true"
          :dropdown-open="dropdownOpen"
          :dropdown-items="dropdownItems"
          :dropdown-mode="dropdownMode"
          @update:model-value="emit('update:query', $event)"
          @search="emit('search')"
          @focus="emit('focus')"
          @blur="emit('blur')"
          @input="emit('input')"
          @clear="emit('clear')"
          @select-item="emit('select-item', $event)"
        />
      </div>
    </header>

    <div class="results-body">

      <div class="results-content">

        <div v-if="resultStatus === 'loading'" class="state-loading">
          <div class="spinner"></div>
        </div>

        <div v-else-if="resultStatus === 'ok'" class="results-list">
          <ResultCard
            v-for="item in results"
            :key="item.id"
            :item="item"
          />
        </div>

        <div v-else-if="resultStatus === 'empty'" class="state-empty">
          <p>По запросу <strong>{{ lastQuery }}</strong> ничего не найдено.</p>
          <p class="hint-title">Рекомендации:</p>
          <ul class="hints">
            <li>Убедитесь, что все слова написаны без ошибок.</li>
            <li>Попробуйте использовать другие ключевые слова.</li>
            <li>Попробуйте использовать более популярные ключевые слова.</li>
          </ul>
        </div>

        <div v-else-if="resultStatus === 'error'" class="state-error">
          Произошла ошибка при выполнении поиска. Попробуйте позже.
        </div>

      </div>

      <FilterSidebar
        :selected-langs="selectedLangs"
        :sort-by="sortBy"
        :date-filter="dateFilter"
        :from-date="fromDate"
        :to-date="toDate"
        @update:selected-langs="emit('update:selectedLangs', $event)"
        @update:sort-by="emit('update:sortBy', $event)"
        @update:date-filter="emit('update:dateFilter', $event)"
        @update:from-date="emit('update:fromDate', $event)"
        @update:to-date="emit('update:toDate', $event)"
      />

    </div>

  </div>
</template>

<style scoped>
.page-results {
    display: flex;
    flex-direction: column;
    min-height: 100vh;
}

/* Header */
.results-header {
    position: sticky;
    top: 0;
    z-index: 50;
    background: var(--bg);
    border-bottom: 1px solid var(--border);
    padding: 10px 24px;
    display: flex;
    align-items: center;
    gap: 20px;
    box-shadow: var(--shadow-sm);
}

.header-brand {
    display: flex;
    align-items: center;
    gap: 10px;
    cursor: pointer;
    text-decoration: none;
    flex-shrink: 0;
}

.header-brand:hover .brand-short {
    text-decoration: underline;
}

.header-brand-text {
    display: flex;
    flex-direction: column;
    line-height: 1.25;
}

.brand-short {
    font-size: 13px;
    font-weight: 700;
    color: var(--blue);
}

.brand-full {
    font-size: 11px;
    color: var(--text-muted);
}

.logo-svg-sm {
    width: 48px;
    height: 48px;
    display: block;
    flex-shrink: 0;
}

.header-search {
    flex: 1;
    max-width: 580px;
    position: relative;
}

/* Context overrides for SearchBar child — :deep() pierces the scoped component boundary */
.header-search :deep(.search-bar) {
    border-radius: 20px;
}

.header-search :deep(.search-input) {
    padding: 8px 4px 8px 0;
}

/* Body layout */
.results-body {
    display: flex;
    flex: 1;
    max-width: 1100px;
    width: 100%;
    margin: 0 auto;
    padding: 28px 24px;
    gap: 32px;
    align-items: flex-start;
}

.results-content {
    flex: 1;
    min-width: 0;
}

.results-list {
    display: flex;
    flex-direction: column;
}

.results-total {
    font-size: 14px;
    color: var(--text-muted);
    margin-bottom: 16px;
}

.state-loading {
    display: flex;
    justify-content: center;
    padding: 60px 0;
}

.spinner {
    width: 36px;
    height: 36px;
    border: 3px solid var(--border);
    border-top-color: var(--blue);
    border-radius: 50%;
    animation: spin .75s linear infinite;
}

@keyframes spin {
    to {
        transform: rotate(360deg);
    }
}

.state-empty,
.state-error {
    padding: 8px 0;
    font-size: 15px;
    line-height: 1.6;
}

.state-empty strong {
    font-weight: 700;
}

.hint-title {
    margin-top: 16px;
    font-weight: 600;
}

.hints {
    margin-top: 8px;
    padding-left: 20px;
}

.hints li {
    margin-bottom: 4px;
    color: var(--text-muted);
}

.state-error {
    color: #c0392b;
}

@media (max-width: 700px) {
    .results-body {
        padding: 16px;
    }

    .results-header {
        padding: 8px 12px;
    }

    .brand-full {
        display: none;
    }
}
</style>
