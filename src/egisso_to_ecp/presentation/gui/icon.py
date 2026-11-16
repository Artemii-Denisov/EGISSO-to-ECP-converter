"""Vector-rendered high-DPI application icon and Windows .ico generator."""

from __future__ import annotations

import struct
from pathlib import Path

from PySide6.QtCore import QBuffer, QIODevice, QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QIcon,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)

ICON_SIZES: tuple[int, ...] = (16, 24, 32, 48, 64, 128, 256)
ICO_SIZES: tuple[int, ...] = (16, 24, 32, 48, 64, 256)


def _render_icon_image(size: int) -> QImage:
    """Renders an Antigravity/Codex-inspired migration badge icon onto a QImage."""
    img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)

    painter = QPainter(img)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

    s = float(size)
    margin = max(1.0, s * 0.06)
    bg_rect = QRectF(margin, margin, s - 2 * margin, s - 2 * margin)
    radius = s * 0.22

    # Background rounded squircle with deep navy-blue gradient
    grad = QLinearGradient(bg_rect.topLeft(), bg_rect.bottomRight())
    grad.setColorAt(0.0, QColor("#0F172A"))
    grad.setColorAt(0.55, QColor("#172554"))
    grad.setColorAt(1.0, QColor("#1D4ED8"))

    bg_path = QPainterPath()
    bg_path.addRoundedRect(bg_rect, radius, radius)
    painter.fillPath(bg_path, grad)

    # Subtle bright top-left highlight border
    border_width = max(1.0, s * 0.032)
    border_pen = QPen(QColor("#60A5FA"), border_width)
    painter.setPen(border_pen)
    painter.drawPath(bg_path)

    # Inner document/registry sheet glyph (left-center)
    doc_x = s * 0.22
    doc_y = s * 0.22
    doc_w = s * 0.42
    doc_h = s * 0.56
    doc_rect = QRectF(doc_x, doc_y, doc_w, doc_h)

    doc_path = QPainterPath()
    doc_path.addRoundedRect(doc_rect, s * 0.06, s * 0.06)
    painter.fillPath(doc_path, QColor(248, 250, 252, 235))

    # Crisp horizontal table rows inside the sheet (skipped below 20px to stay sharp)
    if size >= 20:
        line_pen = QPen(
            QColor("#2563EB"),
            max(1.2, s * 0.045),
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
        )
        painter.setPen(line_pen)
        for row_idx, frac in enumerate((0.35, 0.50, 0.65)):
            ly = s * frac
            right_end = doc_x + doc_w * (0.76 if row_idx != 1 else 0.58)
            painter.drawLine(QPointF(doc_x + doc_w * 0.20, ly), QPointF(right_end, ly))

    # Electric-cyan circular badge + right arrow (bottom-right overlay)
    badge_d = s * 0.42
    badge_x = s * 0.48
    badge_y = s * 0.46
    badge_rect = QRectF(badge_x, badge_y, badge_d, badge_d)

    badge_grad = QLinearGradient(badge_rect.topLeft(), badge_rect.bottomRight())
    badge_grad.setColorAt(0.0, QColor("#38BDF8"))
    badge_grad.setColorAt(1.0, QColor("#2563EB"))

    painter.setPen(QPen(QColor("#0F172A"), max(1.0, s * 0.035)))
    painter.setBrush(badge_grad)
    painter.drawEllipse(badge_rect)

    # Crisp migration arrow inside badge
    cx = badge_x + badge_d * 0.50
    cy = badge_y + badge_d * 0.50
    half_len = badge_d * 0.24
    head_len = badge_d * 0.16

    arrow_pen = QPen(
        QColor("#FFFFFF"),
        max(1.4, s * 0.055),
        Qt.PenStyle.SolidLine,
        Qt.PenCapStyle.RoundCap,
        Qt.PenJoinStyle.RoundJoin,
    )
    painter.setPen(arrow_pen)
    painter.drawLine(QPointF(cx - half_len, cy), QPointF(cx + half_len, cy))
    painter.drawLine(QPointF(cx + half_len - head_len, cy - head_len), QPointF(cx + half_len, cy))
    painter.drawLine(QPointF(cx + half_len - head_len, cy + head_len), QPointF(cx + half_len, cy))

    painter.end()
    return img


def create_app_icon() -> QIcon:
    """Builds a crisp multi-resolution QIcon for window titlebars and taskbars."""
    icon = QIcon()
    for size in ICON_SIZES:
        icon.addPixmap(QPixmap.fromImage(_render_icon_image(size)))
    return icon


def _encode_ico_dib(img: QImage) -> bytes:
    """Encodes a square QImage as a 32-bit BGRA Win32 DIB (BITMAPINFOHEADER + bottom-up XOR + AND)."""
    size = img.width()
    bgra = img.convertToFormat(QImage.Format.Format_ARGB32)

    # BI_RGB (0), height = size * 2 (covers both XOR + AND masks)
    and_row_bytes = ((size + 31) // 32) * 4
    xor_bytes_size = size * size * 4
    bih = struct.pack(
        "<IIIHHIIIIII",
        40,
        size,
        size * 2,
        1,
        32,
        0,
        xor_bytes_size + and_row_bytes * size,
        0,
        0,
        0,
        0,
    )

    xor_chunks = bytearray()
    for y in range(size - 1, -1, -1):
        for x in range(size):
            # Little-endian 0xAARRGGBB -> [B, G, R, A]
            xor_chunks.extend(struct.pack("<I", bgra.pixel(x, y)))

    and_mask = b"\x00" * (and_row_bytes * size)
    return bih + bytes(xor_chunks) + and_mask


def write_ico_file(target_path: Path) -> Path:
    """Writes a multi-size Windows .ico (Win32 DIB for <=64px, PNG for 256px) to `target_path`."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    frames: list[tuple[int, bytes]] = []
    for size in ICO_SIZES:
        img = _render_icon_image(size)
        if size < 256:
            frames.append((size, _encode_ico_dib(img)))
        else:
            buf = QBuffer()
            buf.open(QIODevice.OpenModeFlag.WriteOnly)
            if not img.save(buf, "PNG"):  # type: ignore[call-overload]  # PySide6 stubs declare bytes, runtime expects str
                raise RuntimeError(f"Не удалось закодировать кадр иконки {size}x{size} в PNG")
            frames.append((size, bytes(buf.data().data())))

    count = len(frames)
    header = struct.pack("<HHH", 0, 1, count)
    offset = 6 + 16 * count
    directory_entries: list[bytes] = []
    payloads: list[bytes] = []

    for size, frame_bytes in frames:
        dim = 0 if size >= 256 else size
        entry = struct.pack(
            "<BBBBHHII",
            dim,
            dim,
            0,
            0,
            1,
            32,
            len(frame_bytes),
            offset,
        )
        directory_entries.append(entry)
        payloads.append(frame_bytes)
        offset += len(frame_bytes)

    target_path.write_bytes(header + b"".join(directory_entries) + b"".join(payloads))
    return target_path
