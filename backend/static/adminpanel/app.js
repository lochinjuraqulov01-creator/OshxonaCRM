/* ============================================================
   SmartOshxona Admin Panel — app.js
   • JWT login (username/parol)
   • Buyurtmalar: real-time (WebSocket), filtrlar (holat + vaqt oralig'i),
     vaqt bo'yicha navbat, har bir stol tarixi
   • CRUD: mahsulotlar (rasm/nom/narx/izoh), kategoriyalar, stollar (QR)
   • Statistika: kunlik daromad, TOP mahsulot, talab darajasi, sotilmaganlar
   ============================================================ */
'use strict';

const API = window.location.origin;
const WS_PATH = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/ws/admin/orders/`;

const S = {
    access: null,
    refresh: null,
    user: null,
    ws: null,
    wsConnected: false,
    pages: { orders: 1, products: 1 },
    charts: {},
    tables: [],
    categories: [],
};

const $ = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);
const money = (n) => Number(n || 0).toLocaleString('ru-RU').replace(/,/g, ' ') + 'сум';
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

const STATUS_LABEL = {
    new: '🆕 Новый', preparing: '👨‍🍳 Готовится', in_progress: '🚶 В процессе',
    delivered: '✅ Доставлен', cancelled: '❌ Отменён',
};

function toast(msg, type = '') {
    const el = $('#toast');
    el.textContent = msg;
    el.className = 'toast ' + type;
    setTimeout(() => el.classList.add('hidden'), 3000);
}

// ---------------- API ----------------
async function api(path, options = {}, retried = false) {
    const headers = { ...(options.headers || {}) };
    if (!(options.body instanceof FormData)) headers['Content-Type'] = 'application/json';
    headers['ngrok-skip-browser-warning'] = '1';   // ngrok bepul versiyasi uchun
    if (S.access) headers['Authorization'] = `Bearer ${S.access}`;

    const res = await fetch(API + path, { ...options, headers });

    if (res.status === 401 && !retried && S.refresh) {
        const ok = await refreshTokens();
        if (ok) return api(path, options, true);
        logout();
        throw new Error('Авторизация завершена');
    }
    const data = await res.json().catch(() => ({ success: false, message: 'Операция прошла успешно. После обновления страницы она исчезнет.' }));
    return data;
}

async function refreshTokens() {
    try {
        const res = await fetch(API + '/api/auth/refresh/', {
            method: 'POST', headers: { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': '1' },
            body: JSON.stringify({ refresh: S.refresh }),
        }).then(r => r.json());
        if (res.success) { S.access = res.access; saveTokens(); return true; }
    } catch (e) { /* ignore */ }
    return false;
}

function saveTokens() {
    localStorage.setItem('so_access', S.access);
    localStorage.setItem('so_refresh', S.refresh);
}

// ---------------- AUTH ----------------
$('#loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = $('#loginBtn');
    btn.disabled = true; btn.textContent = 'Входит...';
    const res = await fetch(API + '/api/auth/login/', {
        method: 'POST', headers: { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': '1' },
        body: JSON.stringify({ username: $('#loginUser').value.trim(), password: $('#loginPass').value }),
    }).then(r => r.json()).catch(() => ({ success: false }));

    btn.disabled = false; btn.textContent = 'Войти';

    if (res.success) {
        S.access = res.access; S.refresh = res.refresh; S.user = res.user;
        saveTokens();
        enterApp();
    } else {
        $('#loginError').textContent = res.message || 'Неверный логин или пароль.';
        $('#loginError').classList.remove('hidden');
    }
});

function logout() {
    localStorage.removeItem('so_access');
    localStorage.removeItem('so_refresh');
    if (S.ws) { try { S.ws.close(); } catch (e) {} }
    $('#appView').classList.add('hidden');
    $('#loginView').classList.remove('hidden');
}

$('#logoutBtn').onclick = logout;

function enterApp() {
    $('#loginView').classList.add('hidden');
    $('#appView').classList.remove('hidden');
    $('#whoami').textContent = `👤 ${S.user?.first_name || S.user?.username || ''}`;
    connectWS();
    loadAll();
}

// ---------------- WebSocket (real-time) ----------------
function connectWS() {
    if (S.ws) { try { S.ws.close(); } catch (e) {} }
    const ws = new WebSocket(`${WS_PATH}?token=${encodeURIComponent(S.access)}`);
    S.ws = ws;

    ws.onopen = () => { S.wsConnected = true; $('#liveDot').classList.add('on'); };
    ws.onclose = () => {
        S.wsConnected = false;
        $('#liveDot').classList.remove('on');
        setTimeout(() => { if (S.access) connectWS(); }, 5000);   // qayta ulanish
    };
    ws.onmessage = (e) => {
        let msg;
        try { msg = JSON.parse(e.data); } catch (err) { return; }

        if (msg.event === 'order_new') {
            toast(`🆕 Новый заказ #${msg.order_number} — Стол №${msg.table_number} — ${money(msg.total)}`, 'ok');
            bumpBadge();
            if (activePage() === 'dashboard') loadDashboard();
            if (activePage() === 'orders') loadOrders();
        } else if (msg.event === 'order_status') {
            toast(`🔄 #${msg.order_number}: ${msg.status_display}`, '');
            if (activePage() === 'orders') loadOrders();
            if (activePage() === 'dashboard') loadDashboard();
        }
    };
}

