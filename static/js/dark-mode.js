/* Global Dark Mode + Theme Toggle
   Include this on EVERY page before </body> */
(function() {
    // Apply saved theme immediately (prevents flash)
    const saved = localStorage.getItem('theme') || 'light';
    if (saved === 'dark') {
        document.body.classList.add('dark-theme');
    }

    // Setup toggle button
    document.addEventListener('DOMContentLoaded', function() {
        const btn = document.getElementById('themeToggle');
        if (!btn) return;

        // Set correct icon on load
        const isDark = document.body.classList.contains('dark-theme');
        btn.innerHTML = isDark
            ? '<i class="bi bi-sun-fill"></i>'
            : '<i class="bi bi-moon-stars-fill"></i>';

        btn.addEventListener('click', function() {
            document.body.classList.toggle('dark-theme');
            const nowDark = document.body.classList.contains('dark-theme');
            localStorage.setItem('theme', nowDark ? 'dark' : 'light');
            this.innerHTML = nowDark
                ? '<i class="bi bi-sun-fill"></i>'
                : '<i class="bi bi-moon-stars-fill"></i>';
        });
    });
})();
