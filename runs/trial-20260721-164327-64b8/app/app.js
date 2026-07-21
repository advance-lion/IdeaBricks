(() => {
  const $ = (selector, scope = document) => scope.querySelector(selector);
  const $$ = (selector, scope = document) => [...scope.querySelectorAll(selector)];
  const input = $("#search-input");
  const form = $("#search-form");
  const cards = $$(".product-card");
  const toast = $(".toast");
  const qa = $("#qa-result");
  let cart = 0;
  let toastTimer;

  function announce(message) {
    toast.textContent = message;
    toast.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove("show"), 1800);
  }

  function filterProducts(query) {
    const normalized = query.trim().toLowerCase();
    let shown = 0;
    cards.forEach((card) => {
      const match = !normalized || card.dataset.name.includes(normalized) || normalized.split(/\s+/).some(word => card.dataset.name.includes(word));
      card.hidden = !match;
      if (match) shown += 1;
    });
    $(".suggestions").textContent = normalized ? `${shown} finds for “${query.trim()}”` : "Popular: rover dock · music mirror";
    return shown;
  }

  function primaryAction(label = "rover dock") {
    cart += 1;
    const count = $("[data-testid=cart-count]");
    if (count) count.textContent = cart;
    announce(`${label} added to your Bag`);
    return cart;
  }

  input.addEventListener("input", () => {
    form.classList.add("typing");
    filterProducts(input.value);
  });
  input.addEventListener("focus", () => {
    form.classList.add("typing");
    filterProducts(input.value);
  });
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const count = filterProducts(input.value);
    form.classList.remove("typing");
    announce(count ? `Showing ${count} Mango finds` : "No finds yet — try rover");
  });
  document.addEventListener("click", (event) => {
    if (!form.contains(event.target)) form.classList.remove("typing");
  });

  $$(".tab-rail button").forEach((button) => button.addEventListener("click", () => {
    $$(".tab-rail button").forEach((tab) => { tab.classList.remove("active"); tab.setAttribute("aria-pressed", "false"); });
    button.classList.add("active");
    button.setAttribute("aria-pressed", "true");
    cards.forEach(card => card.hidden = false);
    announce(`${button.textContent} feed selected`);
  }));
  $$(".shortcut").forEach((button) => button.addEventListener("click", () => announce(`${button.dataset.destination} opened`)));
  $$(".deal-card").forEach((button) => button.addEventListener("click", () => announce(`${button.dataset.collection} collection opened`)));
  $(".scan-btn").addEventListener("click", () => announce("Visual-code scanner ready"));
  $(".camera-btn").addEventListener("click", () => announce("Image search is ready"));
  $("#coupon-claim").addEventListener("click", (event) => {
    event.currentTarget.innerHTML = '<span class="speaker">✓</span><strong>Coupon saved</strong><span>ready for your next find</span><b><i>楼12</i> Saved</b>';
    announce("楼12 coupon added");
  });
  $$(".add-button").forEach((button) => button.addEventListener("click", (event) => {
    const name = event.currentTarget.closest(".product-card").querySelector("h3").textContent.replace(/Mango Select|Fresh Finds|Travel Tiny|·/g, "").trim();
    primaryAction(name);
  }));
  $$(".product-image").forEach((button) => button.addEventListener("click", () => announce("Product preview opened")));
  $$(".bottom-nav button").forEach((button) => button.addEventListener("click", () => {
    $$(".bottom-nav button").forEach(item => item.classList.remove("active"));
    button.classList.add("active");
    announce(`${button.dataset.nav} selected`);
  }));

  const badge = document.createElement("span");
  badge.dataset.testid = "cart-count";
  badge.hidden = true;
  $("[data-nav=Bag]").append(badge);

  if (new URLSearchParams(window.location.search).get("qa") === "1") {
    const filtered = filterProducts("rover");
    const cartCount = primaryAction("QA rover dock");
    qa.hidden = false;
    qa.textContent = JSON.stringify({ search: "rover", filtered, primaryAction: "add-to-cart", cartCount, passed: filtered === 1 && cartCount === 1 });
  }
})();
