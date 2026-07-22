const catalog = [
  { id: "orbit", name: "Orbit Desk Bot Set", price: "$46", sales: "2.0k saved", type: "bot", category: "Explore", tags: "portable console desk bot home lab" },
  { id: "arc", name: "Arc Sound Mirror", price: "$64", sales: "890 saved", type: "mirror", category: "Explore", tags: "mirror speaker style travel" },
  { id: "pocket", name: "Pocket Pixel Console", price: "$39", sales: "1.3k saved", type: "console", category: "Flash Picks", tags: "portable console pocket game" },
  { id: "halo", name: "Halo Task Lamp", price: "$28", sales: "510 saved", type: "lamp", category: "Home Lab", tags: "home lab lamp desk" },
  { id: "nova", name: "Nova Controller Dock", price: "$31", sales: "760 saved", type: "console", category: "For You", tags: "portable console controller gaming" },
  { id: "glow", name: "Glow Mirror Speaker", price: "$52", sales: "340 saved", type: "mirror", category: "Style", tags: "style mirror sound" }
];

let activeTab = "Explore";
let displayed = [...catalog.filter(item => item.category === activeTab)];
let cart = 0;
let couponClaimed = false;

const list = document.getElementById("recommendation-list");
const emptyState = document.getElementById("empty-state");
const result = document.getElementById("qa-result");
const feedLabel = document.getElementById("feed-label");
const cartCount = document.getElementById("cart-count");

function announce(message) {
  result.textContent = message;
}

function renderProducts(items) {
  list.innerHTML = "";
  emptyState.hidden = items.length !== 0;
  items.forEach((product) => {
    const card = document.createElement("article");
    card.className = "product-card";
    card.innerHTML = `
      <div class="product-image ${product.type}" aria-hidden="true"></div>
      <div class="product-info">
        <div class="brand-line">LUMA SELECT</div>
        <h2>${product.name}</h2>
        <div class="product-foot">
          <span class="price">${product.price}</span>
          <span class="sales">${product.sales}</span>
          <button class="add-to-cart" data-testid="add-to-cart" data-product="${product.id}" aria-label="Add ${product.name} to cart">+</button>
        </div>
      </div>`;
    list.appendChild(card);
  });
}

function setTab(tab) {
  activeTab = tab;
  document.querySelectorAll("[data-tab]").forEach(button => {
    button.classList.toggle("active", button.dataset.tab === tab);
  });
  displayed = catalog.filter(item => tab === "Member Deals" || item.category === tab);
  if (!displayed.length) displayed = catalog.slice(0, 2);
  document.getElementById("search-input").value = "";
  feedLabel.textContent = `${tab} picks`;
  renderProducts(displayed);
  announce(JSON.stringify({ event: "category", category: tab, results: displayed.length }));
}

function performSearch(query) {
  const normalized = query.trim().toLowerCase();
  displayed = catalog.filter(item => !normalized || `${item.name} ${item.tags}`.toLowerCase().includes(normalized));
  feedLabel.textContent = normalized ? `${displayed.length} search results` : "Fresh discoveries";
  renderProducts(displayed);
  announce(JSON.stringify({ event: "search", query: normalized, results: displayed.length }));
  return displayed;
}

function addToCart(productId, button) {
  const product = catalog.find(item => item.id === productId);
  if (!product) return false;
  cart += 1;
  cartCount.textContent = cart;
  cartCount.classList.add("has-items");
  if (button) {
    button.textContent = "Added";
    button.classList.add("added");
    button.disabled = true;
  }
  announce(JSON.stringify({ event: "add-to-cart", product: product.name, cart }));
  return true;
}

function claimCoupon() {
  couponClaimed = true;
  const button = document.getElementById("coupon-button");
  button.classList.add("claimed");
  button.querySelector(".coupon-label").textContent = "Claimed";
  announce(JSON.stringify({ event: "coupon", claimed: true }));
  return couponClaimed;
}

document.querySelectorAll("[data-tab]").forEach(button => {
  button.addEventListener("click", () => setTab(button.dataset.tab));
});

document.getElementById("search-form").addEventListener("submit", (event) => {
  event.preventDefault();
  performSearch(document.getElementById("search-input").value);
});

list.addEventListener("click", (event) => {
  const button = event.target.closest("[data-product]");
  if (button) addToCart(button.dataset.product, button);
});

document.getElementById("coupon-button").addEventListener("click", () => {
  if (!couponClaimed) claimCoupon();
});

document.querySelectorAll("[data-nav]").forEach(button => {
  button.addEventListener("click", () => {
    document.querySelectorAll("[data-nav]").forEach(item => item.classList.remove("active"));
    button.classList.add("active");
    if (button.dataset.nav === "Home") setTab("Explore");
    else announce(JSON.stringify({ event: "navigation", destination: button.dataset.nav }));
  });
});

renderProducts(displayed);

if (new URLSearchParams(window.location.search).get("qa") === "1") {
  const qaMatches = performSearch("portable console");
  const qaAction = qaMatches[0] ? addToCart(qaMatches[0].id) : false;
  const qaCoupon = claimCoupon();
  result.textContent = JSON.stringify({
    pageLoad: true,
    requiredSections: Boolean(document.querySelector('[data-testid="app-shell"]') && list),
    searchOrFilter: qaMatches.length > 0,
    primaryAction: qaAction && qaCoupon,
    cartCount: cart
  });
}

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
