/* ============================================================
   SmartOshxona Mini App — app.js
   Oqim (talabga mos):
     1. Telegram botga /start → «Menyu» → Mini App ochiladi
     2. initData bilan JWT olinadi (xavfsizlik: server tekshiradi)
     3. Mahsulotlar kartochkalari — 2 ustunli grid
     4. Savat → «Buyurtma berish» → QR skanerlash so'raladi
     5. QR skanerlangach «Tasdiqlaysizmi?» → Ha → buyurtma stol raqami bilan oshxonaga
   ============================================================ */
'use strict';

const tg = window.Telegram.WebApp;
const API = window.location.origin;          // Mini App bilan API bir domenda

// ---------- Holat ----------
const state = {
    token: null,
    user: null,
    lang: 'ru',
    categories: [],
    activeCategory: 'all',
    products: [],            // flat ro'yxat (kartochkalar)
    cart: null,
    orders: [],
    confirmData: null,       // {table_number, qr_token, table}
    pollTimer: null,
};

// ---------- i18n ----------
const I18N = {
    uz: {
        navMenu: 'Меню', navCart: 'Корзина', navOrders: 'Мои заказы', navFeedback: 'Отзыв',
        navAbout: 'О нас', tabAbout: 'О нас', tabOrders: 'Мои заказы',
        heroSub: 'Отсканируйте QR-код на столе, выберите блюда — без официанта и очереди.',
        heroCta: 'Смотреть меню', heroOrder: 'Заказать',
        footerTag: 'Гостеприимство — наш девиз',
        footerHours: '🕘 Ежедневно 10:00 – 22:00', footerPhone: '📞 Позвонить',
        items: 'товаров', cartTitle: 'Корзина',
        checkout: '📷 Оформить заказ (QR-скан)',
        total: 'Итого:', notePlaceholder: 'Комментарий (например: не остро)',
        confirmTitle: 'Подтверждаете заказ?',
        confirmYes: '✅ Да, подтверждаю', confirmNo: 'Отмена',
        successTitle: 'Заказ принят!',
        successHint: 'Когда будет готово — сообщим в боте. Приятного аппетита!',
        successOk: 'Спасибо, понятно',
        emptyCart: 'Корзина пуста — выберите блюда из меню',
        emptyOrders: 'У вас пока нет заказов',
        fbTitle: 'Оставить отзыв',
        fbHint: 'Выберите доставленный заказ и оставьте оценку и отзыв.',
        fbEmpty: 'Пока нет заказов, доступных для оценки.\nСделайте заказ — после доставки оцените его здесь.',
        fbPlaceholder: 'Ваш отзыв (необязательно)...', fbSubmit: 'Отправить',
        fbThanks: 'Спасибо за ваш отзыв!',
        fbRated: 'Оценено',
        fbLabels: ['', 'Очень плохо', 'Плохо', 'Средне', 'Хорошо', 'Восхитительно!'],
        scanPrompt: 'Отсканируйте QR-код под столом',
        greet: 'Добро пожаловать',
        status: { new: '🆕 Новый', preparing: '👨‍🍳 Готовится', in_progress: '🚶 В процессе', delivered: '✅ Доставлено', cancelled: '❌ Отменён' },
    },
    ru: {
        navMenu: 'Меню', navCart: 'Корзина', navOrders: 'Мои заказы', navFeedback: 'Отзыв',
        navAbout: 'О нас', tabAbout: 'О нас', tabOrders: 'Мои заказы',
        heroSub: 'Отсканируйте QR-код на столе, выберите блюда — без официанта и очереди.',
        heroCta: 'Смотреть меню', heroOrder: 'Заказать',
        footerTag: 'Гостеприимство — наш девиз',
        footerHours: '🕘 Ежедневно 10:00 – 22:00', footerPhone: '📞 Позвонить',
        items: 'товаров', cartTitle: 'Корзина',
        checkout: '📷 Оформить заказ (QR-скан)',
        total: 'Итого:', notePlaceholder: 'Комментарий (например: не остро)',
        confirmTitle: 'Подтверждаете заказ?',
        confirmYes: '✅ Да, подтверждаю', confirmNo: 'Отмена',
        successTitle: 'Заказ принят!',
        successHint: 'Когда будет готово — сообщим в боте. Приятного аппетита!',
        successOk: 'Спасибо, понятно',
        emptyCart: 'Корзина пуста — выберите блюда из меню',
        emptyOrders: 'У вас пока нет заказов',
        fbTitle: 'Оставить отзыв',
        fbHint: 'Выберите доставленный заказ и оставьте оценку и отзыв.',
        fbEmpty: 'Пока нет заказов, доступных для оценки.\nСделайте заказ — после доставки оцените его здесь.',
        fbPlaceholder: 'Ваш отзыв (необязательно)...', fbSubmit: 'Отправить',
        fbThanks: 'Спасибо за ваш отзыв!',
        fbRated: 'Оценено',
        fbLabels: ['', 'Очень плохо', 'Плохо', 'Средне', 'Хорошо', 'Восхитительно!'],
        scanPrompt: 'Отсканируйте QR-код под столом',
        greet: 'Добро пожаловать',
        status: { new: '🆕 Новый', preparing: '👨‍🍳 Готовится', in_progress: '🚶 В процессе', delivered: '✅ Доставлено', cancelled: '❌ Отменён' },
    },
};
const t = (key) => (I18N[state.lang] && I18N[state.lang][key]) ?? I18N.uz[key] ?? key;

