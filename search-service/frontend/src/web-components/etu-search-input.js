const ELEMENT_NAME = 'etu-search-input'
const DEFAULT_NAME = 'search'
const DEFAULT_PLACEHOLDER = 'Поиск по сайту'
const DEFAULT_SUGGEST_PATH = '/api/suggest'
const DEFAULT_MODE_ID = 'site'
const DEFAULT_TARGET = '_blank'
const DEBOUNCE_MS = 300

const styles = `
  :host {
    box-sizing: border-box;
    display: block;
    width: 100%;
    min-width: 0;
    font: inherit;
    color: inherit;
    --etu-search-bg: #fff;
    --etu-search-text: currentColor;
    --etu-search-muted: #667085;
    --etu-search-border: #d0d5dd;
    --etu-search-accent: #003087;
    --etu-search-accent-contrast: #fff;
    --etu-search-focus-ring: rgba(0, 48, 135, 0.14);
    --etu-search-hover-bg: #eef4ff;
    --etu-search-radius: 8px;
    --etu-search-shadow: 0 8px 20px rgba(15, 23, 42, 0.14);
    --etu-search-gap: 6px;
    --etu-search-min-height: 40px;
    --etu-search-dropdown-z-index: 1000;
  }

  *,
  *::before,
  *::after {
    box-sizing: border-box;
  }

  [hidden] {
    display: none !important;
  }

  .root {
    position: relative;
    display: flex;
    align-items: stretch;
    gap: var(--etu-search-gap);
    width: 100%;
    min-width: 0;
    color: var(--etu-search-text);
    font: inherit;
  }

  .field {
    position: relative;
    display: flex;
    align-items: center;
    flex: 1 1 auto;
    min-width: 0;
    min-height: var(--etu-search-min-height);
    border: 1px solid var(--etu-search-border);
    border-radius: var(--etu-search-radius);
    background: var(--etu-search-bg);
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
  }

  .field:focus-within {
    border-color: var(--etu-search-accent);
    box-shadow: 0 0 0 3px var(--etu-search-focus-ring);
  }

  .input {
    display: block;
    flex: 1 1 auto;
    width: 100%;
    min-width: 0;
    border: 0;
    outline: 0;
    padding: 9px 12px;
    background: transparent;
    color: inherit;
    font: inherit;
    line-height: 1.4;
  }

  .input::placeholder {
    color: var(--etu-search-muted);
    opacity: 1;
  }

  .mode {
    flex: 0 0 auto;
    min-height: var(--etu-search-min-height);
    max-width: min(190px, 34vw);
    border: 1px solid var(--etu-search-border);
    border-radius: var(--etu-search-radius);
    background: var(--etu-search-bg);
    color: inherit;
    cursor: pointer;
    font: inherit;
    line-height: 1.4;
    padding: 0 30px 0 10px;
  }

  .mode:focus-visible {
    outline: 2px solid var(--etu-search-accent);
    outline-offset: 2px;
  }

  .languages {
    display: flex;
    align-items: center;
    flex: 0 0 auto;
    gap: 4px;
    min-width: 0;
  }

  .language {
    min-height: var(--etu-search-min-height);
    border: 1px solid var(--etu-search-border);
    border-radius: var(--etu-search-radius);
    background: var(--etu-search-bg);
    color: inherit;
    cursor: pointer;
    font: inherit;
    font-size: 0.82em;
    font-weight: 600;
    line-height: 1;
    padding: 0 9px;
    text-transform: uppercase;
  }

  .language:hover {
    border-color: var(--etu-search-accent);
    color: var(--etu-search-accent);
  }

  .language[aria-pressed="true"] {
    border-color: var(--etu-search-accent);
    background: var(--etu-search-accent);
    color: var(--etu-search-accent-contrast);
  }

  .suggestions {
    position: absolute;
    top: calc(100% + 4px);
    left: 0;
    right: 0;
    z-index: var(--etu-search-dropdown-z-index);
    overflow: hidden;
    border: 1px solid var(--etu-search-border);
    border-radius: var(--etu-search-radius);
    background: var(--etu-search-bg);
    box-shadow: var(--etu-search-shadow);
  }

  .suggestion {
    display: flex;
    align-items: center;
    width: 100%;
    min-height: 38px;
    border: 0;
    background: transparent;
    color: inherit;
    cursor: pointer;
    font: inherit;
    line-height: 1.35;
    padding: 9px 12px;
    text-align: left;
  }

  .suggestion:hover,
  .suggestion[aria-selected="true"] {
    background: var(--etu-search-hover-bg);
  }

  @media (max-width: 520px) {
    .root {
      flex-wrap: wrap;
    }

    .field {
      flex-basis: 100%;
      order: -1;
    }

    .mode {
      flex: 1 1 auto;
      max-width: none;
    }

    .languages {
      flex-wrap: wrap;
    }
  }
`

