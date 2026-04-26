import { ref } from 'vue'

const API_BASE = import.meta.env.VITE_API_BASE ?? ''

/**
 * @param {object} options
 * @param {import('vue').Ref<boolean>} options.isEmbed   — preserve ?embed=true in URL
 * @param {function}                   options.saveRecent — called with search term on each search
 * @param {function}                   options.formatDateForQuery — date format utility
 */
export function useSearch({ isEmbed, saveRecent, formatDateForQuery }) {
  const query = ref('')
  const lastQuery = ref('')
  const results = ref([])
  const total = ref(0)
  const resultStatus = ref('loading')
  const inResults = ref(false)

  let abortController = null

  /**
   * @param {string|undefined} q       — search term; falls back to query.value when omitted
   * @param {object}           filters — object of Refs: { selectedLang, sortBy, dateFilter, fromDate, toDate }
   */
  async function doSearch(q, filters = {}) {
    const term = (q ?? query.value).trim()
    if (!term) return

    query.value = term
    lastQuery.value = term
    inResults.value = true
    resultStatus.value = 'loading'

    saveRecent(term)

    // Sync current query to the URL for bookmarking / refresh
    const urlParams = new URLSearchParams(window.location.search)
    urlParams.set('q', term)
    if (isEmbed.value) urlParams.set('embed', 'true')

    if (filters.selectedLangs?.value?.length) {
      urlParams.delete('lang')
      filters.selectedLangs.value.forEach(l => urlParams.append('lang', l))
    } else {
      urlParams.delete('lang')
    }

    if (filters.sortBy?.value && filters.sortBy.value !== 'relevance') urlParams.set('sort_by', filters.sortBy.value)
    else urlParams.delete('sort_by')

    if (filters.dateFilter?.value) urlParams.set('date_filter', filters.dateFilter.value)
    else urlParams.delete('date_filter')

    if (filters.fromDate?.value) urlParams.set('from_date', filters.fromDate.value)
    else urlParams.delete('from_date')

    if (filters.toDate?.value) urlParams.set('to_date', filters.toDate.value)
    else urlParams.delete('to_date')

    window.history.replaceState({}, '', `?${urlParams}`)

    abortController?.abort()
    abortController = new AbortController()

    try {
      const searchParams = new URLSearchParams({ q: term, page: 1, page_size: 10 })

      const { selectedLangs, sortBy, dateFilter, fromDate, toDate } = filters
      if (selectedLangs?.value?.length) {
        selectedLangs.value.forEach(l => searchParams.append('lang', l))
      }
      if (sortBy?.value && sortBy.value !== 'relevance') searchParams.set('sort_by', sortBy.value)
      if (dateFilter?.value) {
        searchParams.set('date_filter', dateFilter.value)
      } else {
        if (fromDate?.value) searchParams.set('from_date', formatDateForQuery(fromDate.value))
        if (toDate?.value) searchParams.set('to_date', formatDateForQuery(toDate.value))
      }

      const res = await fetch(`${API_BASE}/api/search?${searchParams}`, {
        signal: abortController.signal,
      })
      if (!res.ok) { resultStatus.value = 'error'; return }
      const data = await res.json()
      results.value = data.results ?? []
      total.value = data.total ?? 0
      resultStatus.value = results.value.length ? 'ok' : 'empty'
    } catch (err) {
      if (err.name !== 'AbortError') resultStatus.value = 'error'
    }
  }

  function clearAll() {
    abortController?.abort()
    query.value = ''
    lastQuery.value = ''
    results.value = []
    total.value = 0
    inResults.value = false
    resultStatus.value = 'loading'

    const urlParams = new URLSearchParams(window.location.search)
    urlParams.delete('q')
    const qs = urlParams.toString()
    window.history.replaceState({}, '', qs ? `?${qs}` : window.location.pathname)
  }

  return { query, lastQuery, results, total, resultStatus, inResults, doSearch, clearAll }
}
