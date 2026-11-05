// Todo el DOM se construye con createElement + textContent
const API = "http://127.0.0.1:8000";

function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (k === "text") node.textContent = v;
    else if (k in node) node[k] = v;
    else node.setAttribute(k, v);
  }
  children.forEach(c => node.append(c));
  return node;
}
async function api(path, options) {
  const r = await fetch(API + path, options);
  if (!r.ok) throw new Error("Error " + r.status);
  return r.status === 204 ? null : r.json();
}
function videoCard(v, delay = 0) {
  const a = el("a", { className: "card", href: `player.html?id=${v.id}` },
    el("img", { src: v.thumbnail_url, alt: v.title, loading: "lazy" }),
    el("div", {}, el("strong", { text: v.title }), el("small", { text: v.category })));
  a.style.animationDelay = `${delay * 60}ms`;
  return a;
}
function renderList(container, videos) {
  container.replaceChildren(...videos.map((v, i) => videoCard(v, i)));
}
function showMessage(container, msg) {
  container.replaceChildren(el("p", { text: msg }));
}
