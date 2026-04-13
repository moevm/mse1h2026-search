export function escHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

/**
 * Returns a highlight(text) function that wraps query matches in <strong>.
 * @param {import('vue').Ref<string>} queryRef — reactive ref with current query
 */
export function createHighlighter(queryRef) {
  return (text) => {
    if (!text) return ''
    const safe = escHtml(text)
    const q = queryRef.value.trim()
    if (!q) return safe
    const re = new RegExp(`(${q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi')
    return safe.replace(re, '<strong>$1</strong>')
  }
}