let unread = 0;
function bumpBadge() {
    unread += 1;
    const b = $('#wsBadge');
    b.textContent = unread;
    b.classList.remove('hidden');
    if (activePage() === 'orders') { unread = 0; b.classList.add('hidden'); }
}

// ---------------- Navigatsiya ----------------
$$('.sidebar nav a').forEach(a => {
    a.onclick = () => {
        $$('.sidebar nav a').forEach(x => x.classList.remove('active'));
        a.classList.add('active');
        $$('.page').forEach(p => p.classList.remove('active'));
        $(`#page-${a.dataset.page}`).classList.add('active');
        $('#sidebar').classList.remove('open');
        unread = 0; $('#wsBadge').classList.add('hidden');
        routePage(a.dataset.page);
    };
});
$('#menuToggle').onclick = () => $('#sidebar').classList.toggle('open');

function activePage() {
    return document.querySelector('.sidebar nav a.active')?.dataset.page || 'dashboard';
}
function routePage(p) {
    if (p === 'dashboard') loadDashboard();
    else if (p === 'orders') loadOrders();
    else if (p === 'products') loadProducts();
    else if (p === 'categories') loadCategories();
    else if (p === 'tables') loadTablesPage();
    else if (p === 'stats') loadStats();
    else if (p === 'feedback') loadFeedback();
    else if (p === 'profile') loadProfile();
}

async function loadAll() {
    await loadCategories(true);
    routePage('dashboard');
}

// ================= DASHBOARD =================
async function loadDashboard() {
    const [stats, tables] = await Promise.all([
        api('/api/stats/today/'),
        api('/api/restaurant/tables/busy-map/'),
    ]);

    if (stats.success) {
    $('#kpiGrid').innerHTML = kpi([
        ['💰', money(stats.revenue), 'Доход за сегодня'],
        ['🧾', stats.orders_count, 'Заказов за сегодня'],
        ['🔥', stats.active_orders, 'Активные заказы'],
        ['🧮', money(stats.avg_check), 'Средний чек'],
        ['👥', stats.unique_guests, 'Клиенты (Telegram)'],
    ]);
    renderTopList('#todayTop', stats.top_products, 'Не продано сегодня 🎉');
    renderUnsold('#todayUnsold', stats.unsold_products);
}

    if (tables.success) {
        S.tables = tables.results;
        const map = $('#tablesMap');
        map.innerHTML = '';
        tables.results.forEach(t => {
            const cell = document.createElement('div');
            cell.className = 't-cell' + (t.is_busy ? ' busy' : '');
            cell.innerHTML = `
                <div class="t-num">№${t.number}</div>
                <div class="t-status">${t.status_display}${t.active_orders_count ? ` · ${t.active_orders_count} заказа` : ''}</div>
                <div style="margin-top:6px"><button class="btn btn-sm btn-blue" onclick="openTableHistory(${t.id}, ${t.number})">История</button></div>`;
            map.appendChild(cell);
        });
    }
}

function kpi(items) {
    return items.map(([ic, val, label]) => `
        <div class="kpi">
            <div class="k-icon">${ic}</div>
            <div class="k-val">${val}</div>
            <div class="k-label">${label}</div>
        </div>`).join('');
}

function renderTopList(sel, items, emptyMsg) {
    const el = $(sel);
    if (!items?.length) { el.innerHTML = `<div class="empty" style="padding:16px">${emptyMsg}</div>`; return; }
    el.innerHTML = items.map((p, i) => `
        <div style="display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid #eef1f6;font-size:13.5px">
            <span>${['🥇', '🥈', '🥉', '4️⃣', '5️⃣'][i] || '•'} ${esc(p.name)}</span>
            <b>${p.qty} шт · ${money(p.revenue)}</b>
        </div>`).join('');
}

function renderUnsold(sel, items) {
    const el = $(sel);
    if (!items?.length) { el.innerHTML = `<div class="empty" style="padding:16px">Всё продано! 🎉</div>`; return; }
    el.innerHTML = items.map(p => `
        <div style="display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid #eef1f6;font-size:13.5px">
            <span>${esc(p.name)}</span>
            <b style="color:var(--muted)">${money(p.price)}</b>
        </div>`).join('');
}

