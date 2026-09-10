# 🍽 SmartOshxona — Oshxona avtomatlashtirish tizimi

Restoran/oshxona uchun **Telegram Bot + Mini App + Web Admin Panel** — QR kod orqali stol xizmatining to'liq avtomatlashtirilgan tizimi.

> ✅ Loyiha **to'liq ishlaydigan** holatda: backend, bot, Mini App, admin panel,
> WebSocket real-time, QR generatsiya/skanerlash, statistika, demo ma'lumotlar va hujjatlar.

---

## 🎯 Tizim qanday ishlaydi (mijoz oqimi)

1. Har bir stolda **QR kod** bor — mijoz stolga o'tiradi.
2. Mijoz Telegram botga `/start` yozadi → asosiy menyu chiqadi.
3. **"Menyu"** tugmasi → **Telegram Mini App** ochiladi.
4. Mahsulotlar **kartochka ko'rinishida** (rasm, nom, narx, izoh) **2 qatorda** chiqadi.
5. Mijoz mahsulotlarni **savatga qo'shadi**.
6. **"Buyurtma berish"** → **QR kod skanerlash** so'raladi.
7. Skanerlangach **"Buyurtmangizni tasdiqlaysizmi?"** so'rovi chiqadi.
8. **Ha** → buyurtma **stol raqami bilan oshxonaga** yuboriladi.
9. Holat o'zgarganda mijozga **Telegram xabar** boradi; tayyor bo'lgach stolga yetkaziladi.
10. Yakunda mijoz **baho + sharh** qoldiradi.

## 🧑‍💼 Admin panel imkoniyatlari

- 📊 **Dashboard** — bugungi daromad, buyurtmalar, o'rtacha chek, stollar xaritasi (band/bo'sh)
- 🧾 **Buyurtmalar** — real-time (WebSocket toast), holatlar (yangi/tayyorlanmoqda/jarayonda/yetkazildi/bekor), **vaqt oralig'i va holat filtrlari**, navbat tartibi, har bir stolning tarixi
- 🍕 **Mahsulotlar CRUD** — rasm, nom (uz/ru), narx, izoh; kategoriyalar
- 🪑 **Stollar CRUD** — QR kod yaratish/yuklab olish (plakat), token yangilash, o'chirish
- 📈 **Statistika** — bugungi eng ko'p sotilgan, sotilmagan mahsulotlar, talab darajasi, kunlik daromad grafigi, stollar tushumi, reyting
- ⭐ **Fikrlar** — mijozlar baholari va sharhlari

---

## ⚙️ Texnologiyalar

| Qism | Texnologiya |
|---|---|
| Backend | Python **Django 5** + DRF + SimpleJWT |
| Real-time | **Channels + Daphne (ASGI)** + Redis |
| Ma'lumotlar bazasi | **PostgreSQL 16** (lokal demo uchun SQLite ham bor) |
| Bot | **aiogram 3** (polling) |
| Mini App | Telegram WebApp SDK + Vanilla JS |
| Admin panel | Vanilla JS SPA + Chart.js 4 |
| QR | `qrcode[pil]` (generatsiya) + `showScanQrPopup` (skaner) |
| Deploy | Docker Compose (db, redis, web, bot) |

To'liq asoslash: [docs/03_texnologiyalar.md](docs/03_texnologiyalar.md)

---

## 🚀 Ishga tushirish

### Variant A — Docker (tavsiya)

```bash
git clone <repo> && cd smart-oshxona
cp .env.example .env           # to'ldiring (BOT_TOKEN, MINI_APP_URL...)
docker compose up -d --build
# → http://localhost:8000/adminpanel/  (admin / admin123)
# → http://localhost:8000/miniapp/     (Telegram ichida ochiladi)
# → http://localhost:8000/api/docs/    (Swagger)
```

### Variant B — Lokal (tez ko'rish uchun)

```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp ../.env.example ../.env
# .env da: DB_ENGINE=sqlite  USE_REDIS=False  DEBUG=True

python manage.py migrate
python manage.py seed_demo
python manage.py runserver            # → http://127.0.0.1:8000

# ikkinchi terminalda bot:
python -m bot.main
```

### Demo ma'lumotlarni tozalash va o'z ma'lumotingizni kiritish

```bash
# Demo ma'lumotlarni tozalash (interaktiv menyu):
python manage.py clear_data

# Yoki to'g'ridan-to'g'ri:
python manage.py clear_data --orders      # faqat buyurtmalar, savatlar, fikrlar
python manage.py clear_data --products    # faqat menyu (mahsulot + kategoriya)
python manage.py clear_data --tables      # faqat stollar
python manage.py clear_data --all --yes   # hammasi (superuser qoladi), tasdiqsiz
```

