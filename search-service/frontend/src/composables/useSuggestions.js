import { ref, onUnmounted } from 'vue'

const API_BASE = import.meta.env.VITE_API_BASE ?? ''
const DEBOUNCE_MS = 300

export function useSuggestions() {
  const suggestions = ref([])
  const isTyping = ref(false)

  let debounceTimer = null

  function onFocus(currentQuery) {
    isTyping.value = !!(currentQuery.trim() && suggestions.value.length)
  }

  function onInput(currentQuery) {
    if (!currentQuery.trim()) {
      isTyping.value = false
      suggestions.value = []
      return
    }
    isTyping.value = true
    clearTimeout(debounceTimer)
    debounceTimer = setTimeout(() => fetchSuggestions(currentQuery), DEBOUNCE_MS)
  }

  async function fetchSuggestions(q) {
    try {
      const res = await fetch(`${API_BASE}/api/suggest?q=${encodeURIComponent(q)}`)
      if (!res.ok) { suggestions.value = []; return }
      const data = await res.json()
      suggestions.value = data.suggestions ?? []
    } catch {
      suggestions.value = []
    }
  }

  function clear() {
    clearTimeout(debounceTimer)
    suggestions.value = []
    isTyping.value = false
  }

  onUnmounted(() => {
    clearTimeout(debounceTimer)
  })

  return { suggestions, isTyping, onFocus, onInput, clear }
}
