/* global Vue */
const API_BASE = window.API_BASE || '';
const isEmbed = new URLSearchParams(window.location.search).get('embed') === 'true';

const { createApp } = Vue;

createApp({
    data() {
        return {
            inResults: false,
            isEmbed,

            resultStatus: 'loading', // 'loading' | 'ok' | 'empty' | 'error'

            query: '',
            lastQuery: '',

            dropdownOpen: false,
            isTyping: false, // true = suggestions mode, false = recent searches mode

            results: [],
            suggestions: [],
            total: 0,
            recentSearches: (() => {
                try { return JSON.parse(localStorage.getItem('leti_recent') || '[]'); }
                catch { return []; }
            })(),

            selectedLang: null,
            sortBy: 'relevance',
            dateFilter: null,
            fromDate: null,
            toDate: null,

            languages: ['RU', 'EN', 'DE', 'ES', 'FR', 'PT', 'ZH', 'VI'],
            dateOptions: [
                { label: 'За последний месяц', value: 'month' },
                { label: 'За год', value: 'year' },
                { label: 'За 3 года', value: '3years' },
            ],

            debounceTimer: null,
        };
    },

    computed: {
        showButtons() {
            return this.inResults || this.dropdownOpen;
        },
        dropdownItems() {
            if (!this.dropdownOpen) return [];
            return this.isTyping ? this.suggestions : this.recentSearches;
        },
        dropdownMode() {
            return this.isTyping ? 'suggestions' : 'recent';
        },
    },

    watch: {
        selectedLang() { if (this.inResults) this.doSearch(); },
        sortBy() { if (this.inResults) this.doSearch(); },
        dateFilter(val) { if (this.inResults && val !== null) this.doSearch(); },
        fromDate() { this.dateFilter = null; if (this.inResults) this.doSearch(); },
        toDate() { this.dateFilter = null; if (this.inResults) this.doSearch(); },
    },

    methods: {
        onFocus() {
            this.isTyping = !!(this.query.trim() && this.suggestions.length);
            this.dropdownOpen = true;
        },

        onBlur() {
            // Delay so mousedown on dropdown items fires before dropdown closes
            setTimeout(() => { this.dropdownOpen = false; }, 200);
        },

        onInput() {
            if (!this.query.trim()) {
                this.isTyping = false;
                this.suggestions = [];
                this.dropdownOpen = true;
                return;
            }
            this.isTyping = true;
            this.dropdownOpen = true;
            clearTimeout(this.debounceTimer);
            this.debounceTimer = setTimeout(this.fetchSuggestions, 300);
        },

        async fetchSuggestions() {
            try {
                const res = await fetch(`${API_BASE}/api/suggest?q=${encodeURIComponent(this.query)}`);
                if (!res.ok) { this.suggestions = []; return; }
                const data = await res.json();
                this.suggestions = data.suggestions || [];
            } catch {
                this.suggestions = [];
            }
        },

        async doSearch(q) {
            q = (q !== undefined ? q : this.query).trim();
            if (!q) return;

            this.query = q;
            this.lastQuery = q;
            this.dropdownOpen = false;
            this.inResults = true;
            this.resultStatus = 'loading';

            // Persist to recent searches
            const recent = [q, ...this.recentSearches.filter(r => r !== q)].slice(0, 5);
            this.recentSearches = recent;
            try { localStorage.setItem('leti_recent', JSON.stringify(recent)); } catch { /* ignore */ }

            // Reflect query in URL
            const params = new URLSearchParams(window.location.search);
            params.set('q', q);
            if (this.isEmbed) params.set('embed', 'true');
            window.history.replaceState({}, '', `?${params}`);

            try {
                const searchParams = new URLSearchParams({ q, page: 1, page_size: 10 });
                if (this.selectedLang) searchParams.set('lang', this.selectedLang);
                if (this.sortBy && this.sortBy !== 'relevance') searchParams.set('sort_by', this.sortBy);
                if (this.dateFilter) {
                    searchParams.set('date_filter', this.dateFilter);
                } else {
                    if (this.fromDate) searchParams.set('from_date', this.formatDateForQuery(this.fromDate));
                    if (this.toDate) searchParams.set('to_date', this.formatDateForQuery(this.toDate));
                }

                const res = await fetch(`${API_BASE}/api/search?${searchParams}`);
                if (!res.ok) { this.resultStatus = 'error'; return; }
                const data = await res.json();
                this.results = data.results || [];
                this.total = data.total || 0;
                this.resultStatus = this.results.length ? 'ok' : 'empty';
            } catch {
                this.resultStatus = 'error';
            }
        },

        clearInput() {
            this.query = '';
            this.suggestions = [];
            this.isTyping = false;
            this.dropdownOpen = true;
            this.$nextTick(() => {
                const el = this.$refs.searchInput || this.$refs.resultsSearchInput;
                el?.focus();
            });
        },

        clearAll() {
            this.query = '';
            this.lastQuery = '';
            this.results = [];
            this.suggestions = [];
            this.inResults = false;
            this.dropdownOpen = false;
            this.isTyping = false;
            const params = new URLSearchParams(window.location.search);
            params.delete('q');
            const qs = params.toString();
            window.history.replaceState({}, '', qs ? `?${qs}` : window.location.pathname);
        },

        toggleLang(lang) {
            this.selectedLang = this.selectedLang === lang ? null : lang;
        },

        formatDateForQuery(dateStr) {
            if (!dateStr) return null;
            const [y, m, d] = dateStr.split('-');
            return `${d}-${m}-${y}`;
        },

        // XSS-safe: escape HTML entities, then bold-wrap query matches
        escHtml(str) {
            return str
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;');
        },

        // Highlight lastQuery (the submitted search term) in result text
        highlight(text) {
            if (!text) return '';
            const safe = this.escHtml(text);
            const q = this.lastQuery.trim();
            if (!q) return safe;
            const re = new RegExp(`(${q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
            return safe.replace(re, '<strong>$1</strong>');
        },

        // Highlight current query (as user types) in dropdown items
        highlightDrop(text) {
            if (!text) return '';
            const safe = this.escHtml(text);
            const q = this.query.trim();
            if (!q) return safe;
            const re = new RegExp(`(${q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
            return safe.replace(re, '<strong>$1</strong>');
        },
    },

    mounted() {
        const params = new URLSearchParams(window.location.search);
        const urlQ = params.get('q');
        if (urlQ) {
            this.query = urlQ;
            this.doSearch(urlQ);
        }
    },
}).mount('#app');