// ---------- Yordamchilar ----------
const $ = (sel) => document.querySelector(sel);
const fmt = (n) => Number(n).toLocaleString('ru-RU').replace(/,/g, ' ') + ' сум';

function toast(msg, type = '') {
    const el = $('#toast');
    el.textContent = msg;
    el.className = 'toast ' + type;
    setTimeout(() => el.classList.add('hidden'), 2600);
}

function haptic(type = 'light') {
    try {
        if (type === 'ok') tg.HapticFeedback.notificationOccurred('success');
        else if (type === 'error') tg.HapticFeedback.notificationOccurred('error');
        else tg.HapticFeedback.impactOccurred('light');
    } catch (e) { /* ignore */ }
}

async function api(path, options = {}) {
    const headers = { 'Content-Type': 'application/json', ...options.headers };
    headers['ngrok-skip-browser-warning'] = '1';
    if (state.token) headers['Authorization'] = `Bearer ${state.token}`;
    const res = await fetch(API + path, { ...options, headers });
    if (res.status === 401) {          // token eskirdi → qayta auth + 1 marta qayta urinish
        try { await auth(); } catch (e) { /* ignore */ }
        if (state.token) {
            headers['Authorization'] = `Bearer ${state.token}`;
            return fetch(API + path, { ...options, headers }).then(r => r.json());
        }
        return { success: false, message: 'Авторизация не удалась — обновите страницу' };
    }
    return res.json();
}

// ---------- Telegram init + auth ----------
async function boot() {
    tg.ready();
    tg.expand();
    try { tg.setHeaderColor('#f6f0e6'); tg.setBackgroundColor('#f6f0e6'); } catch (e) {}

    const userLang = 'ru';       // FAQAT RUS TILI
    setLang(userLang);

    $('#brandName').textContent = document.title.split('—')[0].trim();
    $('#footerName').textContent = document.title.split('—')[0].trim();

    try { await auth(); } catch (e) {
        toast('Ошибка авторизации: ' + (e && e.message ? e.message : 'обновите страницу'), 'error');
    }
    await Promise.all([loadMenu(), loadCart(), loadOrders()]);

    // Buyurtma holatini har 20 sekundda yangilab turish
    state.pollTimer = setInterval(loadOrders, 20000);
}