// ================= BUYURTMALAR =================
$('#applyFilters').onclick = () => { S.pages.orders = 1; loadOrders(); };
$('#fStatus').onchange = () => { S.pages.orders = 1; loadOrders(); };
$('#fOrder').onchange = () => { S.pages.orders = 1; loadOrders(); };

function ordersQuery(page = 1) {
    const p = new URLSearchParams({ page, page_size: 15 });
    if ($('#fStatus').value) p.set('status', $('#fStatus').value);
    if ($('#fFrom').value) p.set('date_from', $('#fFrom').value);
    if ($('#fTo').value) p.set('date_to', $('#fTo').value);
    if ($('#fSearch').value.trim()) p.set('search', $('#fSearch').value.trim());
    p.set('ordering', $('#fOrder').value);
    return p.toString();
}

async function loadOrders() {
    const res = await api(`/api/orders/admin-orders/?${ordersQuery(S.pages.orders)}`);
    if (!res.success) { toast(res.message || 'Ошибка', 'error'); return; }

    const tb = $('#ordersTbody');
    tb.innerHTML = '';
    (res.results || []).forEach(o => {
        const tr = document.createElement('tr');
        const itemsShort = o.items.map(i => `${esc(i.product_name)} ×${i.quantity}`).join(', ');
        const time = new Date(o.created_at).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
        const canFlow = ['new', 'preparing', 'in_progress'].includes(o.status);
        tr.innerHTML = `
            <td><b>${o.order_number}</b></td>
            <td>№${o.table_number}</td>
            <td>${time}</td>
            <td style="max-width:220px">${itemsShort}${o.customer_note ? `<br><i style="color:var(--muted);font-size:11.5px">📝 ${esc(o.customer_note)}</i>` : ''}</td>
            <td><b>${money(o.total)}</b></td>
            <td><span class="st ${o.status}">${STATUS_LABEL[o.status] || o.status}</span></td>
            <td style="white-space:nowrap">
                ${canFlow ? nextStatusButtons(o) : ''}
                <button class="btn btn-sm btn-blue" onclick="openOrderDetail('${o.id}')">👁</button>
            </td>`;
        tb.appendChild(tr);
    });

    renderPager('#ordersPager', S.pages.orders, res.pages, (p) => { S.pages.orders = p; loadOrders(); });
}

function nextStatusButtons(o) {
    const flows = {
        new: [['preparing', '▶ Принять', 'btn-warn']],
        preparing: [['in_progress', '🍳 Готов', 'btn-ok']],
        in_progress: [['delivered', '✅ Доставлен', 'btn-ok']],
    };
    return (flows[o.status] || []).map(([st, label, cls]) =>
        `<button class="btn btn-sm ${cls}" onclick="setStatus('${o.id}','${st}')">${label}</button> `).join('')
        + (o.status === 'new' ? `<button class="btn btn-sm btn-danger" onclick="cancelOrder('${o.id}')">✖</button> ` : '');
}

async function setStatus(id, status) {
    const reason = status === 'cancelled' ? (prompt('Причина отмены:') || 'Админ отменил') : '';
    const res = await api(`/api/orders/admin-orders/${id}/status/`, {
        method: 'POST', body: JSON.stringify({ status, reason }),
    });
    if (res.success) { toast('Статус: ' + res.order.status_display, 'ok'); loadOrders(); }
    else toast(res.message || 'Ошибка', 'error');
}

async function cancelOrder(id) {
    if (!confirm('Вы хотите отменить этот заказ?')) return;
    setStatus(id, 'cancelled');
}

window.openOrderDetail = async function (id) {
    const res = await api(`/api/orders/admin-orders/${id}/`);
    if (!res.success) return;
    const o = res;
    const items = o.items.map(i => `• ${esc(i.product_name)} × ${i.quantity} — ${money(i.total_price)}`).join('<br>');
    $('#modalBox').innerHTML = `
        <h3>Заказ #${o.order_number}</h3>
        <p style="color:var(--muted);font-size:12.5px">🪑 Стол №${o.table_number} · 🕒 ${new Date(o.created_at).toLocaleString('ru-RU')}</p>
        <div class="order-items-detail">${items}<br><b>Итого: ${money(o.total)}</b></div>
        ${o.customer_note ? `<p>📝 <i>${esc(o.customer_note)}</i></p>` : ''}
        <p style="margin-top:8px"><span class="st ${o.status}">${STATUS_LABEL[o.status]}</span></p>
        <h3 style="margin-top:16px;font-size:14px">История статусов</h3>
        <div class="order-items-detail">
            ${(o.status_history || []).map(h => `• ${STATUS_LABEL[h.new_status] || h.new_status} — ${new Date(h.created_at).toLocaleString('ru-RU')}${h.note ? ` (${esc(h.note)})` : ''}`).join('<br>') || '—'}
        </div>
        ${['⭐'].includes('⭐') && o.feedback ? `<p>⭐ Оценка клиента: <b>${'★'.repeat(o.feedback.rating)}${'☆'.repeat(5 - o.feedback.rating)}</b>${o.feedback.comment ? `<br>«${esc(o.feedback.comment)}»` : ''}</p>` : ''}
        <div class="modal-actions"><button class="btn btn-primary" onclick="closeModal()">Закрыть</button></div>`;
    $('#modal').classList.remove('hidden');
};

