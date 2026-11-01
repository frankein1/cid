// docs/aide/aide.js – agrandissement des vignettes des fiches d'aide CID
(function () {
  var zoom = document.createElement('div');
  zoom.id = 'zoom'; zoom.setAttribute('role', 'dialog'); zoom.setAttribute('aria-label', 'Image agrandie');
  var grand = document.createElement('img'); zoom.appendChild(grand); document.body.appendChild(zoom);
  document.querySelectorAll('figure img').forEach(function (i) {
    i.addEventListener('click', function () { grand.src = i.src; grand.alt = i.alt; zoom.classList.add('ouvert'); });
  });
  zoom.addEventListener('click', function () { zoom.classList.remove('ouvert'); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') zoom.classList.remove('ouvert'); });
})();
