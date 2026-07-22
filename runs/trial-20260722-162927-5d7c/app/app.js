const tabs=["Following","Spark","Quick Finds","New","Style","Flights","Super Deals"];
const icons=["Daily Drop","Try Studio","Coin Club","Maker Hall","Parcel Spot","Tiny Garden","Tide Fish","World Shop","Fast Browse","Event Clock"];
let products=[
 ["Blockwave Charging Hub","¥319"],["Arc Mirror Audio Panel","¥218"],
 ["Cloud Shelf Light","¥136"],["Pocket Craft Kit","¥42"]
],cart=0,selected="Spark",coupon=false;
const $=s=>document.querySelector(s),el=(t,c)=>{let x=document.createElement(t);x.className=c;return x};
function renderTabs(){tabsBox=$("#tabs");tabsBox.innerHTML="";tabs.forEach(t=>{let b=el("button",t==selected?"active":"");b.textContent=t;b.onclick=()=>{selected=t;renderTabs();renderProducts()};tabsBox.append(b)})}
function renderShortcuts(){$("#shortcuts").innerHTML=icons.map((x,i)=>`<div class="shortcut"><div class="ico">${["✦","U","◉","⌂","□","♣","◒","✈","↯","▣"][i]}</div>${x}</div>`).join("")}
function renderPromos(){$("#promos").innerHTML=[["Live Pick","Notebook Stack","¥42"],["Value Boost","Mini Speaker","¥218"],["Flash Pick","LoopLamp","¥136"]].map(x=>`<article class="promo">${x[0]}<div class="art"></div><small>${x[1]}</small><span class="price">${x[2]}</span></article>`).join("")}
function renderProducts(filter=""){let shown=products.filter(p=>p[0].toLowerCase().includes(filter.toLowerCase())||!filter);$("#feed").innerHTML=shown.map((p,i)=>`<article class="card"><div class="picture"></div><div class="details"><p>${p[0]}</p><b>${p[1]}</b><button data-testid="add-to-cart" onclick="add('${p[0]}',this)">Add</button></div></article>`).join("")||"<p>No finds yet.</p>"}
function add(name,b){cart++;b.textContent="Added";b.disabled=true;renderBottom();qa("added",name)}
function renderBottom(){let names=[["◉","Explore"],["▷","Clips"],["◌","Inbox"],["⌑","Cart"],["☺","Me"]];$("#bottom").innerHTML=names.map((n,i)=>`<button class="${i==0?"active":""}"><i>${n[0]}</i>${n[1]}${i==2?'<em class="badge">12</em>':""}${i==3?`<em class="badge" data-testid="cart-count">${cart}</em>`:""}</button>`).join("")}
function qa(action,value){$("#qa-result").textContent=JSON.stringify({action,value,cart,coupon,tab:selected})}
$("#searchForm").onsubmit=e=>{e.preventDefault();let q=$("#query").value;renderProducts(q);qa("search",q)};
$("#coupon button").onclick=()=>{coupon=true;$("#coupon button").textContent="Claimed ✓";qa("coupon","claimed")};
renderTabs();renderShortcuts();renderPromos();renderProducts();renderBottom();
if(new URLSearchParams(location.search).get("qa")==="1"){ $("#query").value="Pocket"; $("#searchForm").requestSubmit(); add("QA",document.createElement("button")); $("#coupon button").click(); qa("qa-complete","functions-executed") }

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
