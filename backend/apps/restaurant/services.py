"""apps/restaurant/services.py — QR kod generatsiyasi (PNG)."""
import io

import qrcode
from qrcode.constants import ERROR_CORRECT_M


def make_qr_png(content: str, size: int = 512, with_label: str | None = None) -> io.BytesIO:
    """
    QR kod PNG obyektini yaratadi.
    with_label berilsa — QR ostida stol raqami yozilgan rasm qaytaradi
    (ofitsiant stolga qo'yadigan plakat sifatida chop etishga tayyor).
    """
    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_M,
        box_size=12,
        border=4,
    )
    qr.add_data(content)
    qr.make(fit=True)

    try:
        # Rangli (gradient) uslub — qrcode[pil] o'rnatilgan bo'lsa
        from qrcode.image.styledpil import StyledPilImage
        from qrcode.image.styles.colormasks import RadialGradiantColorMask
        img = qr.make_image(image_factory=StyledPilImage,
                            color_mask=RadialGradiantColorMask()).convert('RGB')
    except Exception:
        img = qr.make_image(fill_color='black', back_color='white').convert('RGB')

    img = img.resize((size, size))

    if with_label:
        from PIL import Image, ImageDraw, ImageFont
        label_h = 90
        canvas = Image.new('RGB', (size, size + label_h), 'white')
        canvas.paste(img, (0, 0))
        draw = ImageDraw.Draw(canvas)
        text = with_label
        # Standart shrift bilan markazga yozish
        try:
            font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 44)
        except Exception:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        draw.text(((size - w) // 2, size + 18), text, fill='black', font=font)
        buf = io.BytesIO()
        canvas.save(buf, format='PNG')
        buf.seek(0)
        return buf

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf
