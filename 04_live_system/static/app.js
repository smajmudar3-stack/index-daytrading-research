// Partial refresh.
//
// The page used <meta http-equiv=refresh content=60>, which reloaded everything
// every 60 seconds. The five tabs were CSS-only radio buttons with no address of
// their own, so the tab you were reading RESET on every refresh, along with your
// scroll position and any open disclosure. That is most of what made the dashboard
// feel like it was fighting you.
//
// Now each view is a real URL, and the refresh swaps only <main> in place.
(function () {
  var EVERY_MS = 60000;
  var main = document.getElementById('view');
  if (!main) return;

  function stamp(text, severity) {
    var s = document.querySelector('.status');
    if (!s) return;
    var chip = s.querySelector('.chip[data-live]');
    if (!chip) {
      chip = document.createElement('span');
      chip.className = 'chip';
      chip.setAttribute('data-live', '1');
      s.appendChild(chip);
    }
    chip.textContent = text;
    chip.className = 'chip ' + (severity || '');
  }

  function refresh() {
    // Remember which disclosures are open, so a refresh does not close them.
    var open = [];
    main.querySelectorAll('details[open]').forEach(function (d) {
      if (d.closest('section')) open.push(d.closest('section').id + '|' + (d.querySelector('summary') || {}).textContent);
    });

    fetch(window.location.pathname + '?partial=1', { headers: { 'X-Partial': '1' } })
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.text();
      })
      .then(function (html) {
        main.innerHTML = html;
        main.querySelectorAll('details').forEach(function (d) {
          var id = (d.closest('section') || {}).id + '|' + (d.querySelector('summary') || {}).textContent;
          if (open.indexOf(id) !== -1) d.open = true;
        });
        stamp('updated ' + new Date().toLocaleTimeString(), '');
      })
      .catch(function (e) {
        // A failed refresh must SAY it failed. The old page could not tell you the
        // difference between fresh data and a server that had stopped answering.
        stamp('refresh failed: ' + e.message, 'stop');
      });
  }

  window.__idtRefreshView = refresh;
  setInterval(refresh, EVERY_MS);
})();

// ---------------------------------------------------------------- refresh status
// "Refresh the desk" used to return a 302 instantly whether or not anything
// happened, so a no-op looked identical to a completed cycle. Now the button
// starts a background cycle and this polls its real state.
(function () {
  var link = document.querySelector('a.refresh');
  if (!link) return;
  var chip = document.createElement('span');
  chip.className = 'chip';
  chip.setAttribute('data-refresh', '1');
  link.parentNode.insertBefore(chip, link.nextSibling);

  var timer = null;

  function show(s) {
    if (s.state === 'running') {
      var secs = s.started_ago_s || 0;
      chip.textContent = 'refreshing the desk… ' + secs + 's';
      chip.className = 'chip watch';
      link.textContent = 'Refreshing…';
      link.style.pointerEvents = 'none';
      link.style.opacity = '0.6';
      return true;
    }
    link.textContent = 'Refresh the desk';
    link.style.pointerEvents = '';
    link.style.opacity = '';
    if (s.state === 'failed') {
      chip.textContent = 'refresh FAILED: ' + (s.error || 'unknown');
      chip.className = 'chip stop';
    } else if (s.state === 'done') {
      var ago = s.finished_ago_s || 0;
      chip.textContent = 'desk rebuilt ' + (ago < 60 ? ago + 's' : Math.round(ago / 60) + 'm') + ' ago';
      chip.className = 'chip';
      // a completed cycle wrote new snapshots — pull them in
      if (ago < 5 && window.__idtRefreshView) window.__idtRefreshView();
    } else {
      chip.textContent = '';
      chip.className = 'chip';
    }
    return false;
  }

  function poll() {
    fetch('/refresh_status', { cache: 'no-store' })
      .then(function (r) { return r.json(); })
      .then(function (s) {
        var running = show(s);
        if (timer) clearTimeout(timer);
        timer = setTimeout(poll, running ? 1000 : 15000);
      })
      .catch(function () {
        if (timer) clearTimeout(timer);
        timer = setTimeout(poll, 15000);
      });
  }

  link.addEventListener('click', function () {
    chip.textContent = 'starting…';
    chip.className = 'chip watch';
    setTimeout(poll, 400);
  });

  poll();
})();
