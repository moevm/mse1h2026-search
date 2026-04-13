import { ref } from 'vue'

export function useFilters() {
  const selectedLang = ref(null)
  const sortBy = ref('relevance')
  const dateFilter = ref(null)
  const fromDate = ref(null)
  const toDate = ref(null)

  function toggleLang(lang) {
    selectedLang.value = selectedLang.value === lang ? null : lang
  }

  /**
   * Converts yyyy-mm-dd (HTML date input format) to dd-mm-yyyy (API format).
   */
  function formatDateForQuery(dateStr) {
    if (!dateStr) return null
    const [y, m, d] = dateStr.split('-')
    return `${d}-${m}-${y}`
  }

  return { selectedLang, sortBy, dateFilter, fromDate, toDate, toggleLang, formatDateForQuery }
}
