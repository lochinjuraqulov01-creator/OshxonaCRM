"""apps/users/services.py — Telegram WebApp initData tekshiruvi.

Telegram rasmiy algoritmi (xavfsizlik):
  1) data_check_string = initData maydonlari (hash dan tashqari), alifbo bo'yicha,
     "key=value" ko'rinishida & bilan bog'langan.
  2) secret_key = HMAC_SHA256(key=b"WebAppData", msg=BOT_TOKEN)
  3) hisoblangan hash = HMAC_SHA256(key=secret_key, msg=data_check_string) hex
  4) hash mos kelishi + vaqt belgisi yangi bo'lishi kerak (replay hujumiga qarshi).
"""
import datetime as dt
import hashlib
import hmac
import json
import logging
from datetime import timedelta
from urllib.parse import unquote_plus

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger('apps')

# initData qancha vaqt amal qiladi (replay hujumidan himoya)
INIT_DATA_TTL = timedelta(hours=24)


class TelegramInitDataError(Exception):
    """initData noto'g'ri yoki muddati o'tgan."""


def validate_init_data(init_data: str) -> dict:
    """
    Mini App yuborgan initData ni tekshiradi.
    Muvaffaqiyatli bo'lsa — parsed data (user, auth_date, ...) qaytaradi.
    Aks holda TelegramInitDataError oshiradi.
    """
    if not init_data:
        raise TelegramInitDataError('initData bo‘sh.')

    try:
        pairs = [p.split('=', 1) for p in init_data.split('&') if '=' in p]
        received_hash = ''
        data_check_pairs = []
        for key, value in pairs:
            if key == 'hash':
                received_hash = value
            else:
                data_check_pairs.append((key, value))
    except Exception as e:
        raise TelegramInitDataError(f'initData formati noto‘g‘ri: {e}')

    bot_token = settings.TELEGRAM_BOT_TOKEN

    # Lokal demo rejimi: token yo'q va DEBUG — imzo tekshiruvi o'tkazilmaydi
    if not bot_token and settings.DEBUG and not received_hash:
        logger.warning('TELEGRAM_BOT_TOKEN sozlanmagan — initData tekshiruvi o‘tkazildi (DEBUG).')
        return _parse_user_from(data_check_pairs)

    if not received_hash:
        raise TelegramInitDataError('hash maydoni yo‘q.')

    data_check_string = '\n'.join(
        f'{k}={unquote_plus(v)}' for k, v in sorted(data_check_pairs)
    )

    if not bot_token:
        raise TelegramInitDataError('Server sozlamalari tugallanmagan.')

    secret_key = hmac.new(b'WebAppData', bot_token.encode(), hashlib.sha256).digest()
    calculated = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(calculated, received_hash):
        logger.warning('initData hash mos kelmadi! Server tokeni oxiri: ...%s | qabul: %s | hisoblangan: %s',
                       bot_token[-6:] if bot_token else '?', received_hash, calculated)
        raise TelegramInitDataError('Imzo tekshiruvidan o‘tmadi.')

    # auth_date ni tekshirish (replay hujumidan himoya)
    auth_date = dict(data_check_pairs).get('auth_date')
    if auth_date:
        try:
            auth_dt = dt.datetime.fromtimestamp(int(auth_date), tz=dt.timezone.utc)
        except (ValueError, OverflowError, OSError):
            raise TelegramInitDataError('auth_date noto‘g‘ri.')
        if timezone.now() - auth_dt > INIT_DATA_TTL:
            raise TelegramInitDataError('initData muddati o‘tgan. Sahifani yangilang.')

    return _parse_user_from(data_check_pairs)


def _parse_user_from(pairs) -> dict:
    data = dict(pairs)
    user_raw = data.get('user')
    if not user_raw:
        raise TelegramInitDataError('initData tarkibida user yo‘q.')
    # Telegram initData ichidagi qiymatlar URL-encoded bo'ladi (+ va %xx)
    from urllib.parse import unquote_plus
    try:
        user = json.loads(unquote_plus(user_raw))
    except json.JSONDecodeError:
        raise TelegramInitDataError('user maydoni noto‘g‘ri JSON.')
    return data | {'_user': user}