window.openTableHistory = async function (tableId, number) {
    const res = await api(`/api/orders/admin-orders/table-history/?table_id=${tableId}&days=30&page_size=10`);
    if (!res.success) return;
    const rows = (res.results || []).map(o => `
        <div style="padding:8px 0;border-bottom:1px solid #eef1f6">
            <b>${o.order_number}</b> · ${new Date(o.created_at).toLocaleDateString('ru-RU')} ·
            <span class="st ${o.status}" style="font-size:10px">${STATUS_LABEL[o.status]}</span> ·
            <b>${money(o.total)}</b>
        </div>`).join('') || '<div class="empty" style="padding:10px">Заказов нет</div>';
    $('#modalBox').innerHTML = `
        <h3>🪑 Стол №${number} — история заказов (30 дней)</h3>
        ${res.summary ? `<p style="color:var(--muted);font-size:13px">${res.summary.orders} заказ · ${money(res.summary.revenue)}</p>` : ''}
        <div class="order-items-detail" style="max-height:300px;overflow-y:auto">${rows}</div>
        <div class="modal-actions"><button class="btn btn-primary" onclick="closeModal()">Закрыть</button></div>`;
    $('#modal').classList.remove('hidden');
};

function closeModal() { $('#modal').classList.add('hidden'); }
window.closeModal = closeModal;
$('#modal').addEventListener('click', (e) => { if (e.target === $('#modal')) closeModal(); });

// ================= MAHSULOTLAR =================
$('#addProductBtn').onclick = () => productModal(null);

