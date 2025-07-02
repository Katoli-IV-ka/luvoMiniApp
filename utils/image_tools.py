# app/core/image_utils.py

from PIL import Image, ExifTags, UnidentifiedImageError
from io import BytesIO


def compress_image_bytes(
    data: bytes,
    quality: int = 70
) -> tuple[bytes, str]:
    """
    Сжимает изображение в памяти под соцсети:
    - Открывает любой поддерживаемый Pillow формат.
    - Корректирует ориентацию по EXIF (удаляет EXIF после поворота).
    - Конвертирует в RGB, чтобы убрать альфа-канал.
    - Сохраняет в WebP, если исходный формат WebP, иначе в JPEG.
    - Качество по умолчанию снижено до 70 для агрессивного сжатия.

    Возвращает (compressed_bytes, ext), где ext — "webp" или "jpg".
    Бросает ValueError, если файл не распознан как изображение.
    """
    try:
        img = Image.open(BytesIO(data))
    except UnidentifiedImageError:
        raise ValueError("Неподдерживаемый файл — это не изображение")

    # Пытаться получить EXIF и корректировать ориентацию
    try:
        exif = img._getexif()
        if exif is not None:
            # ищем тег ориентации
            orientation_key = next(
                key for key, val in ExifTags.TAGS.items() if val == 'Orientation'
            )
            orientation = exif.get(orientation_key)
            if orientation == 3:
                img = img.rotate(180, expand=True)
            elif orientation == 6:
                img = img.rotate(270, expand=True)
            elif orientation == 8:
                img = img.rotate(90, expand=True)
    except Exception:
        # если EXIF не читается или нет ориентации — пропускаем
        pass

    # Очищаем EXIF, чтобы не передавать метаданные дальше
    if hasattr(img, 'info') and 'exif' in img.info:
        img.info.pop('exif')

    # Сохраняем исходный формат до возможной конвертации
    orig_fmt = (img.format or 'JPEG').upper()

    # Конвертируем в RGB, чтобы убрать альфа-канал
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')

    buf = BytesIO()

    # Если исходник был WebP, сохраняем в WebP
    if orig_fmt == 'WEBP':
        img.save(
            buf,
            'WEBP',
            quality=quality,
            optimize=True
        )
        ext = 'webp'
    else:
        # Сохраняем в JPEG для всех остальных форматов
        img.save(
            buf,
            'JPEG',
            quality=quality,
            optimize=True,
            progressive=True
        )
        ext = 'jpg'

    return buf.getvalue(), ext