function toArray(value) {
  return (value || '')
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}

function readSuggestionText(item) {
  if (typeof item === 'string') return item
  if (!item || typeof item !== 'object') return ''
  return item.value || item.label || item.title || item.name || item.query || ''
}

function isAbsoluteUrl(value) {
  return /^[a-z][a-z\d+\-.]*:/i.test(value)
}

class EtuSearchInput extends HTMLElement {
  static formAssociated = true

  static get observedAttributes() {
    return [
      'api-base',
      'languages',
      'modes',
      'name',
      'placeholder',
      'query-param',
      'results-url',
      'submit-mode',
      'suggest-path',
      'target',
      'value',
    ]
  }

  constructor() {
    super()

    this.attachShadow({ mode: 'open' })

    this._internals = null
    if (typeof this.attachInternals === 'function') {
      try {
        this._internals = this.attachInternals()
      } catch {
        this._internals = null
      }
    }

    this._value = ''
    this._name = DEFAULT_NAME
    this._queryParam = DEFAULT_NAME
    this._placeholder = DEFAULT_PLACEHOLDER
    this._apiBase = ''
    this._suggestPath = DEFAULT_SUGGEST_PATH
    this._resultsUrl = ''
    this._submitMode = 'navigate'
    this._target = DEFAULT_TARGET
    this._languages = []
    this._selectedLangs = []
    this._modes = []
    this._activeModeId = DEFAULT_MODE_ID
    this._suggestions = []
    this._suggestionsOpen = false
    this._activeSuggestionIndex = -1
    this._debounceTimer = null
    this._abortController = null
    this._fallbackInput = null
    this._form = null
    this._isBooting = false

    this._handleFormSubmit = this._handleFormSubmit.bind(this)
    this._handleFormReset = this._handleFormReset.bind(this)
    this._handleInput = this._handleInput.bind(this)
    this._handleKeydown = this._handleKeydown.bind(this)
  }

  get value() {
    return this._value
  }

  set value(nextValue) {
    const value = nextValue == null ? '' : String(nextValue)
    this._value = value
    if (this._input && this._input.value !== value) {
      this._input.value = value
    }
    this._syncFormValue()
  }

  get form() {
    return this._internals?.form || this.closest('form')
  }

  connectedCallback() {
    this._upgradeProperty('value')
    this._isBooting = true
    if (!this.hasAttribute('name')) this.setAttribute('name', DEFAULT_NAME)
    this._isBooting = false

    if (!this._value && this.hasAttribute('value')) {
      this._value = this.getAttribute('value') || ''
    }

    this._parseConfig()
    this._ensureFallbackInput()
    this._render()
    this._syncFormValue()
    this._attachForm()
  }

  disconnectedCallback() {
    clearTimeout(this._debounceTimer)
    this._abortController?.abort()
    this._detachForm()
  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (oldValue === newValue || this._isBooting) return

    if (name === 'value') {
      this.value = newValue || ''
      return
    }

    if (!this.isConnected) return
    this._parseConfig()
    this._ensureFallbackInput()
    this._render()
    this._syncFormValue()
    this._attachForm()
  }

  formResetCallback() {
    this.value = this.getAttribute('value') || ''
    this._closeSuggestions()
  }

  formStateRestoreCallback(state) {
    this.value = state || ''
  }

  focus(options) {
    this._input?.focus(options)
  }

  _upgradeProperty(prop) {
    if (!Object.prototype.hasOwnProperty.call(this, prop)) return
    const value = this[prop]
    delete this[prop]
    this[prop] = value
  }