async function auth() {
    const initData = tg.initData;
    let res;

        if (initData) {
        res = await fetch(API + '/api/auth/telegram/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ init_data: initData }),
        }).then(r => r.json()).catch(() => ({ success: false, message: 'Serverga ulanmadi' }));
    } else {
        // Oddiy brauzerda ochilgan (Telegram tashqarisida) — dev-guest auth
        res = await fetch(API + '/api/auth/dev-guest/', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
        }).then(r => r.json()).catch(() => ({ success: false, message: 'Не удалось подключиться к серверу.' }));
    }

    if (!res.success) throw new Error(res.message || 'Ошибка авторизации.');
    state.token = res.access;
    state.user = res.user;
    const name = res.user.first_name || res.user.telegram_username || '';
    $('#greeting').textContent = `${t('greet')}, ${name}! 👋`;
}
// ---------- Menyu ----------
async function loadMenu() {
    const grid = $('#productsGrid');
    grid.innerHTML = '<div class="skel"></div><div class="skel"></div><div class="skel"></div><div class="skel"></div>';

    const res = await api(`/api/products/menu/?lang=${state.lang}`);
    if (!res.success) { toast('Меню не загрузилось.', 'error'); return; }

    state.categories = res.categories;
    renderChips();
    state.products = [];
    res.categories.forEach(c => {
        c.products.forEach(p => state.products.push({ ...p, category_id: c.id }));
    });
    renderProducts();
}

function renderChips() {
    const box = $('#catChips');
    box.innerHTML = '';
    const mk = (id, label) => {
        const b = document.createElement('button');
        b.className = 'chip' + (state.activeCategory === id ? ' active' : '');
        b.textContent = label;
        b.onclick = () => { state.activeCategory = id; renderChips(); renderProducts(); haptic(); };
        box.appendChild(b);
    };
    mk('all', '☰ ' + (state.lang === 'ru' ? 'Все' : 'Все'));
    state.categories.forEach(c => mk(c.id, `${c.icon || '🍽'} ${c.name}`));
}

function renderProducts() {
    const grid = $('#productsGrid');
    grid.innerHTML = '';
    const list = state.products.filter(p =>
        state.activeCategory === 'all' || p.category_id === state.activeCategory);

    if (!list.length) {
        grid.innerHTML = `<div class="empty">:(<br>${state.lang === 'ru' ? 'Меню пусто' : 'Меню пусто'}</div>`;
        return;
    }

    list.forEach((p, idx) => {

        const featured = (state.activeCategory === 'all' && idx === 0 && p.is_available);
        const card = document.createElement('div');
        card.className = 'product-card' + (p.is_available ? '' : ' unavailable') + (featured ? ' featured' : '');
        card.innerHTML = `
            ${p.image_url
                ? `<img class="p-img" src="${p.image_url}" alt="${p.name}" loading="lazy">`
                : `<div class="p-img">🍽</div>`}
            <div class="p-body">
                <div class="p-name">${p.name}</div>
                <div class="p-desc">${p.description || ''}</div>
                <div class="p-foot">
                    <span class="p-price">${fmt(p.price)}</span>
                    ${p.is_available ? `<button class="p-add" data-add="${p.id}" aria-label="Добавить в корзину">
                               <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/></svg>
                           </button>`
                        : `<span style="font-size:11px;color:var(--muted)">${state.lang === 'ru' ? 'Нет в наличии' : 'Нет в наличии'}</span>`}
                </div>
            </div>`;
            card.onclick = () => openProduct(p.id);
        grid.appendChild(card);
    });

    // Hodisalar (delegatsiya)

    grid.querySelectorAll('[data-add]').forEach(b =>
    b.onclick = (e) => { e.stopPropagation(); addToCart(b.dataset.add, 1); });
}
// ---------- Mahsulot detali ----------
function openProduct(id) {
    const p = state.products.find(x => x.id === id);
    if (!p) return;
    haptic();
    $('#pdImage').src = p.image_url || '';
    $('#pdImage').style.display = p.image_url ? 'block' : 'none';
    $('#pdEmoji').style.display = p.image_url ? 'none' : 'block';
    $('#pdName').textContent = p.name;
    $('#pdDesc').textContent = p.description || '';
    $('#pdPrice').textContent = fmt(p.price);
    $('#pdQty').textContent = '1';
    const add = $('#pdAdd');
    add.dataset.pid = p.id;
    add.disabled = !p.is_available;
    add.textContent = p.is_available ? (state.lang === 'ru' ? '🛒 Добавить в корзину' : '🛒 Добавить в корзину')
        : (state.lang === 'ru' ? 'Нет в наличии' : 'Нет в наличии');
    $('#productOverlay').classList.remove('hidden');
}
function closeProduct() { $('#productOverlay').classList.add('hidden'); }

 $('#pdClose').onclick = closeProduct;
 $('#pdMinus').onclick = () => {
    $('#pdQty').textContent = Math.max(1, +$('#pdQty').textContent - 1);
};
 $('#pdPlus').onclick = () => { $('#pdQty').textContent = +$('#pdQty').textContent + 1; };
 $('#pdAdd').onclick = () => {
    const qty = +$('#pdQty').textContent || 1;
    closeProduct();
    addToCart($('#pdAdd').dataset.pid, qty);
};
 $('#productOverlay').addEventListener('click', (e) => {
    if (e.target.id === 'productOverlay') closeProduct();
});

