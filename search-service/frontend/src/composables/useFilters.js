import { ref } from 'vue'

export function useFilters() {
  const selectedLangs = ref([])
  const sortBy = ref('relevance')
  const dateFilter = ref(null)
  const fromDate = ref(null)
  const toDate = ref(null)

  function toggleLang(lang) {
    const idx = selectedLangs.value.indexOf(lang)
    if (idx > -1) {
      selectedLangs.value.splice(idx, 1)
    } else {
      selectedLangs.value.push(lang)
    }
  }

  function restoreFromUrl() {
    const params = new URLSearchParams(window.location.search)
    selectedLangs.value = params.getAll('lang')
    sortBy.value = params.get('sort_by') || 'relevance'
    dateFilter.value = params.get('date_filter') || null
    fromDate.value = params.get('from_date') || null
    toDate.value = params.get('to_date') || null
  }

  function resetFilters() {
    selectedLangs.value = []
    sortBy.value = 'relevance'
    dateFilter.value = null
    fromDate.value = null
    toDate.value = null
  }

  function formatDateForQuery(dateStr) {
    if (!dateStr) return null
    const [y, m, d] = dateStr.split('-')
    return `${d}-${m}-${y}`
  }

  return {
    selectedLangs, sortBy, dateFilter, fromDate, toDate,
    toggleLang, formatDateForQuery, restoreFromUrl, resetFilters
  }
}