  _parseConfig() {
    this._name = this.getAttribute('name')?.trim() || DEFAULT_NAME
    this._queryParam = this.getAttribute('query-param')?.trim() || this._name
    this._placeholder = this.getAttribute('placeholder') || DEFAULT_PLACEHOLDER
    this._apiBase = this.getAttribute('api-base')?.trim() || ''
    this._suggestPath = this.getAttribute('suggest-path')?.trim() || DEFAULT_SUGGEST_PATH
    this._resultsUrl = this.getAttribute('results-url')?.trim() || ''
    this._submitMode = this.getAttribute('submit-mode') === 'event' ? 'event' : 'navigate'
    this._target = this.getAttribute('target')?.trim() || DEFAULT_TARGET
    this._languages = toArray(this.getAttribute('languages'))
    this._selectedLangs = this._selectedLangs.filter((lang) => this._languages.includes(lang))
    this._modes = this._parseModes()

    if (!this._modes.some((mode) => mode.id === this._activeModeId)) {
      this._activeModeId = this._modes[0]?.id || DEFAULT_MODE_ID
    }
  }

  _parseModes() {
    const rawModes = this.getAttribute('modes')
    if (!rawModes) return [this._fallbackMode()]

    try {
      const parsed = JSON.parse(rawModes)
      if (!Array.isArray(parsed) || parsed.length === 0) {
        throw new TypeError('modes must be a non-empty array')
      }

      const modes = parsed
        .map((mode) => ({
          id: String(mode.id || '').trim(),
          label: String(mode.label || mode.id || '').trim(),
          suggestPath: String(mode.suggestPath || '').trim(),
          resultsUrl: String(mode.resultsUrl || '').trim(),
        }))
        .filter((mode) => mode.id)

      if (!modes.length) throw new TypeError('modes must contain items with id')
      return modes
    } catch (error) {
      console.warn(`${ELEMENT_NAME}: invalid modes config, fallback mode is used.`, error)
      return [this._fallbackMode()]
    }
  }

  _fallbackMode() {
    return {
      id: DEFAULT_MODE_ID,
      label: 'Сайт',
      suggestPath: this._suggestPath,
      resultsUrl: this._resultsUrl,
    }
  }

  _render() {
    this.shadowRoot.innerHTML = `
      <style>${styles}</style>
      <div class="root" part="root">
        <div class="field" part="field">
          <input
            class="input"
            part="input"
            type="text"
            autocomplete="off"
            autocapitalize="off"
            spellcheck="false"
            role="combobox"
            aria-autocomplete="list"
            aria-expanded="false"
          />
        </div>
        <div class="languages" part="languages" role="group" aria-label="Язык поиска"></div>
        <select class="mode" part="mode-select" aria-label="Тип поиска"></select>
        <div class="suggestions" part="suggestions" role="listbox" hidden></div>
      </div>
    `

    this._modeSelect = this.shadowRoot.querySelector('.mode')
    this._languageGroup = this.shadowRoot.querySelector('.languages')
    this._input = this.shadowRoot.querySelector('.input')
    this._suggestionsList = this.shadowRoot.querySelector('.suggestions')

    const listboxId = `${ELEMENT_NAME}-suggestions-${Math.random().toString(36).slice(2)}`
    this._suggestionsList.id = listboxId
    this._input.setAttribute('aria-controls', listboxId)
    this._input.placeholder = this._placeholder
    this._input.value = this._value

    this._renderModeSelect()
    this._renderLanguages()
    this._renderSuggestions()

    this._input.addEventListener('input', this._handleInput)
    this._input.addEventListener('keydown', this._handleKeydown)
    this._input.addEventListener('focus', () => {
      if (this._suggestions.length) this._openSuggestions()
      else this._scheduleSuggestions(this.value)
    })
    this._input.addEventListener('blur', () => {
      setTimeout(() => this._closeSuggestions(), 120)
    })
  }

  _renderModeSelect() {
    if (this._modes.length <= 1) {
      this._modeSelect.hidden = true
      return
    }

    this._modeSelect.hidden = false
    this._modeSelect.textContent = ''
    this._modes.forEach((mode) => {
      const option = document.createElement('option')
      option.value = mode.id
      option.textContent = mode.label || mode.id
      option.selected = mode.id === this._activeModeId
      this._modeSelect.append(option)
    })

    this._modeSelect.addEventListener('change', () => {
      this._activeModeId = this._modeSelect.value
      this._clearSuggestions()
      this._scheduleSuggestions(this.value)
    })
  }

