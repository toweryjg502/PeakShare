(() => {
  const counter = document.getElementById('booking-alert-count');
  const toast = document.getElementById('booking-alert-toast');
  const message = document.getElementById('booking-alert-toast-message');
  const close = document.getElementById('booking-alert-toast-close');
  if (!counter || !toast || !message || !close) return;

  let latestId = Number(counter.dataset.latestId || 0);
  let dismissTimer;

  close.addEventListener('click', () => {
    toast.hidden = true;
    window.clearTimeout(dismissTimer);
  });

  async function refreshAlerts() {
    try {
      if (document.hidden) return;
      const response = await fetch(counter.dataset.statusUrl, {
        credentials: 'same-origin',
        cache: 'no-store',
        headers: { Accept: 'application/json' },
      });
      if (!response.ok) return;

      const data = await response.json();
      counter.dataset.count = String(data.unread_count);
      counter.textContent = String(data.unread_count);
      counter.hidden = data.unread_count < 1;

      if (data.latest && data.latest.id > latestId) {
        latestId = data.latest.id;
        counter.dataset.latestId = String(latestId);
        message.textContent = data.latest.message;
        toast.hidden = false;
        window.clearTimeout(dismissTimer);
        dismissTimer = window.setTimeout(() => { toast.hidden = true; }, 10000);
      }
    } catch (_error) {
      // A missed poll is harmless; the next page load refreshes the alert count.
    }
  }

  window.setInterval(refreshAlerts, 15000);
})();