Superuser (admin) hech qachon o'chmaydi. Tozalagandan keyin o'z
ma'lumotlaringizni shu joylardan kiritasiz:

| Joy | Manzil | Nima qilish mumkin |
|-----|--------|--------------------|
| Django admin | `http://localhost:8000/admin/` | Kategoriya, mahsulot (rasmi bilan), stol, narx tarixi — to'liq CRUD |
| Admin panel | `http://localhost:8000/adminpanel/` | Buyurtmalarni boshqarish, statistika, QR |
| Mini App | Telegram ichida | Haqiqiy mijoz sifatida test qilish |

### Telegram tomonini ulash

1. **@BotFather** → `/newbot` → tokenni `.env` ga yozing.
2. Mini App'ni internetga chiqaring (masalan ngrok: `ngrok http 8000`).
3. `.env`: `MINI_APP_URL=https://<domeningiz>/miniapp/`
4. BotFather → `/setmenubutton` → bot URL'ini Mini App sifatida bog'lang.
5. Admin panel → Stollar → QR yuklab olish → stolga qo'ying.

---

## 📁 Loyiha tuzilmasi

```
smart-oshxona/
├── backend/
│   ├── config/          # Django sozlamalari (settings, asgi...)
│   ├── apps/
│   │   ├── users/       # Telegram + admin auth (JWT)
│   │   ├── restaurant/  # Stollar + QR generatsiya
│   │   ├── products/    # Menyu: kategoriyalar, mahsulotlar
│   │   ├── orders/      # Buyurtma, savat, fikr + WebSocket
│   │   ├── notifications/  # Telegram xabarlar + jurnal
│   │   ├── analytics/   # Statistika endpointlari
│   │   └── core/        # seed_demo
│   ├── bot/             # aiogram 3 (handlers, keyboards, FSM)
│   ├── templates/       # miniapp/ + adminpanel/ sahifalari
│   └── static/          # JS/CSS fayllari
├── docs/                # 7 bo'lim hujjatlar + API.md
├── docker-compose.yml
└── .env.example
```

## 📚 Hujjatlar (siz so'ragan 7 ta javob)

| # | Mavzu | Fayl |
|---|---|---|
| 1 | Arxitektura va tuzilma (diagramma) | [docs/01_arxitektura.md](docs/01_arxitektura.md) |
| 2 | Ma'lumotlar bazasi sxemasi (ER) | [docs/02_er_diagramma.md](docs/02_er_diagramma.md) |
| 3 | Texnologiyalar tavsiyasi | [docs/03_texnologiyalar.md](docs/03_texnologiyalar.md) |
| 4 | Bosqichma-bosqich roadmap | [docs/04_roadmap.md](docs/04_roadmap.md) |
| 5 | Xavfsizlik tavsiyalari | [docs/05_xavfsizlik.md](docs/05_xavfsizlik.md) |
| 6 | Kutilayotgan natijalar / KPI | [docs/06_kpi_natijalar.md](docs/06_kpi_natijalar.md) |
| 7 | Muammolar va yechimlar | [docs/07_muammolar_va_yechimlar.md](docs/07_muammolar_va_yechimlar.md) |
| 8 | **NGROK orqali lokal ishga tushirish** | [docs/08_ngrok_ishga_tushirish.md](docs/08_ngrok_ishga_tushirish.md) |
| + | API endpointlar | [docs/API.md](docs/API.md) |

## 🖥 Admin panel — birinchi kirish

- URL: `/adminpanel/`  •  Login: `admin`  •  Parol: `admin123` (seed yaratadi — **prod'da darhol o'zgartiring!**)
- Django superadmin: `/django-admin/`

## ⚡ Optimallashtirish (talab bo'limi)

- Kesh: menyu 120s, statistika 60s (Redis; yo'q bo'lsa LocMem)
- Indekslar: buyurtma filtrlari/stol tarixi/menyu uchun qamrovli indekslar
- `select_related`/`prefetch_related` — N+1 so'rovlar yo'q
- API orqali ma'lumot almashinuvi — klient hech qachon DB'ga tegmaydi
- WebSocket real-time sinxronizatsiya (Redis channel layer)
- Whitenoise gzip statik fayllar

## 🔒 Xavfsizlik qisqacha

Telegram initData HMAC tekshiruvi (replay himoyasi bilan), JWT qisqa umr,
narx faqat serverda hisoblanadi, QR token UUID, role-based permissions,
throttle, XSS escape, password validatorlar. To'liq: [docs/05_xavfsizlik.md](docs/05_xavfsizlik.md)