async function loadProducts() {
    const res = await api(`/api/products/catalog/?page=${S.pages.products}&page_size=12`);
    if (!res.success) return;
    const tb = $('#productsTbody');
    tb.innerHTML = '';
    (res.results || []).forEach(p => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${p.image_url ? `<img class="p-thumb" src="${p.image_url}">` : '<div class="p-thumb">🍽</div>'}</td>
            <td><b>${esc(p.name_ru)}</b></td>
            <td>${esc(p.category_name || '')}</td>
            <td><b>${money(p.price)}</b></td>
            <td><button class="toggle ${p.is_available ? 'on' : ''}" onclick="toggleProduct('${p.id}', ${!p.is_available})"></button></td>
            <td style="white-space:nowrap">
                <button class="btn btn-sm btn-blue" onclick="productModal('${p.id}')">✏️</button>
                <button class="btn btn-sm btn-danger" onclick="deleteProduct('${p.id}')">🗑</button>
            </td>`;
        tb.appendChild(tr);
    });
    renderPager('#productsPager', S.pages.products, res.pages, (pg) => { S.pages.products = pg; loadProducts(); });
}

window.toggleProduct = async function (id, val) {
    const res = await api(`/api/products/catalog/${id}/`, {
        method: 'PATCH', body: JSON.stringify({ is_available: val }),
    });
    if (res.success) loadProducts();
};

window.deleteProduct = async function (id) {
    if (!confirm('Подтверждаете удаление товара?')) return;
    const res = await api(`/api/products/catalog/${id}/`, { method: 'DELETE' });
    if (res.success !== false) { toast('Удалён', 'ok'); loadProducts(); }
    else toast(res.message || 'Ошибка', 'error');
};

window.productModal = async function (id) {
    await loadCategories(true);
    const p = id ? await api(`/api/products/catalog/${id}/`) : null;
    const catOpts = S.categories.map(c =>
        `<option value="${c.id}" ${p?.category === c.id ? 'selected' : ''}>${esc(c.name_ru)}</option>`).join('');

    $('#modalBox').innerHTML = `
        <h3>${p ? 'Редактировать товар' : 'Новый товар'}</h3>
        <div class="form-row"><label>Фото</label>
            <input type="file" id="pImage" accept="image/*">
            ${p?.image_url ? `<img class="p-thumb" src="${p.image_url}" style="margin-top:6px">` : ''}
        </div>
        <div class="form-row"><label>Название</label><input id="pNameRu" value="${esc(p?.name_ru || '')}"></div>
        <div class="form-row"><label>Описание</label><textarea id="pDescRu" rows="2">${esc(p?.description_ru || '')}</textarea></div>
        <div class="form-2col">
            <div class="form-row"><label>Цена (сум)</label><input type="number" id="pPrice" min="0" value="${p?.price ?? ''}"></div>
            <div class="form-row"><label>Категория</label><select id="pCategory">${catOpts}</select></div>
        </div>
        <div class="form-row"><label>В продаже</label><select id="pAvailable">
            <option value="true" ${p?.is_available !== false ? 'selected' : ''}>Да</option>
            <option value="false" ${p?.is_available === false ? 'selected' : ''}>Нет</option>
        </select></div>
        <div class="modal-actions">
            <button class="btn btn-ghost" onclick="closeModal()">Отмена</button>
            <button class="btn btn-primary" id="saveProductBtn">Сохранить</button>
        </div>`;
    $('#modal').classList.remove('hidden');

    $('#saveProductBtn').onclick = async () => {
        const fd = new FormData();
        fd.append('name_uz', $('#pNameRu').value.trim());      // uz maydoni = ru (avtomatik)
        fd.append('name_ru', $('#pNameRu').value.trim());
        fd.append('description_uz', $('#pDescRu').value.trim());
        fd.append('description_ru', $('#pDescRu').value.trim());
        fd.append('price', $('#pPrice').value || 0);
        fd.append('category', $('#pCategory').value);
        fd.append('is_available', $('#pAvailable').value);
        const file = $('#pImage').files[0];
        if (file) fd.append('image', file);

        const res = await api(id ? `/api/products/catalog/${id}/` : '/api/products/catalog/', {
            method: id ? 'PATCH' : 'POST', body: fd,
        });
        if (res.success !== false) { closeModal(); toast('Сохранено', 'ok'); loadProducts(); }
        else toast(firstError(res), 'error');
    };
};

// ================= KATEGORIYALAR =================
async function loadCategories(silent = false) {
    const res = await api('/api/products/categories/');
    if (res.success !== false) S.categories = Array.isArray(res) ? res : (res.results || []);
    if (!silent) {
        const tb = $('#categoriesTbody');
        tb.innerHTML = '';
        S.categories.forEach(c => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td style="font-size:18px">${esc(c.icon || '🍽')}</td>
                <td><b>${esc(c.name_ru)}</b></td>
                <td>${c.order_num}</td>
                <td>${c.products_count}</td>
                <td><button class="toggle ${c.is_active ? 'on' : ''}" onclick="toggleCategory('${c.id}', ${!c.is_active})"></button></td>
                <td><button class="btn btn-sm btn-blue" onclick="categoryModal('${c.id}')">✏️</button>
                    <button class="btn btn-sm btn-danger" onclick="deleteCategory('${c.id}')">🗑</button></td>`;
            tb.appendChild(tr);
        });
    }
}
window.toggleCategory = async function (id, val) {
    await api(`/api/products/categories/${id}/`, { method: 'PATCH', body: JSON.stringify({ is_active: val }) });
    loadCategories();
};
window.deleteCategory = async function (id) {
    if (!confirm('Подтверждаете удаление категории?')) return;
    const res = await api(`/api/products/categories/${id}/`, { method: 'DELETE' });
    if (res.success !== false) { toast('Удалена', 'ok'); loadCategories(); }
    else toast(res.message || 'Ошибка', 'error');
};
$('#addCategoryBtn').onclick = () => categoryModal(null);

window.categoryModal = function (id) {
    const c = S.categories.find(x => x.id === id) || {};
    $('#modalBox').innerHTML = `
        <h3>${id ? 'Редактировать категорию' : 'Новая категория'}</h3>
        <div class="form-2col">
            <div class="form-row"><label>Эмодзи</label><input id="cIcon" value="${esc(c.icon || '')}" placeholder="🍲"></div>
            <div class="form-row"><label>Порядок</label><input type="number" id="cOrder" value="${c.order_num ?? 0}"></div>
        </div>

        <div class="form-row"><label>Название</label><input id="cNameRu" value="${esc(c.name_ru || '')}"></div>
        <div class="modal-actions">
            <button class="btn btn-ghost" onclick="closeModal()">Отмена</button>
            <button class="btn btn-primary" id="saveCatBtn">Сохранить</button>
        </div>`;
    $('#modal').classList.remove('hidden');
    $('#saveCatBtn').onclick = async () => {
        const body = {
            icon: $('#cIcon').value.trim(), order_num: +$('#cOrder').value || 0,
            name_uz: $('#cNameRu').value.trim(),
            name_ru: $('#cNameRu').value.trim(),
        };
        const res = await api(id ? `/api/products/categories/${id}/` : '/api/products/categories/', {
            method: id ? 'PATCH' : 'POST', body: JSON.stringify(body),
        });
        if (res.success !== false) { closeModal(); toast('Сохранено', 'ok'); loadCategories(); }
        else toast(firstError(res), 'error');
    };
};

// ================= STOLLAR & QR =================
$('#addTableBtn').onclick = () => tableModal(null);

