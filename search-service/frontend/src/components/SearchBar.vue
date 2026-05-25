<script setup>
import { ref, inject, nextTick } from 'vue'

defineProps({
  modelValue: { type: String, required: true },
  showButtons: { type: Boolean, default: false },
  dropdownOpen: { type: Boolean, default: false },
  dropdownItems: { type: Array, default: () => [] },
  dropdownMode: { type: String, default: 'recent' }, // 'recent' | 'suggestions'
})

const emit = defineEmits([
  'update:modelValue',
  'search',
  'focus',
  'blur',
  'input',
  'clear',
  'select-item',
])

const highlightDrop = inject('highlightDrop')

const inputEl = ref(null)

function focus() {
  inputEl.value?.focus()
}

defineExpose({ focus })

function handleClear() {
  emit('clear')
  nextTick(() => inputEl.value?.focus())
}
</script>

<template>
  <div class="search-bar" :class="{ active: showButtons }">
    <input
      ref="inputEl"
      type="text"
      class="search-input"
      :placeholder="showButtons ? '' : 'Найти информацию'"
      :value="modelValue"
      autocomplete="off"
      spellcheck="false"
      @input="emit('update:modelValue', $event.target.value); emit('input')"
      @focus="emit('focus')"
      @blur="emit('blur')"
      @keydown.enter.prevent="emit('search')"
    />
    <button
      v-if="showButtons && modelValue"
      class="btn-clear"
      aria-label="Очистить"
      @mousedown.prevent
      @click="handleClear"
    >&times;</button>
    <button
      v-if="showButtons"
      class="btn-search"
      @mousedown.prevent
      @click="emit('search')"
    >Поиск</button>
  </div>

  <transition name="dropdown-fade">
    <div v-if="dropdownOpen && dropdownItems.length" class="dropdown">
      <div
        v-for="(item, i) in dropdownItems"
        :key="i"
        class="dropdown-item"
        @mousedown.prevent
        @click="emit('select-item', item)"
      >
        <span class="dropdown-icon">
          <svg
            v-if="dropdownMode === 'recent'"
            viewBox="0 0 16 16"
            width="14"
            height="14"
            fill="none"
            stroke="currentColor"
            stroke-width="1.5"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <circle cx="8" cy="8" r="6.5" />
            <polyline points="8,4.5 8,8 10.5,10" />
          </svg>
          <svg
            v-else
            viewBox="0 0 16 16"
            width="14"
            height="14"
            fill="none"
            stroke="currentColor"
            stroke-width="1.5"
            stroke-linecap="round"
          >
            <circle cx="6.5" cy="6.5" r="5" />
            <line x1="10.5" y1="10.5" x2="14" y2="14" />
          </svg>
        </span>
        <span v-html="highlightDrop(item)"></span>
      </div>
    </div>
  </transition>
</template>

<style scoped>
.search-bar {
    display: flex;
    align-items: center;
    background: var(--bg);
    border: 1.5px solid var(--border);
    border-radius: 24px;
    padding: 0 4px 0 16px;
    transition: border-color .2s, box-shadow .2s;
    position: relative;
}

.search-bar:focus-within,
.search-bar.active {
    border-color: var(--blue);
    box-shadow: 0 0 0 3px rgba(0, 48, 135, .08);
}

.search-input {
    flex: 1;
    border: none;
    outline: none;
    background: transparent;
    font-size: 15px;
    color: var(--text);
    padding: 10px 4px 10px 0;
    min-width: 0;
}

.search-input::placeholder {
    color: #999;
}

.btn-clear {
    background: none;
    border: none;
    cursor: pointer;
    color: #999;
    font-size: 18px;
    line-height: 1;
    padding: 6px 8px;
    border-radius: 50%;
    transition: color .15s, background .15s;
}

.btn-clear:hover {
    color: var(--text);
    background: var(--blue-light);
}

.btn-search {
    background: var(--blue);
    color: #fff;
    border: none;
    cursor: pointer;
    font-size: 14px;
    font-weight: 600;
    padding: 7px 18px;
    border-radius: 20px;
    margin: 3px;
    transition: background .15s;
    white-space: nowrap;
}

.btn-search:hover {
    background: var(--blue-hover);
}

.dropdown {
    position: absolute;
    top: calc(100% + 4px);
    left: 0;
    right: 0;
    background: var(--bg);
    border: 1.5px solid var(--border);
    border-radius: var(--radius);
    box-shadow: var(--shadow-md);
    z-index: 100;
    overflow: hidden;
}

.dropdown-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 9px 14px;
    cursor: pointer;
    font-size: 14px;
    color: var(--text);
    transition: background .12s;
}

.dropdown-item:hover {
    background: var(--blue-light);
}

.dropdown-icon {
    color: var(--text-muted);
    flex-shrink: 0;
    display: flex;
    align-items: center;
}

.dropdown-item :deep(strong) {
    color: var(--text);
}

.dropdown-fade-enter-active {
    transition: opacity .15s, transform .15s;
}

.dropdown-fade-leave-active {
    transition: opacity .1s;
}

.dropdown-fade-enter-from {
    opacity: 0;
    transform: translateY(-4px);
}

.dropdown-fade-leave-to {
    opacity: 0;
}
</style>
