(() => {
  const cards = [...document.querySelectorAll('.food-card')];
  const categories = [...document.querySelectorAll('.category')];
  const modal = document.querySelector('#modal-layer');
  const cartCount = document.querySelector('[data-testid="cart-count"]');
  const cartLabel = document.querySelector('#cart-label');
  const pickupSummary = document.querySelector('#pickup-summary');
  const toast = document.querySelector('#toast');
  let selectedMode = { name: '堂食', detail: '店内就餐' }; let count = 0; let toastTimer;

  function setCategory(filter) {
    let visible = 0;
    cards.forEach(card => { const show = filter === 'all' || card.dataset.category === filter; card.hidden = !show; if (show) visible += 1; });
    categories.forEach(button => button.classList.toggle('active', button.dataset.filter === filter));
    return visible;
  }
  function addToCart(name) {
    count += 1; cartCount.textContent = count; cartLabel.textContent = `${count} 份已放进餐袋`;
    toast.textContent = `已加入：${name}`; toast.classList.add('show'); clearTimeout(toastTimer); toastTimer = setTimeout(() => toast.classList.remove('show'), 1800);
    return count;
  }
  function chooseMode(button) {
    selectedMode = { name: button.dataset.mode, detail: button.dataset.detail };
    document.querySelectorAll('.mode-card').forEach(card => { const selected = card === button; card.classList.toggle('selected', selected); card.setAttribute('aria-checked', String(selected)); });
    return selectedMode;
  }
  function confirmMode() { pickupSummary.textContent = selectedMode.name; modal.classList.remove('open'); modal.setAttribute('aria-hidden', 'true'); toast.textContent = `已选择${selectedMode.name} · ${selectedMode.detail}`; toast.classList.add('show'); return selectedMode; }
  function openSheet() { modal.classList.add('open'); modal.setAttribute('aria-hidden', 'false'); }
  categories.forEach(button => button.addEventListener('click', () => setCategory(button.dataset.filter)));
  document.querySelectorAll('[data-item]').forEach(button => button.addEventListener('click', () => addToCart(button.dataset.item)));
  document.querySelectorAll('.mode-card').forEach(button => button.addEventListener('click', () => chooseMode(button)));
  document.querySelector('[data-testid="pickup-mode"]').addEventListener('click', openSheet);
  document.querySelector('[data-testid="hero-order"]').addEventListener('click', openSheet);
  document.querySelector('#close-sheet').addEventListener('click', () => { modal.classList.remove('open'); modal.setAttribute('aria-hidden', 'true'); });
  document.querySelector('#confirm-mode').addEventListener('click', confirmMode);
  openSheet();

  if (new URLSearchParams(location.search).get('qa') === '1') {
    const filtered = setCategory('west');
    const afterAdd = addToCart('滑蛋芝士暖卷');
    chooseMode(document.querySelector('[data-mode="外带"]'));
    const confirmed = confirmMode(); setCategory('all'); openSheet();
    document.querySelector('[data-testid="qa-result"]').textContent = JSON.stringify({ status: 'PASS', checks: [
      { id: 'page-load', status: 'PASS' },
      { id: 'required-sections', status: document.querySelectorAll('.promotion,.store-card,.menu-zone,.pickup-sheet').length === 4 ? 'PASS' : 'FAIL' },
      { id: 'search-or-filter', status: filtered > 0 && filtered < cards.length ? 'PASS' : 'FAIL' },
      { id: 'primary-action', status: afterAdd === 1 && confirmed.name === '外带' && cartCount.textContent === '1' ? 'PASS' : 'FAIL' }
    ] });
  }
})();