async function loadTablesPage() {
    const res = await api('/api/restaurant/tables/busy-map/');
    if (!res.success) return;
    const grid = $('#tablesGrid');
    grid.innerHTML = '';
    res.results.forEach(t => {
        // <img>/<a download> teglari Authorization sarlavhasini yubora olmaydi —
        // shuning uchun JWT ni ?token= orqali beramiz + keshni o'tkazib yuborish uchun vaqt belgisi
        const tok = encodeURIComponent(S.access || '');
        const bust = Date.now();
        const qrUrl = `/api/restaurant/tables/${t.id}/qr/?token=${tok}&_=${bust}`;
        const qrDl  = `/api/restaurant/tables/${t.id}/qr/?download=1&label=1&token=${tok}`;
        const card = document.createElement('div');
        card.className = 'table-card-item';
        card.innerHTML = `
            <img class="qr-img" src="${qrUrl}" alt="QR ${t.number}"
                 onerror="this.classList.add('qr-error'); this.title='QR не загрузился — обновите страницу.'">
            <div class="tc-name">🪑 Стол №${t.number}</div>
            <div class="tc-sub">${esc(t.name || '')} · ${t.seats} мест · ${t.is_busy ? '🔴 Занят' : '🟢 Свободен'}</div>
            <div class="tc-actions">
                <a class="btn btn-sm btn-qr" href="${qrDl}" download="stol-${t.number}-qr.png">⬇️ Скачать QR (PNG)</a>
                <button class="btn btn-sm btn-blue" onclick="tableModal('${t.id}')">✏️</button>
                <button class="btn btn-sm btn-warn" onclick="regenQr('${t.id}', ${t.number})">🔄 Обновить QR</button>
                <button class="btn btn-sm btn-danger" onclick="deleteTable('${t.id}', ${t.number})">🗑</button>
            </div>`;
            card.onclick = () => openProduct(p.id);
        grid.appendChild(card);
    });
}

window.regenQr = async function (id, number) {
    if (!confirm(`QR-код стола №${number} будет обновлён. Старые QR-коды перестанут работать. Продолжим?`)) return;
    const res = await api(`/api/restaurant/tables/${id}/regenerate-qr/`, { method: 'POST' });
    if (res.success) { toast(res.message, 'ok'); loadTablesPage(); }
};

window.deleteTable = async function (id, number) {
    if (!confirm(`Стол №${number} будет удалён. Продолжим?`)) return;
    const res = await api(`/api/restaurant/tables/${id}/`, { method: 'DELETE' });
    if (res.success !== false) { toast('Удалён', 'ok'); loadTablesPage(); }
    else toast(res.message || 'Ошибка', 'error');
};

window.tableModal = function (id) {
    const t = S.tables.find(x => x.id === id) || {};
    $('#modalBox').innerHTML = `
        <h3>${id ? 'Редактировать стол' : 'Новый стол'}</h3>
        <div class="form-2col">
            <div class="form-row"><label>Номер</label><input type="number" id="tNumber" min="1" value="${t.number ?? nextTableNumber()}"></div>
            <div class="form-row"><label>Мест</label><input type="number" id="tSeats" min="1" value="${t.seats ?? 4}"></div>
        </div>
        <div class="form-row"><label>Зона / название</label><input id="tName" value="${esc(t.name || '')}" placeholder="Zal 1, Terasa..."></div>
        <div class="form-row"><label>Примечание</label><input id="tNote" value="${esc(t.note || '')}"></div>
        <div class="modal-actions">
            <button class="btn btn-ghost" onclick="closeModal()">Отмена</button>
            <button class="btn btn-primary" id="saveTableBtn">Сохранить (QR создаётся автоматически)</button>
        </div>`;
    $('#modal').classList.remove('hidden');
    $('#saveTableBtn').onclick = async () => {
        const body = {
            number: +$('#tNumber').value, seats: +$('#tSeats').value || 4,
            name: $('#tName').value.trim(), note: $('#tNote').value.trim(), is_active: true,
        };
        const res = await api(id ? `/api/restaurant/tables/${id}/` : '/api/restaurant/tables/', {
            method: id ? 'PATCH' : 'POST', body: JSON.stringify(body),
        });
        if (res.success !== false) { closeModal(); toast('Сохранено — QR-код готов', 'ok'); loadTablesPage(); }
        else toast(firstError(res), 'error');
    };
};

function nextTableNumber() {
    return (S.tables.reduce((m, t) => Math.max(m, t.number), 0) || 0) + 1;
}

// ================= STATISTIKA =================
$('#statsDays').onchange = loadStats;

