(() => {
  const toggle = document.getElementById('menuToggle');
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('mobileOverlay');
  const closeMenu = () => {
    sidebar?.classList.remove('is-open');
    overlay?.classList.remove('is-open');
    toggle?.setAttribute('aria-expanded', 'false');
  };
  toggle?.addEventListener('click', () => {
    const opening = !sidebar?.classList.contains('is-open');
    sidebar?.classList.toggle('is-open', opening);
    overlay?.classList.toggle('is-open', opening);
    toggle?.setAttribute('aria-expanded', String(opening));
  });
  overlay?.addEventListener('click', closeMenu);
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeMenu(); });

  document.querySelectorAll('.flash-close').forEach(btn => {
    btn.addEventListener('click', () => btn.closest('.flash')?.remove());
  });

  // Confirmar operações de risco. O servidor continua verificando permissões.
  document.querySelectorAll('form[data-confirm]').forEach(form => {
    form.addEventListener('submit', e => {
      if (!window.confirm(form.dataset.confirm)) e.preventDefault();
    });
  });

  const tabs = document.querySelectorAll('button[data-tab]');
  tabs.forEach(tab => tab.addEventListener('click', () => {
    tabs.forEach(other => {
      const active = other === tab;
      other.classList.toggle('active', active);
      other.setAttribute('aria-selected', String(active));
      const panel = document.getElementById('tab-' + other.dataset.tab);
      if (panel) panel.hidden = !active;
    });
  }));

  const imageInput = document.getElementById('image');
  const preview = document.getElementById('imagePreview');
  imageInput?.addEventListener('change', () => {
    const file = imageInput.files?.[0];
    if (!file || !preview) return;
    if (file.size > 5 * 1024 * 1024) {
      window.alert('Escolha uma imagem com até 5 MB.');
      imageInput.value = '';
      return;
    }
    const url = URL.createObjectURL(file);
    preview.innerHTML = '';
    const img = new Image();
    img.alt = 'Prévia da foto escolhida';
    img.onload = () => URL.revokeObjectURL(url);
    img.src = url;
    const label = document.createElement('span');
    label.textContent = file.name;
    preview.append(img, label);
  });
})();
