// Skillify - Login/Registration JS (Django-compatible)
// This replaces the original JS to work with Django form submissions

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

    // Password Toggle
    const togglePassword = document.getElementById('togglePassword');
    if (togglePassword) {
        togglePassword.addEventListener('click', function() {
            const passwordInput = document.getElementById('password');
            const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
            passwordInput.setAttribute('type', type);
            this.querySelector('i').classList.toggle('bi-eye');
            this.querySelector('i').classList.toggle('bi-eye-slash');
        });
    }

    const toggleConfirmPassword = document.getElementById('toggleConfirmPassword');
    if (toggleConfirmPassword) {
        toggleConfirmPassword.addEventListener('click', function() {
            const confirmInput = document.getElementById('confirmPassword');
            const type = confirmInput.getAttribute('type') === 'password' ? 'text' : 'password';
            confirmInput.setAttribute('type', type);
            this.querySelector('i').classList.toggle('bi-eye');
            this.querySelector('i').classList.toggle('bi-eye-slash');
        });
    }

    // Password Strength Indicator (register page)
    const passwordInput = document.getElementById('password');
    const strengthFill = document.getElementById('strengthFill');
    const strengthText = document.getElementById('strengthText');
    if (passwordInput && strengthFill) {
        passwordInput.addEventListener('input', function() {
            const password = this.value;
            let strength = 0;
            if (password.length >= 6) strength++;
            if (password.length >= 8) strength++;
            if (/[A-Z]/.test(password)) strength++;
            if (/[0-9]/.test(password)) strength++;
            if (/[^A-Za-z0-9]/.test(password)) strength++;

            const percent = (strength / 5) * 100;
            strengthFill.style.width = percent + '%';

            const colors = ['#dc3545', '#dc3545', '#ffc107', '#28a745', '#28a745'];
            const labels = ['Very Weak', 'Weak', 'Fair', 'Strong', 'Very Strong'];
            strengthFill.style.backgroundColor = colors[Math.min(strength, 4)];
            if (strengthText) strengthText.textContent = labels[Math.min(strength, 4)];
        });
    }

    // Confirm Password Match
    const confirmPassword = document.getElementById('confirmPassword');
    const passwordMismatch = document.getElementById('passwordMismatch');
    if (confirmPassword && passwordMismatch) {
        confirmPassword.addEventListener('input', function() {
            if (this.value && passwordInput && this.value !== passwordInput.value) {
                passwordMismatch.textContent = 'Passwords do not match';
                passwordMismatch.style.color = '#dc3545';
            } else {
                passwordMismatch.textContent = '';
            }
        });
    }

    // Register form - client-side validation only, then let Django handle submission
    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        registerForm.addEventListener('submit', function(e) {
            const pass = document.getElementById('password').value;
            const confirm = document.getElementById('confirmPassword').value;
            if (pass !== confirm) {
                e.preventDefault();
                alert('Passwords do not match!');
                return false;
            }
            const terms = document.getElementById('terms');
            if (terms && !terms.checked) {
                e.preventDefault();
                alert('Please accept the Terms & Conditions.');
                return false;
            }
            // Form submits normally to Django via POST
        });
    }

    // Login form - submits normally to Django via POST
    // No JS interception - Django handles auth and redirect
});
