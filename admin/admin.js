'use strict';
(() => {
const CFG = { id: 'byiv', site: '../', api: 'https://webhunter-admin.webhunter.workers.dev' };
const S = { sess: null, F: [], Z: null, snap: '', pending: {}, preview: {}, q: '', cat: '', pub: ['', 'Web je aktuální'], saving: false, def: false };
const $ = (s, c = document) => c.querySelector(s);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const slugify = (s) => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 70);
const uid = () => Math.random().toString(36).slice(2, 8);
const photo = (f) => S.preview[f] || (f.startsWith('img/uploads/') ? CFG.site + f : CFG.site + 'images/produkty/' + f);
const dirty = () => JSON.stringify(S.F) !== S.snap || Object.keys(S.pending).length > 0;
function toast(t, type = '') { const e = document.createElement('div'); e.className = 'toast ' + type; e.textContent = t; $('#toasts').appendChild(e); setTimeout(() => e.remove(), type === 'err' ? 7000 : 4000); }

const b64e = (bytes) => { let s = ''; bytes = new Uint8Array(bytes); for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000)); return btoa(s); };
const utf8b64 = (str) => b64e(new TextEncoder().encode(str));
const saveSess = () => localStorage.setItem('byiv_sess', JSON.stringify({ t: S.sess, def: S.def, exp: Date.now() + 11.5 * 3600e3 }));
async function api(path, opt = {}, retried = false) {
  const headers = { ...(opt.body ? { 'Content-Type': 'application/json' } : {}) };
  if (S.sess) headers.Authorization = 'Bearer ' + S.sess;
  let r;
  try { r = await fetch(`${CFG.api}/api/${CFG.id}${path}`, { ...opt, headers, cache: 'no-store' }); }
  catch { throw new Error('Nelze se spojit se serverem. Zkontrolujte připojení k internetu.'); }
  if (r.status === 401 && path !== '/login' && !retried && S.F.length) { if (await reauth()) return api(path, opt, true); }
  if (!r.ok) { let m = r.statusText; try { m = (await r.json()).error || m; } catch {} const e = new Error(m); e.status = r.status; throw e; }
  return opt.raw ? r.text() : r.json();
}
const readFile = (p) => api('/file?path=' + encodeURIComponent(p) + '&t=' + Date.now(), { raw: true });
async function commit(files, message) {
  const out = [], q = [...files];
  const w = async () => { while (q.length) { const f = q.shift(); const { sha } = await api('/blob', { method: 'POST', body: JSON.stringify({ content: f.b64 ?? utf8b64(f.content), encoding: 'base64' }) }); out.push({ path: f.path, sha }); } };
  await Promise.all([w(), w(), w()]);
  return (await api('/commit', { method: 'POST', body: JSON.stringify({ files: out, message }) })).sha;
}
function reauth() {
  const pw = prompt('Přihlášení vypršelo. Zadejte heslo (rozpracované změny zůstanou):');
  if (!pw) return Promise.resolve(false);
  return api('/login', { method: 'POST', body: JSON.stringify({ password: pw }) }).then((r) => { S.sess = r.token; S.def = r.def; saveSess(); return true; }, (e) => { toast(e.message, 'err'); return false; });
}

/* obrázky */
async function compress(file, max = 1600) {
  let bmp; try { bmp = await createImageBitmap(file); } catch { throw new Error(`Soubor „${file.name}“ nejde načíst (použijte JPG, PNG nebo WebP).`); }
  const sc = Math.min(1, max / Math.max(bmp.width, bmp.height)), w = Math.round(bmp.width * sc), h = Math.round(bmp.height * sc);
  const c = document.createElement('canvas'); c.width = w; c.height = h; c.getContext('2d').drawImage(bmp, 0, 0, w, h);
  let blob = await new Promise((r) => c.toBlob(r, 'image/webp', 0.82)), ext = 'webp';
  if (!blob || blob.type !== 'image/webp') { blob = await new Promise((r) => c.toBlob(r, 'image/jpeg', 0.86)); ext = 'jpg'; }
  return { blob, ext };
}
async function upload(file, hint) {
  const { blob, ext } = await compress(file); const d = new Date();
  const path = `img/uploads/${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}/${(slugify(hint) || 'foto').slice(0, 40)}-${uid()}.${ext}`;
  S.pending[path] = b64e(await blob.arrayBuffer()); S.preview[path] = URL.createObjectURL(blob); return path;
}