// ---------- Savat ----------
async function loadCart() {
    const res = await api('/api/orders/cart/');
    if (res.success) { state.cart = res.cart; renderCartBar(); }
}

function cartQty(productId) {
    if (!state.cart) return 0;
    const item = (state.cart.items || []).find(i => i.product_id === productId);
    return item ? item.quantity : 0;
}

function renderCartBar() {
    // Pastki navigatsiya belgisi (savatdagi mahsulotlar soni)
    const badge = $('#cartBadge');
    const count = state.cart?.items_count || 0;
    if (count > 0) { badge.textContent = count > 99 ? '99+' : count; badge.classList.remove('hidden'); }
    else { badge.classList.add('hidden'); }
    renderCartModal();          // savat sahifasi (tab)
}

function renderCartModal() {
    const box = $('#cartItems');
    if (!state.cart || !state.cart.items?.length) {
        box.innerHTML = `<div class="empty">${t('emptyCart')}</div>`;
        return;
    }
    box.innerHTML = '';
    state.cart.items.forEach(i => {
        const row = document.createElement('div');
        row.className = 'c-item';
        row.innerHTML = `
            <div class="c-info">
                <div class="c-name">${i.name}</div>
                <div class="c-price">${fmt(i.price)} × ${i.quantity} = ${fmt(i.total_price)}</div>
            </div>
            <div class="c-qty">
                <button class="minus" data-ci-minus="${i.id}">−</button>
                <span>${i.quantity}</span>
                <button class="plus" data-ci-plus="${i.id}">+</button>
            </div>`;
        box.appendChild(row);
    });
    box.querySelectorAll('[data-ci-plus]').forEach(b =>
        b.onclick = () => updateCartItem(b.dataset.ciPlus, 1));
    box.querySelectorAll('[data-ci-minus]').forEach(b =>
        b.onclick = () => updateCartItem(b.dataset.ciMinus, -1));
    $('#cartModalTotal').textContent = fmt(state.cart.total_amount);
}

async function addToCart(productId, qty = 1) {
    haptic();
    const res = await api('/api/orders/cart/add/', {
        method: 'POST', body: JSON.stringify({ product_id: productId, quantity: qty }),
    });
    if (res.success) {
        state.cart = res.cart;
        renderCartBar(); renderProducts();
        toast(res.message, 'ok');
    } else toast(res.message || 'Ошибка.', 'error');
}

async function removeFromCart(productId) {
    if (!state.cart) return;
    const item = state.cart.items.find(i => i.product_id === productId);
    if (!item) return;
    haptic();
    if (item.quantity <= 1) {
        const res = await api(`/api/orders/cart/items/${item.id}/`, { method: 'DELETE' });
        if (res.success) state.cart = res.cart;
    } else {
        const res = await api(`/api/orders/cart/items/${item.id}/`, {
            method: 'PATCH', body: JSON.stringify({ quantity: item.quantity - 1 }),
        });
        if (res.success) state.cart = res.cart;
    }
    renderCartBar(); renderProducts();
}