async function loadStats() {
    const days = $('#statsDays').value;
    const res = await api(`/api/stats/admin/?days=${days}`);
    if (!res.success) { toast('Статистика не загрузилась', 'error'); return; }

    $('#statsKpi').innerHTML = kpi([
        ['💰', money(res.kpi.revenue), `${days} ежедневный доход`],
        ['🧾', res.kpi.orders, 'Всего заказов'],
        ['✅', res.kpi.delivered, 'Доставлен'],
        ['❌', res.kpi.cancelled, 'Отменён'],
        ['🧮', money(res.kpi.avg_check), 'Средний чек'],
        ['⏱', res.kpi.avg_prep_minutes != null ? res.kpi.avg_prep_minutes + ' мин' : '—', 'Среднее время готовки'],
        ['⭐', (res.kpi.avg_rating || 0) + ' / 5', `Рейтинг (${res.kpi.feedback_count} отзывов)`],
    ]);

    // Kunlik daromad grafigi
    drawLine('#chartRevenue', res.trend.map(x => x.date), res.trend.map(x => x.revenue));
    // TOP mahsulot grafigi
    const top = res.demand.slice(0, 10);
    drawBar('#chartTop', top.map(x => x.name), top.map(x => x.qty));

    // Talab jadvali
    $('#demandTbody').innerHTML = res.demand.slice(0, 12).map(d => `
        <tr><td>${esc(d.name)}</td><td><b>${d.qty}</b></td><td>${d.share}%</td>
        <td class="d-${d.color}">${d.level}</td></tr>`).join('');

    $('#tableRevTbody').innerHTML = (res.table_revenue || []).map(t => `
        <tr><td>№${t.table}</td><td>${t.orders}</td><td><b>${money(t.revenue)}</b></td></tr>`).join('')
        || '<tr><td colspan="3" style="color:var(--muted)">Нет данных</td></tr>';

    // Umuman sotilmaganlar
    if (res.never_sold?.length) {
        $('#demandTbody').innerHTML += res.never_sold.slice(0, 6).map(p => `
            <tr><td>${esc(p.name)}</td><td>0</td><td>0%</td><td class="d-low">Не продан</td></tr>`).join('');
    }
}

function drawLine(sel, labels, values) {
    const ctx = $(sel);
    if (S.charts[sel]) S.charts[sel].destroy();
    S.charts[sel] = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [{
                label: 'Доход (сум)', data: values, fill: true, tension: .35,
                borderColor: '#2563eb', backgroundColor: 'rgba(37,99,235,.12)', borderWidth: 2.5,
                pointBackgroundColor: '#2563eb',
            }],
        },
        options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: { y: { ticks: { callback: (v) => v >= 1000 ? (v / 1000) + 'k' : v } } },
        },
    });
}

function drawBar(sel, labels, values) {
    const ctx = $(sel);
    if (S.charts[sel]) S.charts[sel].destroy();
    S.charts[sel] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [{ label: 'Продано (шт.)', data: values, backgroundColor: '#f59e0b', borderRadius: 6 }],
        },
        options: {
            indexAxis: 'y', responsive: true,
            plugins: { legend: { display: false } },
        },
    });
}

// ================= FIKRLAR =================
async function loadFeedback() {
    // Feedbacklar — buyurtmalar orqali (feedback=true filtri yo'q; alohida endpoint bo'lsa yaxshiroq)
    const res = await api('/api/orders/admin-orders/?ordering=-created_at&page_size=30');
    if (!res.success) return;
    const fb = (res.results || []).filter(o => o.feedback);
    const el = $('#feedbackList');
    if (!fb.length) {
        el.innerHTML = '<div class="card empty">Пока нет отзывов</div>';
        return;
    }
    el.innerHTML = fb.map(o => `
        <div class="fb-card">
            <div class="fb-stars">${'★'.repeat(o.feedback.rating)}${'☆'.repeat(5 - o.feedback.rating)}</div>
            <div class="fb-order">#${o.order_number} · Stol №${o.table_number} · ${o.feedback.user_name}</div>
            ${o.feedback.comment ? `<div class="fb-text">«${esc(o.feedback.comment)}»</div>` : '<div class="fb-text" style="color:var(--muted)">Комментарий не написан</div>'}
        </div>`).join('');
}

// ================= Yordamchilar =================
function renderPager(sel, cur, pages, cb) {
    const el = $(sel);
    if (!pages || pages <= 1) { el.innerHTML = ''; return; }
    let html = '';
    for (let i = 1; i <= Math.min(pages, 7); i++) {
        html += `<button class="${i === cur ? 'cur' : ''}" data-p="${i}">${i}</button>`;
    }
    el.innerHTML = html;
    el.querySelectorAll('button').forEach(b => b.onclick = () => cb(+b.dataset.p));
}

function firstError(res) {
    if (res?.error && typeof res.error === 'object') {
        const first = Object.values(res.error)[0];
        if (Array.isArray(first)) return first[0];
        if (typeof first === 'string') return first;
    }
    return res?.message || 'Ошибка';
}