/* zveřejnění */
let pubTimer = null;
function setPub(state, text) { S.pub = [state, text]; const el = $('.pub'); if (el) { el.className = 'pub ' + state; el.textContent = text; } }
function watchPublish(sha) {
  localStorage.setItem('byiv_pub', JSON.stringify({ sha, t: Date.now() })); clearInterval(pubTimer); setPub('busy', 'Zveřejňuji změny…');
  const t0 = Date.now();
  pubTimer = setInterval(async () => {
    try { const v = await fetch(CFG.site + 'version.json?t=' + Date.now(), { cache: 'no-store' }).then((r) => r.json());
      if (v.sha === sha) { clearInterval(pubTimer); localStorage.removeItem('byiv_pub'); setPub('', 'Web je aktuální'); toast('Změny jsou na webu', 'ok'); return; } } catch {}
    if (Date.now() - t0 > 10 * 60000) { clearInterval(pubTimer); setPub('warn', 'Zveřejnění trvá déle než obvykle'); }
  }, 7000);
}

/* data */
async function load() {
  S.Z = JSON.parse(await readFile('_data/zaklad.json'));
  S.F = JSON.parse(await readFile('_data/produkty.json'));
  S.snap = JSON.stringify(S.F);
}
function validate() {
  const sl = new Set();
  for (const p of S.F) {
    if (!p.nazev.trim()) return 'Některý produkt nemá název.';
    if (!/^[a-z0-9][a-z0-9-]*$/.test(p.slug)) return `Produkt „${p.nazev}“ má neplatnou adresu.`;
    if (sl.has(p.slug)) return `Dva produkty mají stejnou adresu „${p.slug}“.`;
    sl.add(p.slug);
    if (!(p.cena > 0)) return `Produkt „${p.nazev}“ nemá cenu.`;
    if (!p.fotky.length) return `Produkt „${p.nazev}“ nemá žádnou fotku.`;
  }
}
async function save() {
  if (S.saving || !dirty()) return; const err = validate(); if (err) return toast(err, 'err');
  S.saving = true; render();
  try {
    S.F.forEach((p, i) => { p.poradi = i; });
    const used = JSON.stringify(S.F);
    const files = [{ path: '_data/produkty.json', content: JSON.stringify(S.F, null, 1) + '\n' }];
    const imgs = Object.keys(S.pending).filter((p) => used.includes(p)); imgs.forEach((p) => files.push({ path: p, b64: S.pending[p] }));
    const sha = await commit(files, 'Produkty (administrace)' + (imgs.length ? ` +${imgs.length} fotek` : ''));
    imgs.forEach((p) => delete S.pending[p]); S.snap = JSON.stringify(S.F);
    toast('Uloženo. Na webu to bude za 2–3 minuty.', 'ok'); watchPublish(sha);
  } catch (e) { toast('Uložení se nepovedlo: ' + e.message, 'err'); }
  S.saving = false; render();
}

