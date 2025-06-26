from PIL import Image, UnidentifiedImageError
from io import BytesIO


def compress_image_bytes(
    data: bytes,
    quality: int = 70
) -> tuple[bytes, str]:
    """
    Сжимает изображение в памяти под соцсети:
    - Открывает любой поддерживаемый Pillow формат.
    - Конвертирует в RGB, если есть альфа-канал.
    - Сохраняет в WebP, если исходный формат WebP, иначе в JPEG.
    - Качество по умолчанию снижено до 70 для агрессивного сжатия.

    Возвращает (compressed_bytes, ext), где ext — "webp" или "jpg".
    Бросает ValueError, если файл не распознан как изображение.
    """
    try:
        img = Image.open(BytesIO(data))
    except UnidentifiedImageError:
        raise ValueError("Неподдерживаемый файл — это не изображение")

    # Сохраняем исходный формат до возможной конвертации
    orig_fmt = (img.format or "JPEG").upper()

    # Конвертируем в RGB, чтобы убрать альфа-канал
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    buf = BytesIO()

    # Если исходник был WebP, сохраняем в WebP
    if orig_fmt == "WEBP":
        img.save(
            buf,
            "WEBP",
            quality=quality,
            optimize=True
        )
        ext = "webp"
    else:
        # Сохраняем в JPEG для всех остальных форматов
        img.save(
            buf,
            "JPEG",
            quality=quality,
            optimize=True,
            progressive=True
        )
        ext = "jpg"

    return buf.getvalue(), ext
