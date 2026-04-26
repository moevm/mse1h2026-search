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

  /**
   * Converts yyyy-mm-dd (HTML date input format) to dd-mm-yyyy (API format).
   */
  function formatDateForQuery(dateStr) {
    if (!dateStr) return null
    const [y, m, d] = dateStr.split('-')
    return `${d}-${m}-${y}`
  }

  return { selectedLangs, sortBy, dateFilter, fromDate, toDate, toggleLang, formatDateForQuery }
}