/* UI */
function shell(inner) {
  return `<div class="top"><b>by IV · administrace</b><span class="pub ${S.pub[0]}">${esc(S.pub[1])}</span><span class="sp"></span>
  <a class="btn" href="${CFG.site}" target="_blank">Otevřít web</a><button class="btn" data-pw>Změnit heslo</button><button class="btn" data-out>Odhlásit</button></div>
  <div class="wrap">${inner}</div>`;
}
function render() { const h = location.hash; if (!S.sess) return login(); if (h.startsWith('#p/')) return edit(h.slice(3)); list(); bindTop(); }
function bindTop() {
  $('[data-out]')?.addEventListener('click', () => { if (dirty() && !confirm('Máte neuložené změny. Opravdu odhlásit?')) return; localStorage.removeItem('byiv_sess'); S.sess = null; S.F = []; login(); });
  $('[data-pw]')?.addEventListener('click', changePw);
}
function list() {
  const q = slugify(S.q), cats = S.Z.y2.filter((c) => !['novinky', 'slevy'].includes(c.slug));
  const rows = S.F.map((p, i) => [p, i]).filter(([p]) => (!q || slugify(p.nazev).includes(q)) && (!S.cat || p.kategorie === S.cat));
  $('#app').innerHTML = shell(`<div style="display:flex;gap:.5rem;flex-wrap:wrap"><input data-q placeholder="Hledat produkt…" value="${esc(S.q)}" style="flex:2;min-width:180px">
    <select data-cat style="flex:1;min-width:140px"><option value="">Všechny kategorie</option>${cats.map((c) => `<option value="${c.slug}" ${S.cat === c.slug ? 'selected' : ''}>${esc(c.nazev)}</option>`).join('')}</select>
    <button class="btn btn-p" data-new>+ Nový produkt</button></div>
    <p class="hint">${rows.length} z ${S.F.length} produktů</p>
    ${rows.slice(0, 150).map(([p, i]) => `<div class="row" data-s="${p.slug}"><img src="${photo(p.fotky[0])}" alt="" loading="lazy"><div class="t"><b>${esc(p.nazev)}</b><small>${p.cena} Kč${p.puvodni ? ` (dříve ${p.puvodni})` : ''}</small>
      ${p.novinka ? '<span class="badge">novinka</span>' : ''}${p.vyprodej ? '<span class="badge">výprodej</span>' : ''}${p.vyprodano ? '<span class="badge">vyprodáno</span>' : ''}</div></div>`).join('')}
    ${rows.length > 150 ? '<p class="hint">Zobrazeno prvních 150, upřesněte hledání.</p>' : ''}
    <div class="bar"><span class="hint">${dirty() ? 'Máte neuložené změny' : ''}</span><button class="btn btn-p" data-save ${dirty() && !S.saving ? '' : 'disabled'}>${S.saving ? 'Ukládám…' : 'Uložit a zveřejnit'}</button></div>`);
  $('[data-q]').addEventListener('input', (e) => { S.q = e.target.value; const p = e.target.selectionStart; list(); bindTop(); const i = $('[data-q]'); i.focus(); i.setSelectionRange(p, p); });
  $('[data-cat]').addEventListener('change', (e) => { S.cat = e.target.value; list(); bindTop(); });
  $('[data-save]').addEventListener('click', save);
  $('[data-new]').addEventListener('click', () => {
    const n = prompt('Název nového produktu:'); if (!n) return; let slug = slugify(n), k = 2; while (S.F.some((p) => p.slug === slug)) slug = slugify(n) + '-' + k++;
    S.F.unshift({ slug, nazev: n.trim(), cena: 0, puvodni: null, kategorie: cats[0].slug, rada: null, velikosti: [], material: '', popis: [], fotky: [], novinka: true, vyprodej: false, vyprodano: false, poradi: 0 });
    location.hash = '#p/' + slug;
  });
  document.querySelectorAll('.row').forEach((r) => r.addEventListener('click', () => { location.hash = '#p/' + r.dataset.s; }));
}
function edit(slug) {
  const p = S.F.find((x) => x.slug === slug); if (!p) { location.hash = ''; return; }
  const cats = S.Z.y2.filter((c) => !['novinky', 'slevy'].includes(c.slug));
  $('#app').innerHTML = shell(`<p><a href="#" data-back>← Zpět na seznam</a></p><div class="card"><h2>${esc(p.nazev || 'Nový produkt')}</h2>
    <label>Název</label><input data-k="nazev" value="${esc(p.nazev)}">
    <div class="g2"><div><label>Cena (Kč)</label><input data-k="cena" type="number" min="0" value="${p.cena || ''}"></div>
    <div><label>Původní cena (Kč, nechte prázdné bez slevy)</label><input data-k="puvodni" type="number" min="0" value="${p.puvodni || ''}"></div>
    <div><label>Kategorie</label><select data-k="kategorie">${cats.map((c) => `<option value="${c.slug}" ${p.kategorie === c.slug ? 'selected' : ''}>${esc(c.nazev)}</option>`).join('')}</select></div>
    <div><label>Řada</label><select data-k="rada"><option value="">— žádná —</option>${S.Z.xB.map((r) => `<option ${p.rada === r.nazev ? 'selected' : ''}>${esc(r.nazev)}</option>`).join('')}</select></div></div>
    <label>Materiál</label><input data-k="material" value="${esc(p.material || '')}">
    <label>Velikosti</label><div class="chk">${S.Z.LD.map((v) => `<label><input type="checkbox" data-v="${v}" ${p.velikosti.includes(v) ? 'checked' : ''}> ${v}</label>`).join('')}</div>
    <label>Popis (každý odstavec na nový řádek)</label><textarea data-k="popis">${esc(p.popis.join('\n'))}</textarea>
    <div class="chk"><label><input type="checkbox" data-f="novinka" ${p.novinka ? 'checked' : ''}> Novinka</label><label><input type="checkbox" data-f="vyprodej" ${p.vyprodej ? 'checked' : ''}> Výprodej</label><label><input type="checkbox" data-f="vyprodano" ${p.vyprodano ? 'checked' : ''}> Vyprodáno</label></div></div>
    <div class="card"><h3>Fotografie</h3><p class="hint">První fotka je hlavní. Doporučujeme foto na výšku.</p><div class="fotos">${p.fotky.map((f, i) => `<div><img src="${photo(f)}" alt=""><div class="a">
      <button class="btn btn-s" data-m="${i}:-1" ${i ? '' : 'disabled'}>←</button><button class="btn btn-s" data-m="${i}:1" ${i < p.fotky.length - 1 ? '' : 'disabled'}>→</button><button class="btn btn-s btn-d" data-x="${i}">✕</button></div></div>`).join('')}</div>
      <p><input type="file" data-up accept="image/*" multiple></p></div>
    <div class="card"><button class="btn" data-first>Dát na začátek nabídky</button> <button class="btn btn-d" data-del>Smazat produkt</button></div>
    <div class="bar"><span class="hint">${dirty() ? 'Máte neuložené změny' : ''}</span><button class="btn btn-p" data-save ${dirty() && !S.saving ? '' : 'disabled'}>${S.saving ? 'Ukládám…' : 'Uložit a zveřejnit'}</button></div>`);
  bindTop();
  const mark = () => { const b = $('[data-save]'); if (b) b.disabled = !dirty(); };
  $('[data-back]').addEventListener('click', (e) => { e.preventDefault(); location.hash = ''; });
  document.querySelectorAll('[data-k]').forEach((el) => el.addEventListener('input', () => {
    const k = el.dataset.k, v = el.value;
    if (k === 'cena') p.cena = +v || 0; else if (k === 'puvodni') p.puvodni = +v || null; else if (k === 'popis') p.popis = v.split('\n').map((x) => x.trim()).filter(Boolean);
    else if (k === 'rada') p.rada = v || null; else p[k] = v; mark();
  }));
  document.querySelectorAll('[data-v]').forEach((el) => el.addEventListener('change', () => { p.velikosti = S.Z.LD.filter((v) => $(`[data-v="${v}"]`).checked); mark(); }));
  document.querySelectorAll('[data-f]').forEach((el) => el.addEventListener('change', () => { p[el.dataset.f] = el.checked; mark(); }));
  document.querySelectorAll('[data-m]').forEach((b) => b.addEventListener('click', () => { const [i, d] = b.dataset.m.split(':').map(Number); p.fotky.splice(i + d, 0, p.fotky.splice(i, 1)[0]); edit(slug); }));
  document.querySelectorAll('[data-x]').forEach((b) => b.addEventListener('click', () => { p.fotky.splice(+b.dataset.x, 1); edit(slug); }));
  $('[data-up]').addEventListener('change', async (e) => {
    for (const f of e.target.files) { try { p.fotky.push(await upload(f, p.nazev)); } catch (err) { toast(err.message, 'err'); } }
    edit(slug);
  });
  $('[data-first]').addEventListener('click', () => { S.F.splice(S.F.indexOf(p), 1); S.F.unshift(p); toast('Přesunuto na začátek.', 'ok'); edit(slug); });
  $('[data-del]').addEventListener('click', () => { if (!confirm(`Opravdu smazat „${p.nazev}“? Z webu zmizí po uložení.`)) return; S.F.splice(S.F.indexOf(p), 1); location.hash = ''; });
  $('[data-save]').addEventListener('click', save);
}
async function changePw() {
  const old = prompt('Současné heslo:'); if (!old) return; const n1 = prompt('Nové heslo (alespoň 8 znaků):'); if (!n1) return;
  if (n1.length < 8) return toast('Heslo je příliš krátké.', 'err'); if (prompt('Nové heslo ještě jednou:') !== n1) return toast('Hesla se neshodují.', 'err');
  try { const r = await api('/password', { method: 'POST', body: JSON.stringify({ old, password: n1 }) }); S.sess = r.token; S.def = false; saveSess(); toast('Heslo změněno.', 'ok'); } catch (e) { toast(e.message, 'err'); }
}
function login(msg = '') {
  $('#app').innerHTML = `<form class="login"><h2>Přihlášení</h2><p class="hint">Administrace e-shopu by IV</p><label>Heslo</label><input type="password" id="pw" autocomplete="current-password" autofocus>
    <p class="err">${esc(msg)}</p><button class="btn btn-p" style="width:100%">Přihlásit se</button></form>`;
  $('form').addEventListener('submit', async (e) => {
    e.preventDefault();
    try { const r = await api('/login', { method: 'POST', body: JSON.stringify({ password: $('#pw').value }) }); S.sess = r.token; S.def = r.def; saveSess(); boot(); }
    catch (err) { $('.err').textContent = err.status === 401 ? 'Nesprávné heslo.' : err.message; }
  });
}
async function boot() {
  $('#app').innerHTML = '<p style="text-align:center;margin-top:20vh">Načítám produkty…</p>';
  try { await load(); } catch (e) {
    if (e.status === 401) { S.sess = null; return login('Přihlášení vypršelo.'); }
    $('#app').innerHTML = `<p style="text-align:center;margin-top:20vh">Načtení se nepovedlo: ${esc(e.message)} <button onclick="location.reload()">Zkusit znovu</button></p>`; return;
  }
  const p = JSON.parse(localStorage.getItem('byiv_pub') || 'null'); if (p && Date.now() - p.t < 10 * 60000) watchPublish(p.sha);
  render();
}
window.addEventListener('hashchange', () => S.sess && S.F.length && render());
window.addEventListener('beforeunload', (e) => { if (dirty()) { e.preventDefault(); e.returnValue = ''; } });
const ss = JSON.parse(localStorage.getItem('byiv_sess') || 'null');
if (ss && ss.exp > Date.now()) { S.sess = ss.t; S.def = !!ss.def; boot(); } else login();
})();