async function updateCartItem(itemId, delta) {
    const item = state.cart.items.find(i => i.id === itemId);
    if (!item) return;
    haptic();
    const newQty = item.quantity + delta;
    if (newQty < 1) {
        const res = await api(`/api/orders/cart/items/${itemId}/`, { method: 'DELETE' });
        if (res.success) state.cart = res.cart;
    } else {
        const res = await api(`/api/orders/cart/items/${itemId}/`, {
            method: 'PATCH', body: JSON.stringify({ quantity: newQty }),
        });
        if (res.success) state.cart = res.cart;
    }
    renderCartBar(); renderProducts();
}

// ---------- Buyurtma berish: QR skanerlash oqimi ----------
async function checkout() {
    if (!state.cart || !state.cart.items?.length) {
        toast(t('emptyCart'), 'error'); return;
    }

    // 1) QR skanerlash so'raladi (Telegram native QR popup)
    if (tg.showScanQrPopup) {
        tg.showScanQrPopup({ text: t('scanPrompt') }, (result) => {
            const parsed = parseQr(result);
            if (!parsed) {
                toast(state.lang === 'ru' ? 'QR-код не относится к этому столу' : 'QR-код не относится к этому столу', 'error');
                return false;      // popup ochiq qoladi, boshqa QR skanerlash mumkin
            }
            tg.closeScanQrPopup();
            validateTable(parsed);
            return true;
        });
    } else {
        // Fallback: qo'lda kiritish (eski Telegram versiyalari)
        const raw = prompt(state.lang === 'ru'
            ? 'Введите код со стола (SMARTOX:TABLE:№:токен):'
            : 'Введите код со стола (SMARTOX:TABLE:№:токен):');
        const parsed = parseQr(raw || '');
        if (parsed) validateTable(parsed);
        else toast('Неверный код.', 'error');
    }
}

function parseQr(raw) {
    if (!raw) return null;
    let text = String(raw).trim();
    // URL ichidan ham ajratib olish (https://dom.uz/?qr=SMARTOX:TABLE:5:token)
    if (text.includes('qr=')) text = decodeURIComponent(text.split('qr=')[1]);
    const prefix = 'SMARTOX:TABLE:';
    if (!text.startsWith(prefix)) return null;
    const rest = text.slice(prefix.length);
    const idx = rest.indexOf(':');
    if (idx < 1) return null;
    const number = parseInt(rest.slice(0, idx), 10);
    const token = rest.slice(idx + 1).trim();
    if (!number || token.length < 8) return null;
    return { table_number: number, qr_token: token };
}

async function validateTable(parsed) {
    const res = await api('/api/restaurant/tables/validate/', {
        method: 'POST', body: JSON.stringify(parsed),
    });
    if (!res.success) { toast(res.message, 'error'); haptic('error'); return; }

    // 2) Skanerlangach — tasdiqlash so'rovi
    state.confirmData = { ...parsed, table: res.table };
    showConfirm();
}

function showConfirm() {
    const { table, qr_token, table_number } = state.confirmData;
    const itemsCount = state.cart.items_count;
    $('#confirmInfo').innerHTML = `
        🪑 <b>Стол №{table_number}</b>${table.name ? ` (${table.name})` : ''}<br>
        🍽 ${itemsCount} ${t('items')} позиций<br>
        💰 Итого: <b>${fmt(state.cart.total_amount)}</b><br><br>
        Заказ будет отправлен на кухню с этим номером стола.`;
    $('#confirmOverlay').classList.remove('hidden');
}

