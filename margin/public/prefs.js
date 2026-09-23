// Applies reading settings before the page paints (no flash of the wrong
// size or theme). Loaded in <head>; the settings panel lives in ui.js.
(function () {
  'use strict';
  try {
    var p = JSON.parse(localStorage.getItem('margin:prefs') || '{}');
    var root = document.documentElement;
    if (p.size && p.size !== 'm') root.setAttribute('data-size', p.size);
    if (p.theme === 'light' || p.theme === 'dark') root.setAttribute('data-theme', p.theme);
  } catch (e) { /* storage blocked: system defaults apply */ }
})();
