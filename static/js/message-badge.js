/* Live unread-message badge updater.
   Polls /api/unread-count/ every 8 seconds and updates the navbar badge.
   Skips polling on active chat pages (messages are marked read there). */
(function () {
    'use strict';

    var path = window.location.pathname;
    if (path.indexOf('/chat/') === 0) return;

    function updateBadge(count) {
        var links = document.querySelectorAll('a[href*="inbox"]');
        for (var i = 0; i < links.length; i++) {
            var link = links[i];
            var badge = link.querySelector('.message-badge');

            if (count > 0) {
                var text = count > 99 ? '99+' : String(count);
                if (badge) {
                    badge.textContent = text;
                } else {
                    badge = document.createElement('span');
                    badge.className = 'badge rounded-pill bg-danger ms-1 message-badge';
                    badge.textContent = text;
                    link.appendChild(badge);
                }
            } else if (badge) {
                badge.remove();
            }
        }
    }

    function poll() {
        fetch('/api/unread-count/', { credentials: 'same-origin' })
            .then(function (res) { return res.ok ? res.json() : null; })
            .then(function (data) { if (data) updateBadge(data.unread); })
            .catch(function () {});
    }

    /* Initial poll after a short delay, then every 8 seconds */
    setTimeout(poll, 1500);
    setInterval(poll, 8000);
})();
