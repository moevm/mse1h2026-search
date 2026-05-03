import { ref } from 'vue'

const STORAGE_KEY = 'leti_recent'
const MAX_ITEMS = 5

function loadFromStorage() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]')
  } catch {
    return []
  }
}

export function useRecentSearches() {
  const recentSearches = ref(loadFromStorage())

  function save(term) {
    const next = [term, ...recentSearches.value.filter(r => r !== term)].slice(0, MAX_ITEMS)
    recentSearches.value = next
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
    } catch {
      // Ignore localStorage quota errors
    }
  }

  return { recentSearches, save }
}
