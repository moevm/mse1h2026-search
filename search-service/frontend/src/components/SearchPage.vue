<script setup>
import SearchBar from './SearchBar.vue'
import logo from '../assets/etu-ru-logo.svg'

defineProps({
  query: { type: String, required: true },
  showButtons: { type: Boolean, default: false },
  dropdownOpen: { type: Boolean, default: false },
  dropdownItems: { type: Array, default: () => [] },
  dropdownMode: { type: String, default: 'recent' },
})

const emit = defineEmits([
  'update:query',
  'search',
  'focus',
  'blur',
  'input',
  'clear',
  'select-item',
  'go-home',
])
</script>

<template>
  <div class="page-search">
    <div class="search-logo" title="На главную" @click="emit('go-home')">
      <img class="logo-svg" :src="logo" alt="СПбГЭТУ ЛЭТИ" />
    </div>

    <div class="search-wrap">
      <SearchBar
        :model-value="query"
        :show-buttons="showButtons"
        :dropdown-open="dropdownOpen"
        :dropdown-items="dropdownItems"
        :dropdown-mode="dropdownMode"
        @update:model-value="emit('update:query', $event)"
        @search="emit('search')"
        @focus="emit('focus')"
        @blur="emit('blur')"
        @input="emit('input')"
        @clear="emit('clear')"
        @select-item="emit('select-item', $event)"
      />
    </div>
  </div>
</template>

<style scoped>
.page-search {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 40px 20px 80px;
}

.search-logo {
    cursor: pointer;
    margin-bottom: 32px;
}

.logo-svg {
    width: 130px;
    height: 130px;
    display: block;
}

.search-wrap {
    width: 100%;
    max-width: 560px;
    position: relative;
}

.search-wrap :deep(.search-bar) {
    border-radius: 28px;
}

.search-wrap :deep(.search-input) {
    padding: 13px 4px 13px 0;
    font-size: 16px;
}

.search-wrap :deep(.btn-search) {
    padding: 9px 22px;
    font-size: 15px;
}
</style>
