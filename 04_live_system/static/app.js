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

  setInterval(refresh, EVERY_MS);
})();
