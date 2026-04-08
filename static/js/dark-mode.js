/* ============================================
   SKILLIFY GLOBAL DARK MODE
   - Persists via localStorage key 'skillify-theme'
   - Sets data-theme="dark" on <html>
   - Auto-creates floating toggle button on every page
   - Syncs across browser tabs via storage event
   ============================================ */

(function () {
    'use strict';

    var STORAGE_KEY = 'skillify-theme';

    function getSavedTheme() {
        try {
            return localStorage.getItem(STORAGE_KEY) || 'light';
        } catch (e) {
            return 'light';
        }
    }

    function applyTheme(theme) {
        var root = document.documentElement;
        if (theme === 'dark') {
            root.setAttribute('data-theme', 'dark');
        } else {
            root.removeAttribute('data-theme');
        }
        updateToggleIcon(theme);
    }

    function saveTheme(theme) {
        try {
            localStorage.setItem(STORAGE_KEY, theme);
        } catch (e) { /* ignore */ }
    }

    function currentTheme() {
        return document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
    }

    function toggleTheme() {
        var next = currentTheme() === 'dark' ? 'light' : 'dark';
        applyTheme(next);
        saveTheme(next);
    }

    function updateToggleIcon(theme) {
        var btn = document.getElementById('skillify-theme-toggle');
        if (!btn) return;
        btn.innerHTML = theme === 'dark' ? '☀️' : '🌙';
        btn.setAttribute('aria-label', theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode');
        btn.setAttribute('title', theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode');
    }

    function bindExistingToggles() {
        /* Bind any existing toggle buttons (legacy #themeToggle or .theme-toggle).
           Returns true if at least one was found. */
        var bound = false;
        var legacy = document.getElementById('themeToggle');
        if (legacy) {
            legacy.addEventListener('click', toggleTheme);
            bound = true;
        }
        var classList = document.querySelectorAll('.theme-toggle');
        for (var i = 0; i < classList.length; i++) {
            if (classList[i].id !== 'themeToggle') {
                classList[i].addEventListener('click', toggleTheme);
            }
            bound = true;
        }
        return bound;
    }

    function createToggleButton() {
        if (document.getElementById('skillify-theme-toggle')) return;
        /* If the page already has a toggle button, just wire it up. */
        if (bindExistingToggles()) return;
        var btn = document.createElement('button');
        btn.id = 'skillify-theme-toggle';
        btn.type = 'button';
        btn.addEventListener('click', toggleTheme);
        document.body.appendChild(btn);
        updateToggleIcon(currentTheme());
    }

    /* Apply saved theme IMMEDIATELY (before DOMContentLoaded) so there is no FOUC */
    applyTheme(getSavedTheme());

    /* Create floating button once DOM is ready */
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', createToggleButton);
    } else {
        createToggleButton();
    }

    /* Sync across tabs */
    window.addEventListener('storage', function (e) {
        if (e.key === STORAGE_KEY && e.newValue) {
            applyTheme(e.newValue);
        }
    });

    /* Expose helper globally (optional) */
    window.SkillifyTheme = {
        toggle: toggleTheme,
        set: function (t) { applyTheme(t); saveTheme(t); },
        get: currentTheme
    };
})();