// ---------------- Boot ----------------
(function boot() {
    const access = localStorage.getItem('so_access');
    const refresh = localStorage.getItem('so_refresh');
    if (access && refresh) {
        S.access = access; S.refresh = refresh;
        // Token yaroqliligini tekshirish
        api('/api/auth/me/').then(res => {
            if (res.success && res.user) { S.user = res.user; enterApp(); }
            else if (!refreshTokens()) logout();
            else enterApp();
        }).catch(() => {});
    }
})();

// ================= PROFIL =================
let profAvatarFile = null;   // tanlangan (hali yuklanmagan) rasm fayli

function setAvatar(url) {
    const img = $('#profAvatar');
    const fb = $('#profAvatarFallback');
    if (url) {
        img.src = url + (url.includes('?') ? '&' : '?') + '_=' + Date.now();   // kesh-bust
        img.classList.remove('hidden');
        fb.classList.add('hidden');
    } else {
        img.classList.add('hidden');
        img.removeAttribute('src');
        fb.classList.remove('hidden');
    }
}

async function loadProfile() {
    const res = await api('/api/auth/profile/');
    if (res.success === false) { toast(res.message || 'Профиль не загружен', 'error'); return; }
    const p = res.profile;
    S.user = { ...(S.user || {}), ...p };

    $('#profFirstName').value = p.first_name || '';
    $('#profLastName').value = p.last_name || '';
    $('#profPhone').value = p.phone || '';
    $('#profEmail').value = p.email || '';
    $('#profUsername').textContent = p.username || '—';
    $('#profRole').textContent = p.is_staff ? 'Администратор' : 'Сотрудник';
    $('#profJoined').textContent = p.date_joined
        ? new Date(p.date_joined).toLocaleDateString('ru-RU') : '—';
    setAvatar(p.avatar_url);
    profAvatarFile = null;
}

// --- Rasm tanlash + zudlik bilan ko'rish ---
 $('#profAvatarBtn').onclick = () => $('#profAvatarFile').click();
 $('#profAvatarFile').onchange = () => {
    const f = $('#profAvatarFile').files[0];
    if (!f) return;
    if (f.size > 2 * 1024 * 1024) { toast('Размер изображения должен быть меньше 2 МБ', 'error'); return; }
    profAvatarFile = f;
    setAvatar(URL.createObjectURL(f));   // darhol ko'rish
};

// --- Rasmni serverga yuklash (faqat avatar maydoni PATCH qilinadi) ---
 $('#profAvatarSave').onclick = async () => {
    if (!profAvatarFile) { toast('Сначала выберите изображение', 'error'); return; }
    const fd = new FormData();
    fd.append('avatar', profAvatarFile);
    const res = await api('/api/auth/profile/', { method: 'PATCH', body: fd });
    if (res.success !== false) {
        toast(res.message || 'Фото профиля обновлено', 'ok');
        profAvatarFile = null;
        $('#profAvatarFile').value = '';
        setAvatar(res.profile?.avatar_url);
        S.user = { ...(S.user || {}), ...(res.profile || {}) };
        $('#whoami').textContent = `👤 ${S.user.first_name || S.user.username || ''}`;
    } else toast(res.message || firstError(res), 'error');
};

// --- Ma'lumotlarni saqlash ---
 $('#profSaveBtn').onclick = async () => {
    const fd = new FormData();
    fd.append('first_name', $('#profFirstName').value.trim());
    fd.append('last_name', $('#profLastName').value.trim());
    fd.append('phone', $('#profPhone').value.trim());
    fd.append('email', $('#profEmail').value.trim());
    const res = await api('/api/auth/profile/', { method: 'PATCH', body: fd });
    if (res.success !== false) {
        toast(res.message || 'Профиль сохранён', 'ok');
        S.user = { ...(S.user || {}), ...(res.profile || {}) };
        $('#whoami').textContent = `👤 ${S.user.first_name || S.user.username || ''}`;
    } else toast(res.message || firstError(res), 'error');
};

// --- Parolni o'zgartirish ---
 $('#profPassBtn').onclick = async () => {
    const oldP = $('#profOldPass').value, newP = $('#profNewPass').value, newP2 = $('#profNewPass2').value;
    if (!oldP || !newP) { toast('Заполните все поля пароля', 'error'); return; }
    if (newP.length < 6) { toast('Новый пароль должен содержать не менее 6 символов', 'error'); return; }
    if (newP !== newP2) { toast('Новые пароли не совпадают', 'error'); return; }
    const res = await api('/api/auth/profile/password/', {
        method: 'POST', body: JSON.stringify({ old_password: oldP, new_password: newP }),
    });
    if (res.success !== false) {
        toast(res.message || 'Пароль обновлён', 'ok');
        $('#profOldPass').value = $('#profNewPass').value = $('#profNewPass2').value = '';
    } else {
        // DRF xatosi: {old_password: ["Eski parol noto'g'ri."]} ko'rinishida kelishi mumkin
        toast(res.message || firstError(res) || 'Пароль не изменён', 'error');
    }
};