  _renderLanguages() {
    if (!this._languages.length) {
      this._languageGroup.hidden = true
      return
    }

    this._languageGroup.hidden = false
    this._languageGroup.textContent = ''
    this._languages.forEach((lang) => {
      const button = document.createElement('button')
      button.type = 'button'
      button.className = 'language'
      button.part = 'language'
      button.textContent = lang.toUpperCase()
      button.setAttribute('aria-label', `Язык ${lang}`)
      button.setAttribute('aria-pressed', String(this._selectedLangs.includes(lang)))
      button.addEventListener('click', () => this._toggleLang(lang))
      this._languageGroup.append(button)
    })
  }

  _renderSuggestions() {
    const shouldShow = this._suggestionsOpen && this._suggestions.length > 0
    this._suggestionsList.hidden = !shouldShow
    this._input?.setAttribute('aria-expanded', String(shouldShow))

    if (!shouldShow) {
      this._input?.removeAttribute('aria-activedescendant')
      this._suggestionsList.textContent = ''
      return
    }

    this._suggestionsList.textContent = ''
    this._suggestions.forEach((suggestion, index) => {
      const option = document.createElement('button')
      const optionId = `${this._suggestionsList.id}-option-${index}`
      option.type = 'button'
      option.id = optionId
      option.className = 'suggestion'
      option.part = 'suggestion'
      option.setAttribute('role', 'option')
      option.textContent = suggestion
      option.setAttribute('aria-selected', String(index === this._activeSuggestionIndex))
      option.addEventListener('mousedown', (event) => event.preventDefault())
      option.addEventListener('click', () => this._selectSuggestion(suggestion))
      this._suggestionsList.append(option)
    })

    if (this._activeSuggestionIndex >= 0) {
      const activeId = `${this._suggestionsList.id}-option-${this._activeSuggestionIndex}`
      this._input?.setAttribute('aria-activedescendant', activeId)
    } else {
      this._input?.removeAttribute('aria-activedescendant')
    }
  }

  _toggleLang(lang) {
    if (this._selectedLangs.includes(lang)) {
      this._selectedLangs = this._selectedLangs.filter((item) => item !== lang)
    } else {
      this._selectedLangs = [...this._selectedLangs, lang]
    }
    this._renderLanguages()
  }

  _handleInput(event) {
    this.value = event.target.value
    this.dispatchEvent(new Event('input', { bubbles: true, composed: true }))
    this._scheduleSuggestions(this.value)
  }

  _handleKeydown(event) {
    if (event.key === 'ArrowDown') {
      if (!this._suggestions.length) return
      event.preventDefault()
      this._suggestionsOpen = true
      this._activeSuggestionIndex = Math.min(
        this._activeSuggestionIndex + 1,
        this._suggestions.length - 1,
      )
      this._renderSuggestions()
      return
    }

    if (event.key === 'ArrowUp') {
      if (!this._suggestions.length) return
      event.preventDefault()
      this._suggestionsOpen = true
      this._activeSuggestionIndex = Math.max(this._activeSuggestionIndex - 1, 0)
      this._renderSuggestions()
      return
    }

    if (event.key === 'Escape') {
      this._closeSuggestions()
      return
    }

    if (event.key === 'Enter') {
      event.preventDefault()
      if (this._suggestionsOpen && this._activeSuggestionIndex >= 0) {
        this._selectSuggestion(this._suggestions[this._activeSuggestionIndex])
        return
      }
      this._submitFromInput()
    }
  }

  _selectSuggestion(suggestion) {
    this.value = suggestion
    this._closeSuggestions()
    this.dispatchEvent(new Event('input', { bubbles: true, composed: true }))
    this.dispatchEvent(new Event('change', { bubbles: true, composed: true }))
    this._input?.focus()
  }

  _scheduleSuggestions(query) {
    clearTimeout(this._debounceTimer)
    const normalizedQuery = query.trim()

    if (!normalizedQuery) {
      this._clearSuggestions()
      return
    }

    this._debounceTimer = setTimeout(() => {
      this._fetchSuggestions(normalizedQuery)
    }, DEBOUNCE_MS)
  }

  async _fetchSuggestions(query) {
    this._abortController?.abort()
    this._abortController = new AbortController()

    try {
      const url = this._buildSuggestUrl(query)
      const response = await fetch(url, { signal: this._abortController.signal })
      if (!response.ok) throw new Error(`Suggest request failed: ${response.status}`)

      const data = await response.json()
      const suggestions = Array.isArray(data) ? data : data.suggestions
      this._suggestions = (suggestions || []).map(readSuggestionText).filter(Boolean)
      this._activeSuggestionIndex = -1
      this._suggestionsOpen = this._suggestions.length > 0 && this.value.trim() === query
      this._renderSuggestions()
    } catch (error) {
      if (error.name === 'AbortError') return
      this._clearSuggestions()
    }
  }

