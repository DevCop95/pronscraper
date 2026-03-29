(function() {
    function updateClock() {
        const now = new Date();
        const utc = now.getTime() + (now.getTimezoneOffset() * 60000);
        const col = new Date(utc + (-5 * 3600000));
        const h = String(col.getHours()).padStart(2, '0');
        const m = String(col.getMinutes()).padStart(2, '0');
        const s = String(col.getSeconds()).padStart(2, '0');
        const el = document.getElementById('live-clock');
        if (el) el.textContent = h + ':' + m + ':' + s;
    }
    updateClock();
    setInterval(updateClock, 1000);

    const KEY = 'sport_v5';
    try {
        const creatorModalEl = document.getElementById('creatorModal');
        if (creatorModalEl && !localStorage.getItem(KEY)) {
            new bootstrap.Modal(creatorModalEl).show();
        }
        const enterBtn = document.getElementById('enterBtn');
        if (enterBtn) {
            enterBtn.addEventListener('click', () => {
                try { localStorage.setItem(KEY, '1'); } catch (_) {}
            });
        }
    } catch (_) {}

    const allCards = [...document.querySelectorAll('.card-match')];
    let aT = 'ALL',
        aC = 'ALL';

    function render() {
        let visible = 0;
        allCards.forEach((c) => {
            const ok = (aT === 'ALL' || c.dataset.tier === aT) && (aC === 'ALL' || c.dataset.comp === aC);
            c.style.display = ok ? '' : 'none';
            if (ok) {
                c.style.animationDelay = (visible * 0.04) + 's';
                visible++;
            }
        });
        const emptyState = document.getElementById('empty-state');
        if (emptyState) emptyState.classList.toggle('d-none', visible > 0);
    }

    document.querySelectorAll('.tier-btn').forEach(b => b.addEventListener('click', () => {
        document.querySelectorAll('.tier-btn').forEach(x => x.classList.remove('active'));
        b.classList.add('active');
        aT = b.dataset.t;
        render();
    }));

    document.querySelectorAll('.comp-chip').forEach(b => b.addEventListener('click', () => {
        document.querySelectorAll('.comp-chip').forEach(x => x.classList.remove('active'));
        b.classList.add('active');
        aC = b.dataset.comp;
        render();
    }));
})();
