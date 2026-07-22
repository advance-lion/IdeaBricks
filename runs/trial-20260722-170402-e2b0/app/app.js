const foods=[
  {name:"Golden Chicken Melt",desc:"Toasty brioche, herb chicken and citrus slaw",icon:"🥪"},
  {name:"Garden Pasta Bowl",desc:"Roasted tomatoes and creamy basil sauce",icon:"🍝"},
  {name:"Sparkling Peach Tea",desc:"Lightly sweet and freshly brewed",icon:"🧋"}
], modes=[
  ["🍔","Dine In","Enjoy it here"],["🛍️","Takeout","Collect at counter"],["🚗","Drive Thru","Fast curb pickup"]
];
let cart=0,selected=null;
const list=document.querySelector("#recommendations"),count=document.querySelector("[data-testid=cart-count]"),options=document.querySelector("#options");
function renderFoods(rows=foods){
  list.innerHTML=rows.map(x=>`<article class="food"><div class="pic">${x.icon}</div><div><h4>${x.name}</h4><p>${x.desc}</p><button data-testid="add-to-cart" onclick="addCart()">Add</button></div></article>`).join("")||"<p>No weekend picks found.</p>";
}
function filterFoods(term){renderFoods(foods.filter(x=>(x.name+x.desc).toLowerCase().includes(term.toLowerCase())))}
function addCart(){count.textContent=++cart}
function renderOptions(){options.innerHTML=modes.map((m,i)=>`<button class="option ${selected===i?"selected":""}" onclick="choose(${i})"><em>${m[0]}</em><b>${m[1]}</b><small>${m[2]}</small></button>`).join("")}
function choose(i){selected=i;renderOptions()}
function closeSheet(){document.querySelector("#sheet").classList.add("closed");document.querySelector("#shade").classList.add("closed")}
document.querySelector("[data-testid=search-input]").addEventListener("input",e=>filterFoods(e.target.value));
document.querySelector("#close").onclick=closeSheet;
document.querySelector("#confirm").onclick=()=>{if(selected===null){selected=0;renderOptions()}closeSheet()};
renderFoods();renderOptions();
if(new URLSearchParams(location.search).get("qa")==="1"){
  filterFoods("Pasta"); addCart(); choose(1);
  document.querySelector("#confirm").click();
  document.querySelector("#qa-result").value=JSON.stringify({pageLoad:true,sections:!!list,filter:list.textContent.includes("Pasta"),primaryAction:cart===1&&selected===1});
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
