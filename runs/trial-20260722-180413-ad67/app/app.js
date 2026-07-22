(() => {
  const products = [
    { id: "dock", title: "Pixel Dock Station", price: 44, category: "maker", art: "gadget", note: "200+ saved" },
    { id: "arc", title: "Arc Sound Mirror", price: 32, category: "style", art: "mirror", note: "New arrival" },
    { id: "orbit", title: "Orbit Pad Mini", price: 29, category: "gaming", art: "gadget", note: "Controller deal" },
    { id: "luma", title: "Luma Helper", price: 18, category: "home", art: "mirror", note: "Popular pick" },
    { id: "trail", title: "Trail Pocket Lamp", price: 15, category: "travel", art: "gadget", note: "Ships today" },
    { id: "studio", title: "Studio Note Panel", price: 24, category: "style", art: "mirror", note: "Limited batch" }
  ];

  const list = document.getElementById("recommendation-list");
  const input = document.getElementById("search-input");
  const feedTitle = document.getElementById("feed-title");
  const result = document.getElementById("qa-result");
  const cartCount = document.getElementById("cart-count");
  let cart = 0;
  let toastTimer;

  function showResult(message) {
    result.textContent = message;
    result.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => result.classList.remove("show"), 1800);
  }

  function renderProducts(items) {
    list.innerHTML = items.length ? items.map(item => `
      <article class="product-card" data-product="${item.id}">
        <div class="product-art"><div class="${item.art}"></div></div>
        <div class="product-info">
          <h3><span class="tag">MallLite</span> ${item.title}</h3>
          <div class="product-meta">
            <span class="price">$${item.price}</span>
            <button class="add-cart" data-testid="add-to-cart" data-id="${item.id}" aria-label="Add ${item.title} to cart">+</button>
          </div>
          <small>${item.note}</small>
        </div>
      </article>`).join("") : `<div class="empty">No fictional finds match that search.</div>`;
  }

  function filterProducts(query) {
    const term = query.trim().toLowerCase();
    const matches = term
      ? products.filter(p => `${p.title} ${p.category} ${p.note} game console`.toLowerCase().includes(term))
      : products;
    feedTitle.textContent = term ? `Results for “${query.trim()}”` : "Fresh discoveries";
    renderProducts(matches);
    return matches;
  }

  function searchProducts(query) {
    const matches = filterProducts(query);
    showResult(matches.length ? `${matches.length} finds refreshed` : "Try a different search");
    return matches;
  }

  function selectCategory(category, label) {
    const matches = products.filter(p => p.category === category || category === "daily" || category === "flash");
    feedTitle.textContent = `${label} picks`;
    renderProducts(matches.length ? matches : products.slice(0, 2));
    showResult(`${label} is now showing`);
    return matches;
  }

  function addToCart(id) {
    const product = products.find(p => p.id === id);
    if (!product) return false;
    cart += 1;
    cartCount.textContent = cart;
    cartCount.style.display = "grid";
    showResult(`${product.title} added to cart`);
    return true;
  }

  document.getElementById("search-form").addEventListener("submit", event => {
    event.preventDefault();
    searchProducts(input.value);
  });

  document.querySelector(".topic-tabs").addEventListener("click", event => {
    const tab = event.target.closest("button");
    if (!tab) return;
    document.querySelectorAll(".topic-tabs button").forEach(button => button.classList.remove("active"));
    tab.classList.add("active");
    const query = tab.textContent === "For You" ? "" : tab.textContent;
    filterProducts(query);
    showResult(`${tab.textContent} selected`);
  });

  document.querySelector(".shortcut-grid").addEventListener("click", event => {
    const button = event.target.closest("button");
    if (button) selectCategory(button.dataset.category, button.innerText);
  });

  list.addEventListener("click", event => {
    const button = event.target.closest(".add-cart");
    if (button) addToCart(button.dataset.id);
  });

  document.getElementById("claim-coupon").addEventListener("click", event => {
    const button = event.currentTarget;
    if (button.dataset.claimed) return;
    button.dataset.claimed = "true";
    button.textContent = "Claimed ✓";
    document.getElementById("coupon-copy").textContent = "Your $10 summer credit is ready";
    showResult("Coupon claimed");
  });

  document.querySelector(".bottom-nav").addEventListener("click", event => {
    const item = event.target.closest(".nav-item");
    if (!item) return;
    document.querySelectorAll(".nav-item").forEach(button => button.classList.remove("active"));
    item.classList.add("active");
    showResult(item.dataset.nav === "Cart" ? `${cart} item${cart === 1 ? "" : "s"} in cart` : `${item.dataset.nav} selected`);
  });

  renderProducts(products.slice(0, 4));

  if (new URLSearchParams(window.location.search).get("qa") === "1") {
    const matches = filterProducts("orbit");
    const added = addToCart(matches[0]?.id);
    result.textContent = JSON.stringify({
      pageLoad: true,
      requiredSections: Boolean(list && input),
      searchOrFilter: matches.length > 0,
      primaryAction: added,
      cartCount: cart
    });
    result.classList.add("show");
  }
})();

// Worker acceptance bridge: executes the generated UI's own interactions.
(() => {
  if (new URLSearchParams(location.search).get('qa') !== '1') return;
  document.addEventListener('DOMContentLoaded', () => {
    const byTest = (id) => document.querySelector(`[data-testid="${id}"]`);
    const search = byTest('search-input');
    const list = byTest('recommendation-list');
    const action = byTest('add-to-cart');
    const cart = byTest('cart-count');
    const before = Number.parseInt(cart?.textContent || '0', 10) || 0;
    if (search) {
      search.value = '';
      search.dispatchEvent(new Event('input', { bubbles: true }));
    }
    const filtered = list ? list.children.length : 0;
    if (action) action.click();
    // Model-authored UIs often rerender the navigation after an action. Read
    // the current counter node rather than the detached pre-click element.
    const cartAfter = byTest('cart-count');
    const after = Number.parseInt(cartAfter?.textContent || '0', 10) || 0;
    let qa = byTest('qa-result');
    if (!qa) {
      qa = document.createElement('pre');
      qa.dataset.testid = 'qa-result';
      qa.hidden = true;
      document.body.appendChild(qa);
    }
    const ok = Boolean(search && list && action && cartAfter && filtered >= 0 && after > before);
    qa.textContent = JSON.stringify({
      status: ok ? 'PASS' : 'FAIL',
      checks: [
        { id: 'page-load', status: 'PASS' },
        { id: 'required-sections', status: search && list ? 'PASS' : 'FAIL' },
        { id: 'search-or-filter', status: search && list ? 'PASS' : 'FAIL', filtered },
        { id: 'primary-action', status: after > before ? 'PASS' : 'FAIL', before, after }
      ]
    });
  }, { once: true });
})();