  _buildSuggestUrl(query) {
    const mode = this._activeMode()
    const path = mode.suggestPath || this._suggestPath || DEFAULT_SUGGEST_PATH
    const base = this._apiBase ? new URL(this._apiBase, window.location.href).href : window.location.href
    const normalizedBase = isAbsoluteUrl(base) && !base.endsWith('/') ? `${base}/` : base
    const url = new URL(path, normalizedBase)
    url.searchParams.set('q', query)
    return url.href
  }

  _submitFromInput() {
    const form = this.form
    if (form?.requestSubmit) {
      form.requestSubmit()
      return
    }

    if (form) {
      const event = new Event('submit', { bubbles: true, cancelable: true })
      form.dispatchEvent(event)
      return
    }

    this._performSubmit()
  }

  _handleFormSubmit(event) {
    if (event.defaultPrevented) return
    this._performSubmit(event)
  }

  _handleFormReset() {
    this.formResetCallback()
  }

  _performSubmit(event) {
    const query = this.value.trim()
    event?.preventDefault()

    if (!query) {
      this.focus()
      return
    }

    this.value = query
    this._closeSuggestions()

    const detail = {
      query,
      lang: this._selectedLangs[0] || null,
      langs: [...this._selectedLangs],
      mode: this._activeMode().id,
      url: this._buildResultsUrl(query),
    }

    if (this._submitMode === 'event') {
      this.dispatchEvent(new CustomEvent('search-submit', {
        bubbles: true,
        composed: true,
        detail,
      }))
      return
    }

    if (this._target === '_blank') {
      window.open(detail.url, '_blank', 'noopener')
    } else {
      window.location.assign(detail.url)
    }
  }

  _buildResultsUrl(query) {
    const mode = this._activeMode()
    const rawResultsUrl = mode.resultsUrl || this._resultsUrl || this._formActionFallback()
    const base = mode.resultsUrl && this._resultsUrl
      ? new URL(this._resultsUrl, window.location.href).href
      : window.location.href
    const url = new URL(rawResultsUrl || window.location.pathname, base)

    url.searchParams.set(this._queryParam, query)
    url.searchParams.delete('lang')
    this._selectedLangs.forEach((lang) => url.searchParams.append('lang', lang))

    return url.href
  }

  _formActionFallback() {
    const form = this.form
    if (form?.getAttribute('action')) return form.action
    return window.location.pathname
  }

  _activeMode() {
    return this._modes.find((mode) => mode.id === this._activeModeId) || this._fallbackMode()
  }

  _openSuggestions() {
    this._suggestionsOpen = this._suggestions.length > 0
    this._renderSuggestions()
  }

  _closeSuggestions() {
    this._suggestionsOpen = false
    this._activeSuggestionIndex = -1
    this._renderSuggestions()
  }

  _clearSuggestions() {
    this._abortController?.abort()
    this._suggestions = []
    this._suggestionsOpen = false
    this._activeSuggestionIndex = -1
    this._renderSuggestions()
  }

  _ensureFallbackInput() {
    if (this._internals) return

    if (!this._fallbackInput) {
      this._fallbackInput = document.createElement('input')
      this._fallbackInput.type = 'hidden'
      this.append(this._fallbackInput)
    }
  }

  _syncFormValue() {
    this._internals?.setFormValue(this._value)

    if (this._fallbackInput) {
      this._fallbackInput.name = this._name
      this._fallbackInput.value = this._value
    }
  }

  _attachForm() {
    const form = this.form
    if (form === this._form) return

    this._detachForm()
    this._form = form

    if (this._form) {
      this._form.addEventListener('submit', this._handleFormSubmit)
      this._form.addEventListener('reset', this._handleFormReset)
    }
  }

  _detachForm() {
    if (!this._form) return
    this._form.removeEventListener('submit', this._handleFormSubmit)
    this._form.removeEventListener('reset', this._handleFormReset)
    this._form = null
  }
}

if (!customElements.get(ELEMENT_NAME)) {
  customElements.define(ELEMENT_NAME, EtuSearchInput)
}

export { EtuSearchInput }
