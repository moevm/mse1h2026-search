<script setup>
import { ref, computed, watch, onMounted, provide } from 'vue'
import SearchPage from './components/SearchPage.vue'
import ResultsPage from './components/ResultsPage.vue'
import { createHighlighter } from './composables/useHighlight'
import { useRecentSearches } from './composables/useRecentSearches'
import { useSuggestions } from './composables/useSuggestions'
import { useFilters } from './composables/useFilters'
import { useSearch } from './composables/useSearch'

const isEmbed = ref(new URLSearchParams(window.location.search).get('embed') === 'true')
const dropdownOpen = ref(false)

const { recentSearches, save: saveRecent } = useRecentSearches()
const { suggestions, isTyping, onFocus: _onFocus, onInput: _onInput, clear: clearSuggestions } = useSuggestions()
const { selectedLangs, sortBy, dateFilter, fromDate, toDate, formatDateForQuery } = useFilters()
const { query, lastQuery, results, total, resultStatus, inResults, doSearch: _doSearch, clearAll: _clearAll } = useSearch({ isEmbed, saveRecent, formatDateForQuery })

provide('highlight', createHighlighter(lastQuery))
provide('highlightDrop', createHighlighter(query))

const showButtons = computed(() => inResults.value || dropdownOpen.value)
const dropdownItems = computed(() => {
  if (!dropdownOpen.value) return []
  return isTyping.value ? suggestions.value : recentSearches.value
})
const dropdownMode = computed(() => isTyping.value ? 'suggestions' : 'recent')

// --- Filter watchers: re-run search when filters change ---
watch(selectedLangs, () => { if (inResults.value) doSearch() }, { deep: true })
watch(sortBy, () => { if (inResults.value) doSearch() })
watch(dateFilter, (val) => {
  if (val) {
    fromDate.value = null
    toDate.value = null
  }
  if (inResults.value && (val !== null || (!fromDate.value && !toDate.value))) doSearch()
})
watch(fromDate, (val) => {
  if (val) dateFilter.value = null
  if (inResults.value && (val || !dateFilter.value)) doSearch()
})
watch(toDate, (val) => {
  if (val) dateFilter.value = null
  if (inResults.value && (val || !dateFilter.value)) doSearch()
})

// --- Methods ---
function doSearch(q) {
  dropdownOpen.value = false
  _doSearch(q, { selectedLangs, sortBy, dateFilter, fromDate, toDate })
}

function clearAll() {
  clearSuggestions()
  dropdownOpen.value = false
  _clearAll()
}

function onFocus() {
  _onFocus(query.value)
  dropdownOpen.value = true
}

function onBlur() {
  setTimeout(() => { dropdownOpen.value = false }, 200)
}

function onInput() {
  dropdownOpen.value = true
  _onInput(query.value)
}

function handleClear() {
  query.value = ''
  clearSuggestions()
  dropdownOpen.value = true
}

// --- Lifecycle ---
onMounted(() => {
  const urlParams = new URLSearchParams(window.location.search)
  const urlQ = urlParams.get('q')
  if (urlQ) {
    query.value = urlQ

    selectedLangs.value = urlParams.getAll('lang')
    sortBy.value = urlParams.get('sort_by') || 'relevance'
    dateFilter.value = urlParams.get('date_filter') || null
    fromDate.value = urlParams.get('from_date') || null
    toDate.value = urlParams.get('to_date') || null

    doSearch(urlQ)
  }
})
</script>

<template>
  <SearchPage
    v-if="!inResults"
    :query="query"
    :show-buttons="showButtons"
    :dropdown-open="dropdownOpen"
    :dropdown-items="dropdownItems"
    :dropdown-mode="dropdownMode"
    @update:query="query = $event"
    @search="doSearch"
    @focus="onFocus"
    @blur="onBlur"
    @input="onInput"
    @clear="handleClear"
    @select-item="doSearch"
    @go-home="clearAll"
  />
  <ResultsPage
    v-else
    :query="query"
    :last-query="lastQuery"
    :results="results"
    :total="total"
    :result-status="resultStatus"
    :is-embed="isEmbed"
    :dropdown-open="dropdownOpen"
    :dropdown-items="dropdownItems"
    :dropdown-mode="dropdownMode"
    :selected-langs="selectedLangs"
    :sort-by="sortBy"
    :date-filter="dateFilter"
    :from-date="fromDate"
    :to-date="toDate"
    @update:query="query = $event"
    @search="doSearch"
    @focus="onFocus"
    @blur="onBlur"
    @input="onInput"
    @clear="handleClear"
    @select-item="doSearch"
    @go-home="clearAll"
    @update:selected-langs="selectedLangs = $event"
    @update:sort-by="sortBy = $event"
    @update:date-filter="dateFilter = $event"
    @update:from-date="fromDate = $event"
    @update:to-date="toDate = $event"
  />
</template>