async function confirmOrder() {
    if (!state.confirmData) return;
    $('#confirmYes').disabled = true;

    const res = await api('/api/orders/orders/', {
        method: 'POST',
        body: JSON.stringify({
            table_number: state.confirmData.table_number,
            qr_token: state.confirmData.qr_token,
            items: state.cart.items.map(i => ({ product_id: i.product_id, quantity: i.quantity })),
            customer_note: $('#orderNote').value || '',
        }),
    });
    $('#confirmYes').disabled = false;
    $('#confirmOverlay').classList.add('hidden');

    if (res.success) {
        haptic('ok');
        const o = res.order;
        $('#successSub').innerHTML =
            `№ <b>${o.order_number}</b> · Stol №${o.table_number}<br>${fmt(o.total)}`;
        $('#successOverlay').classList.remove('hidden');
        state.cart = { items: [], items_count: 0, total_amount: 0 };
        $('#orderNote').value = '';
        renderCartBar();
        loadOrders();
    } else {
        haptic('error');
        toast(res.message || 'Заказ не отправлен.', 'error');
    }
}

// ---------- Buyurtmalarim ----------
async function loadOrders() {
    const res = await api('/api/orders/orders/?page_size=10');
    if (!res.success) return;
    state.orders = res.results || [];
    renderOrders();
}

function renderOrders() {
    const box = $('#ordersList');
    if (!state.orders.length) {
        box.innerHTML = `<div class="empty">${t('emptyOrders')}</div>`;
        return;
    }
    box.innerHTML = '';
    state.orders.forEach(o => {
        const st = t('status')[o.status] || o.status_display;
        const card = document.createElement('div');
        card.className = 'order-card';
        card.innerHTML = `
            <div class="o-head">
                <span class="o-num">№ ${o.order_number}</span>
                <span class="o-status ${o.status}">${st}</span>
            </div>
            <div class="o-meta">🪑 Stol №${o.table_number} · 🕒 ${new Date(o.created_at).toLocaleString('ru-RU')}</div>
            <div class="o-items">${o.items.map(i => `• ${i.product_name} × ${i.quantity}`).join('<br>')}</div>
            ${o.customer_note ? `<div class="o-note">📝 ${o.customer_note}</div>` : ''}
            <div class="o-total">${fmt(o.total)}</div>`;
        box.appendChild(card);
    });
    renderFeedbackTargets();       // fikr bo'limini ham yangilab turish
}

// ---------- Fikr qoldirish ----------
let fbOrderId = null;
let fbRating = 0;

function renderFeedbackTargets() {
    const box = $('#fbOrders');
    if (!box) return;
    const eligible = state.orders.filter(o => o.status === 'delivered');

    if (!eligible.length) {
        box.innerHTML = `<div class="empty">${t('fbEmpty').replace(/\n/g, '<br>')}</div>`;
        $('#fbForm').classList.add('hidden');
        return;
    }

    box.innerHTML = '';
    eligible.forEach(o => {
        const el = document.createElement('button');
        el.className = 'fb-order' + (o.has_feedback ? ' rated' : '') + (fbOrderId === o.id ? ' selected' : '');
        el.innerHTML = `
            <div class="fb-order-main">
                <span class="fb-order-num">№ ${o.order_number}</span>
                <span class="fb-order-meta">🪑 Стол №${o.table_number} · ${fmt(o.total)}</span>
            </div>
            ${o.has_feedback
                ? `<span class="fb-order-badge">★ ${o.feedback?.rating || ''} · ${t('fbRated')}</span>`
                : `<span class="fb-order-badge gold">${state.lang === 'ru' ? 'Выбрать' : 'Выбрать'}</span>`}`;
        el.onclick = () => {
            if (o.has_feedback) return;
            fbOrderId = o.id;
            $('#fbForm').classList.remove('hidden');
            renderFeedbackTargets();
        };
        box.appendChild(el);
    });
    if (!fbOrderId) $('#fbForm').classList.add('hidden');
}

function paintStars() {
    document.querySelectorAll('#fbStars button').forEach(b => {
        b.classList.toggle('on', Number(b.dataset.star) <= fbRating);
    });
    $('#fbStarLabel').textContent = fbRating ? t('fbLabels')[fbRating] : '';
}

