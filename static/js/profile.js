document.addEventListener('DOMContentLoaded', function() {
    // Theme Toggle
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        const savedTheme = localStorage.getItem('theme') || 'light';
        if (savedTheme === 'dark') {
            document.body.classList.add('dark-theme');
            themeToggle.innerHTML = '<i class="bi bi-sun-fill"></i>';
        }
        themeToggle.addEventListener('click', function() {
            document.body.classList.toggle('dark-theme');
            const isDark = document.body.classList.contains('dark-theme');
            localStorage.setItem('theme', isDark ? 'dark' : 'light');
            this.innerHTML = isDark ? '<i class="bi bi-sun-fill"></i>' : '<i class="bi bi-moon-stars-fill"></i>';
        });
    }

    // Auto-dismiss alerts after 5 seconds
    document.querySelectorAll('.alert-dismissible').forEach(function(alert) {
        setTimeout(function() {
            var bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) bsAlert.close();
        }, 5000);
    });
});
