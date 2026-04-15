/**
 * Skillify — Form Loading Spinners
 * Automatically shows a spinner on submit buttons when a form is submitted.
 * Works with any submit button that has data-loading-text or falls back to "Processing..."
 * Safe: 20-second auto-reset in case of navigation failure.
 */
document.addEventListener('DOMContentLoaded', function () {

  document.querySelectorAll('form').forEach(function (form) {
    form.addEventListener('submit', function () {

      // Find the first enabled submit button in this form
      var btn = form.querySelector('button[type="submit"]:not([disabled]), input[type="submit"]:not([disabled])');
      if (!btn) return;

      // Don't double-fire (e.g. if JS validation re-submits)
      if (btn.dataset.loading === 'true') return;
      btn.dataset.loading = 'true';

      var originalHtml = btn.innerHTML;
      var loadingText  = btn.dataset.loadingText || 'Processing...';

      btn.disabled = true;
      btn.innerHTML =
        '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>' +
        loadingText;

      // Safety reset after 20 s in case page doesn't navigate away
      setTimeout(function () {
        btn.disabled     = false;
        btn.innerHTML    = originalHtml;
        btn.dataset.loading = 'false';
      }, 20000);
    });
  });

});