async function submitFeedback() {
    if (!fbOrderId) return;
    if (!fbRating) {
        toast(state.lang === 'ru' ? 'Сначала поставьте оценку' : 'Сначала поставьте оценку', 'error');
        return;
    }
    $('#fbSubmit').disabled = true;
    const res = await api(`/api/orders/orders/${fbOrderId}/feedback/`, {
        method: 'POST',
        body: JSON.stringify({ rating: fbRating, comment: $('#fbComment').value || '' }),
    });
    $('#fbSubmit').disabled = false;
    if (res.success) {
        haptic('ok');
        toast(t('fbThanks'), 'ok');
        fbOrderId = null; fbRating = 0;
        $('#fbComment').value = '';
        paintStars();
        $('#fbForm').classList.add('hidden');
        loadOrders();
    } else {
        haptic('error');
        toast(res.message || 'Ошибка', 'error');
    }
}

function setLang(lang) {
    state.lang = lang;
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.dataset.i18n;
        const val = t(key);
        if (typeof val === 'string') el.textContent = val;
    });
    $('#langToggle').textContent = lang === 'uz' ? 'RU' : 'UZ';
    if (state.user) {
        const name = state.user.first_name || state.user.telegram_username || '';
        $('#greeting').textContent = `${t('greet')}, ${name}! 👋`;
    }
    renderProducts(); renderOrders(); renderCartBar();
    renderFeedbackTargets();
}

function closeSheet(sel) { $(sel).classList.add('hidden'); }

function switchTab(name) {
    document.querySelectorAll('.bn-item').forEach(x =>
        x.classList.toggle('active', x.dataset.tab === name));
    document.querySelectorAll('.tab-content').forEach(x => x.classList.remove('active'));
    $(`#tab-${name}`).classList.add('active');
    window.scrollTo({ top: 0 });
    if (name === 'orders') loadOrders();
    if (name === 'feedback') renderFeedbackTargets();
    if (name === 'cart') renderCartBar();
    haptic();
}

document.addEventListener('DOMContentLoaded', () => {
    // Pastki navigatsiya (fixed): [Menyu | Savat | Buyurtmalarim | Fikr]
    document.querySelectorAll('.bn-item').forEach(btn => {
        btn.onclick = () => switchTab(btn.dataset.tab);
    });

    // Hero CTA tugmalari
    $('#heroMenuBtn').onclick = () => {
        $('#catChips').scrollIntoView({ behavior: 'smooth', block: 'start' });
    };
    $('#heroOrderBtn').onclick = () => {
        if (state.cart?.items_count) switchTab('cart');
        else { toast(state.lang === 'ru' ? 'Сначала выберите блюда из меню' : 'Сначала выберите блюда из меню'); switchTab('menu'); }
    };

    $('#langToggle').onclick = () => setLang(state.lang === 'uz' ? 'ru' : 'uz');
    $('#checkoutBtn').onclick = checkout;
    $('#confirmYes').onclick = confirmOrder;
    $('#confirmNo').onclick = () => closeSheet('#confirmOverlay');
    $('#successOk').onclick = () => { closeSheet('#successOverlay'); switchTab('orders'); };

    // Fikr qoldirish: yulduzchalar + yuborish
    document.querySelectorAll('#fbStars button').forEach(b => {
        b.onclick = () => { fbRating = Number(b.dataset.star); paintStars(); haptic(); };
    });
    $('#fbSubmit').onclick = submitFeedback;

    // Overlay foniga bosganda yopish
    ['#confirmOverlay', '#successOverlay'].forEach(sel => {
        $(sel).addEventListener('click', (e) => { if (e.target === $(sel)) closeSheet(sel); });
    });

    document.querySelectorAll('.about-card[href^="http"]').forEach(a => {
        a.addEventListener('click', (e) => {
            if (tg.openLink) { e.preventDefault(); tg.openLink(a.href); }
        });
    });
    boot();
});
