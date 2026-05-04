#!/usr/bin/env python3
"""
PDF Signature Stamper v2
Workflow: Otevřít PDF → Vybrat certifikát → Umístit razítka → Podepsat
"""

import sys
import os
import io
import traceback
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Dict

import fitz  # PyMuPDF

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QFileDialog, QDialog,
    QDialogButtonBox, QMessageBox, QScrollArea, QSplitter,
    QStatusBar, QSizePolicy, QToolBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPoint, QRect, QSettings
from PyQt6.QtGui import (
    QPixmap, QImage, QPainter, QPen, QBrush, QColor, QFont,
    QKeyEvent, QMouseEvent, QPaintEvent, QResizeEvent
)

from cryptography.hazmat.primitives.serialization.pkcs12 import load_key_and_certificates
from cryptography.x509.oid import NameOID

import cairosvg
from PIL import Image
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib import colors as rl_colors
from reportlab.lib.utils import ImageReader

from pyhanko.sign import fields
from pyhanko.sign.fields import SigFieldSpec
from pyhanko.sign.signers import PdfSigner, PdfSignatureMetadata, SimpleSigner
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.stamp.static import StaticStampStyle

# ── Konstanty ──────────────────────────────────────────────────────────────────
STAMP_W_MM = 71.0
STAMP_H_MM = 21.0
MM_TO_PT   = 72.0 / 25.4
STAMP_W_PT = STAMP_W_MM * MM_TO_PT
STAMP_H_PT = STAMP_H_MM * MM_TO_PT
THUMB_W    = 120

# ── PDF ikona (embeddovaná) ────────────────────────────────────────────────────
PDF_SVG = b"""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg width="800px" height="800px" viewBox="-4 0 40 40" fill="none"
   version="1.1" xmlns="http://www.w3.org/2000/svg">
  <path d="m 25.6686,26.0962 c -0.4874,0.1439 -1.203,0.1601 -1.9702,0.0488
   -0.8234,-0.1194 -1.6633,-0.3711 -2.4888,-0.742 1.4721,-0.2142 2.6141,-0.1482
   3.5909,0.1979 0.2314,0.082 0.6115,0.3012 0.8681,0.4953 z
   m -8.2134,-1.3503 c -0.0599,0.0163 -0.1189,0.0317 -0.1776,0.048
   -0.3961,0.1078 -0.7815,0.213 -1.1529,0.3066 l -0.5008,0.127
   c -1.0074,0.2549 -2.0374,0.5153 -3.0547,0.8254 0.3866,-0.9323
   0.7458,-1.8749 1.0975,-2.7965 0.2604,-0.6822 0.5263,-1.3791
   0.8013,-2.067 0.1395,0.2304 0.2851,0.4609 0.4366,0.692
   0.6902,1.0512 1.5578,2.0231 2.5506,2.8645 z
   M 14.8927,14.2326 c 0.0653,1.1504 -0.1829,2.2571 -0.547,3.3188
   -0.4485,-1.3128 -0.6575,-2.7625 -0.0968,-3.9329 0.1438,-0.3
   0.2616,-0.4604 0.338,-0.5441 0.118,0.1822 0.2732,0.5898
   0.3058,1.1582 z
   M 9.63347,28.8054 c -0.25199,0.4508 -0.50921,0.8728 -0.77284,1.2713
   -0.63621,0.9588 -1.6767,1.9854 -2.21122,1.9854 -0.0526,0
   -0.11625,-0.0085 -0.20926,-0.1067 C 6.38028,31.8926 6.37069,31.8476
   6.37359,31.7862 6.39161,31.4337 6.85867,30.8059 7.53527,30.2238
   8.14939,29.6957 8.84352,29.2262 9.63347,28.8054 Z
   M 27.3706,26.1461 c -0.0817,-1.1742 -2.0583,-1.9275 -2.0778,-1.9345
   -0.7641,-0.2709 -1.5942,-0.4025 -2.5376,-0.4025 -1.0099,0
   -2.0987,0.1461 -3.497,0.4728 -1.2442,-0.882 -2.319,-1.9862
   -3.122,-3.2086 -0.3546,-0.5401 -0.6734,-1.0792 -0.9513,-1.6058
   0.6784,-1.6221 1.2893,-3.3662 1.1783,-5.3196 -0.0895,-1.5663
   -0.7958,-2.6184 -1.7563,-2.6184 -0.6589,0 -1.2262,0.488
   -1.6875,1.4518 -0.8229,1.7174 -0.6066,3.9149 0.6426,6.5371
   -0.4499,1.0567 -0.8679,2.1522 -1.2725,3.2127 -0.5034,1.3187
   -1.0221,2.6792 -1.6067,3.9734 -1.63946,0.6487 -2.98632,1.4354
   -4.10878,2.4012 -0.73532,0.6316 -1.62179,1.5971 -1.67239,2.605
   -0.0247,0.4747 0.13806,0.91 0.46881,1.2588 0.35139,0.3703
   0.79285,0.5653 1.27826,0.5659 1.60319,0 3.14619,-2.2027
   3.4389,-2.6445 0.5891,-0.888 1.1405,-1.8785 1.6808,-3.021
   1.3608,-0.4918 2.811,-0.8589 4.2166,-1.2137 l 0.5034,-0.1279
   c 0.3784,-0.0962 0.7717,-0.2026 1.1751,-0.313 0.4269,-0.1154
   0.8661,-0.2351 1.3125,-0.3488 1.4433,0.9179 2.9954,1.5166
   4.5091,1.7363 1.275,0.1855 2.4073,0.0779 3.1738,-0.3217
   0.6897,-0.3592 0.7277,-0.9135 0.7117,-1.135 z"
   fill="#eb5757"/>
</svg>"""


# ── Datová třída pro razítko ───────────────────────────────────────────────────
@dataclass
class StampMarker:
    page:     int
    x_pt:     float
    y_pt:     float
    selected: bool = False


# ── Generování vizuálního razítka ─────────────────────────────────────────────
def extract_name_from_p12(p12_path: str, password: bytes) -> str:
    with open(p12_path, 'rb') as f:
        data = f.read()
    _, cert, _ = load_key_and_certificates(data, password)
    try:
        return cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
    except Exception:
        return "Neznámý podepisující"


def generate_stamp_pdf(name: str, sign_time: datetime) -> str:
    """Vygeneruje razítko jako dočasný PDF. Vrátí cestu (volající maže)."""
    png_data = cairosvg.svg2png(bytestring=PDF_SVG, output_width=60, output_height=60)
    img = Image.open(io.BytesIO(png_data)).convert('RGBA')
    img_reader = ImageReader(img)

    tz_offset = sign_time.strftime('%z')
    tz_str   = f"{tz_offset[:3]}'{tz_offset[3:]}'" if len(tz_offset) == 5 else "+00'00'"
    date_str = sign_time.strftime('%Y.%m.%d')
    time_str = sign_time.strftime('%H:%M:%S')

    parts = name.split(maxsplit=1)
    first = parts[0] if parts else name
    last  = parts[1] if len(parts) > 1 else ''

    W, H = 200, 58
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=(W, H))

    # Bílé pozadí
    c.setFillColor(rl_colors.white)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    # SVG logo jako pozadí (vycentrované, poloprůhledné)
    c.saveState()
    c.setFillAlpha(0.08)
    c.drawImage(img_reader, W // 2 - 30, H // 2 - 30, width=60, height=60, mask='auto')
    c.restoreState()

    # Tenký rámeček
    c.setStrokeColor(rl_colors.HexColor('#b0b0b0'))
    c.setLineWidth(0.5)
    c.rect(0.5, 0.5, W - 1, H - 1, fill=0, stroke=1)

    # Svislá dělicí čára
    c.setStrokeColor(rl_colors.HexColor('#d0d0d0'))
    c.setLineWidth(0.3)
    c.line(75, 6, 75, H - 6)

    # Levý blok: jméno
    c.setFillColor(rl_colors.black)
    if last:
        c.setFont('Helvetica', 17)
        c.drawString(5, H - 23, first)
        c.drawString(5, H - 43, last)
    else:
        c.setFont('Helvetica', 14)
        c.drawString(5, H / 2 - 7, first)

    # Pravý blok
    x = 80
    c.setFont('Helvetica-Bold', 6.5)
    c.setFillColor(rl_colors.black)
    c.drawString(x, H - 13, 'Digitally signed by')
    c.setFont('Helvetica', 6.5)
    c.drawString(x, H - 22, name)
    c.drawString(x, H - 31, f'Date: {date_str}')
    c.drawString(x, H - 40, f'{time_str} {tz_str}')

    c.save()

    tmp = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
    tmp.write(buf.getvalue())
    tmp.close()
    return tmp.name


# ── Náhled stránky s umisťováním razítek ──────────────────────────────────────
class PageView(QWidget):
    stamps_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._doc: Optional[fitz.Document] = None
        self._current_page = 0
        self._page_pixmap: Optional[QPixmap] = None
        self._scale  = 1.0
        self._offset = QPoint(0, 0)

        self._stamps: List[StampMarker] = []
        self._ghost_pos: Optional[QPoint] = None
        self._ghost_pixmap: Optional[QPixmap] = None

        self._dragging: Optional[StampMarker] = None
        self._drag_offset = QPoint(0, 0)

    def load_document(self, doc: fitz.Document):
        self._doc = doc
        self._stamps = []
        self._current_page = 0
        self._render_page()
        self.update()
        self.stamps_changed.emit()

    def set_page(self, page_idx: int):
        if self._doc and 0 <= page_idx < len(self._doc):
            self._current_page = page_idx
            self._render_page()
            self.update()

    def _render_page(self):
        if not self._doc:
            return
        page = self._doc[self._current_page]
        w = max(self.width(),  400)
        h = max(self.height(), 400)
        r = page.rect
        self._scale = min(w / r.width, h / r.height) * 0.95
        mat = fitz.Matrix(self._scale, self._scale)
        pix = page.get_pixmap(matrix=mat)
        img = QImage(pix.samples, pix.width, pix.height,
                     pix.stride, QImage.Format.Format_RGB888)
        self._page_pixmap = QPixmap.fromImage(img)
        self._offset = QPoint(
            (self.width()  - self._page_pixmap.width())  // 2,
            (self.height() - self._page_pixmap.height()) // 2,
        )
        self._rebuild_ghost()

    def _rebuild_ghost(self):
        w = max(int(STAMP_W_PT * self._scale), 10)
        h = max(int(STAMP_H_PT * self._scale), 4)
        pm = QPixmap(w, h)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(0, 0, w, h, QColor(180, 200, 255, 90))
        pen = QPen(QColor(40, 80, 200, 200))
        pen.setWidth(2)
        p.setPen(pen)
        p.drawRect(1, 1, w - 2, h - 2)
        x1 = w * 75 // 200
        pen2 = QPen(QColor(100, 130, 220, 120))
        pen2.setStyle(Qt.PenStyle.DashLine)
        pen2.setWidth(1)
        p.setPen(pen2)
        p.drawLine(x1, 3, x1, h - 3)
        p.setPen(QColor(40, 80, 200, 180))
        font = QFont()
        font.setPointSizeF(max(5.0, 6.0 * self._scale))
        p.setFont(font)
        p.drawText(QRect(x1 + 3, 2, w - x1 - 5, h - 4),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                   "Digitally signed by\n…")
        p.end()
        self._ghost_pixmap = pm

    def _screen_to_pdf(self, pos: QPoint):
        return ((pos.x() - self._offset.x()) / self._scale,
                (pos.y() - self._offset.y()) / self._scale)

    def _stamp_screen_rect(self, stamp: StampMarker) -> QRect:
        return QRect(
            int(stamp.x_pt * self._scale) + self._offset.x(),
            int(stamp.y_pt * self._scale) + self._offset.y(),
            int(STAMP_W_PT * self._scale),
            int(STAMP_H_PT * self._scale),
        )

    def _page_rect(self) -> Optional[QRect]:
        if not self._page_pixmap:
            return None
        return QRect(self._offset, self._page_pixmap.size())

    def _stamp_at(self, pos: QPoint) -> Optional[StampMarker]:
        for stamp in reversed(self._stamps):
            if stamp.page == self._current_page:
                if self._stamp_screen_rect(stamp).contains(pos):
                    return stamp
        return None

    def _clamp_stamp(self, stamp: StampMarker):
        if not self._doc:
            return
        r = self._doc[stamp.page].rect
        stamp.x_pt = max(0.0, min(stamp.x_pt, r.width  - STAMP_W_PT))
        stamp.y_pt = max(0.0, min(stamp.y_pt, r.height - STAMP_H_PT))

    def get_stamps(self) -> List[StampMarker]:
        return list(self._stamps)

    def stamp_count(self) -> int:
        return len(self._stamps)

    def paintEvent(self, event: QPaintEvent):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor(72, 72, 72))

        if self._page_pixmap:
            p.drawPixmap(self._offset, self._page_pixmap)

        for stamp in self._stamps:
            if stamp.page != self._current_page:
                continue
            rect = self._stamp_screen_rect(stamp)
            fill = QColor(180, 210, 255, 130) if stamp.selected else QColor(210, 225, 255, 80)
            p.fillRect(rect, fill)
            pen = QPen(QColor(20, 60, 180) if stamp.selected else QColor(80, 120, 200))
            pen.setWidth(2 if stamp.selected else 1)
            p.setPen(pen)
            p.drawRect(rect)
            if stamp.selected:
                for cx, cy in [(rect.x(), rect.y()), (rect.right(), rect.y()),
                               (rect.x(), rect.bottom()), (rect.right(), rect.bottom())]:
                    p.fillRect(cx - 4, cy - 4, 8, 8, QColor(20, 60, 180))

        pr = self._page_rect()
        if (self._ghost_pos and self._ghost_pixmap and pr
                and pr.contains(self._ghost_pos) and not self._dragging):
            gx = self._ghost_pos.x() - self._ghost_pixmap.width()  // 2
            gy = self._ghost_pos.y() - self._ghost_pixmap.height() // 2
            p.drawPixmap(gx, gy, self._ghost_pixmap)
        p.end()

    def mouseMoveEvent(self, event: QMouseEvent):
        pos = event.position().toPoint()
        if self._dragging:
            x_pt = (pos.x() - self._drag_offset.x() - self._offset.x()) / self._scale
            y_pt = (pos.y() - self._drag_offset.y() - self._offset.y()) / self._scale
            self._dragging.x_pt = x_pt
            self._dragging.y_pt = y_pt
            self._clamp_stamp(self._dragging)
            self.update()
            self.stamps_changed.emit()
            return
        self._ghost_pos = pos
        over_stamp = self._stamp_at(pos)
        pr = self._page_rect()
        if over_stamp:
            self.setCursor(Qt.CursorShape.SizeAllCursor)
        elif pr and pr.contains(pos):
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()

    def mousePressEvent(self, event: QMouseEvent):
        self.setFocus()
        pos = event.position().toPoint()

        if event.button() == Qt.MouseButton.RightButton:
            stamp = self._stamp_at(pos)
            if stamp:
                self._stamps.remove(stamp)
                self.stamps_changed.emit()
                self.update()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            stamp = self._stamp_at(pos)
            if stamp:
                for s in self._stamps:
                    s.selected = False
                stamp.selected = True
                r = self._stamp_screen_rect(stamp)
                self._dragging = stamp
                self._drag_offset = QPoint(pos.x() - r.x(), pos.y() - r.y())
            else:
                for s in self._stamps:
                    s.selected = False
                pr = self._page_rect()
                if pr and pr.contains(pos) and self._doc:
                    x_pt, y_pt = self._screen_to_pdf(pos)
                    new_stamp = StampMarker(
                        self._current_page,
                        x_pt - STAMP_W_PT / 2,
                        y_pt - STAMP_H_PT / 2,
                        selected=True,
                    )
                    self._clamp_stamp(new_stamp)
                    self._stamps.append(new_stamp)
                    self.stamps_changed.emit()
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._dragging = None

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            before = len(self._stamps)
            self._stamps = [s for s in self._stamps if not s.selected]
            if len(self._stamps) < before:
                self.stamps_changed.emit()
                self.update()

    def leaveEvent(self, event):
        self._ghost_pos = None
        self.update()

    def resizeEvent(self, event: QResizeEvent):
        self._render_page()
        self.update()


# ── Panel miniatur ─────────────────────────────────────────────────────────────
class ThumbnailPanel(QScrollArea):
    page_selected = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(THUMB_W + 28)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        self._layout = QVBoxLayout(container)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._layout.setSpacing(6)
        self._layout.setContentsMargins(4, 6, 4, 6)
        self.setWidget(container)

        self._labels: List[QLabel] = []
        self._current = -1

    def load_document(self, doc: fitz.Document):
        for lbl in self._labels:
            self._layout.removeWidget(lbl)
            lbl.deleteLater()
        self._labels = []
        self._current = -1

        for i in range(len(doc)):
            page = doc[i]
            scale = THUMB_W / page.rect.width
            pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale))
            img = QImage(pix.samples, pix.width, pix.height,
                         pix.stride, QImage.Format.Format_RGB888)
            pm = QPixmap.fromImage(img)

            wrapper = QWidget()
            vl = QVBoxLayout(wrapper)
            vl.setContentsMargins(2, 2, 2, 2)
            vl.setSpacing(2)

            lbl_img = QLabel()
            lbl_img.setPixmap(pm)
            lbl_img.setFixedSize(pm.size())
            lbl_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_img.setCursor(Qt.CursorShape.PointingHandCursor)

            lbl_num = QLabel(str(i + 1))
            lbl_num.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_num.setStyleSheet("font-size: 10px; color: #555;")

            vl.addWidget(lbl_img)
            vl.addWidget(lbl_num)

            wrapper.setStyleSheet("border: 2px solid transparent; border-radius: 2px;")
            wrapper.setCursor(Qt.CursorShape.PointingHandCursor)

            idx = i
            wrapper.mousePressEvent = lambda e, n=idx: self._on_click(n)
            lbl_img.mousePressEvent = lambda e, n=idx: self._on_click(n)

            self._layout.addWidget(wrapper)
            self._labels.append(wrapper)

        if self._labels:
            self.highlight(0)

    def highlight(self, page_idx: int):
        if 0 <= self._current < len(self._labels):
            self._labels[self._current].setStyleSheet(
                "border: 2px solid transparent; border-radius: 2px;")
        self._current = page_idx
        if 0 <= page_idx < len(self._labels):
            self._labels[page_idx].setStyleSheet(
                "border: 2px solid #3a6fd8; border-radius: 2px;")
            self.ensureWidgetVisible(self._labels[page_idx])

    def _on_click(self, idx: int):
        self.highlight(idx)
        self.page_selected.emit(idx)


# ── Dialog na heslo ────────────────────────────────────────────────────────────
class PasswordDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Heslo k certifikátu")
        self.setMinimumWidth(320)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Zadejte heslo k p12 certifikátu:"))
        self.pw_edit = QLineEdit()
        self.pw_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.pw_edit.setPlaceholderText("Heslo…")
        layout.addWidget(self.pw_edit)
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)
        self.pw_edit.returnPressed.connect(self.accept)

    def password(self) -> bytes:
        return self.pw_edit.text().encode('utf-8')


# ── Podpisový worker ───────────────────────────────────────────────────────────
class SignerThread(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, input_path: str, output_path: str, p12_path: str,
                 password: bytes, stamps: List[StampMarker],
                 page_heights: Dict[int, float]):
        super().__init__()
        self.input_path   = input_path
        self.output_path  = output_path
        self.p12_path     = p12_path
        self.password     = password
        self.stamps       = stamps
        self.page_heights = page_heights

    def run(self):
        stamp_pdf = None
        tmp_files = []
        try:
            self.progress.emit("Načítám certifikát…")
            name = extract_name_from_p12(self.p12_path, self.password)
            self.progress.emit(f"Podepisuji jako: {name}")

            self.progress.emit("Generuji razítko…")
            sign_time = datetime.now(timezone.utc).astimezone()
            stamp_pdf = generate_stamp_pdf(name, sign_time)

            # ── Krok 1: přidat všechna podpisová pole najednou ────────────────
            self.progress.emit("Přidávám podpisová pole…")
            tmp1 = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
            tmp1.close()
            tmp_files.append(tmp1.name)

            with open(self.input_path, 'rb') as f:
                in_data = f.read()

            writer = IncrementalPdfFileWriter(io.BytesIO(in_data))
            for i, stamp in enumerate(self.stamps):
                ph = self.page_heights.get(stamp.page, 842.0)
                y_bottom = ph - stamp.y_pt - STAMP_H_PT
                box = (stamp.x_pt, y_bottom,
                       stamp.x_pt + STAMP_W_PT, y_bottom + STAMP_H_PT)
                fields.append_signature_field(
                    writer,
                    SigFieldSpec(f'Sig{i + 1}', on_page=stamp.page, box=box)
                )
            with open(tmp1.name, 'wb') as out:
                writer.write(out)
                out.flush()
                os.fsync(out.fileno())

            # ── Krok 2: postupně podepisovat každé pole ───────────────────────
            style  = StaticStampStyle.from_pdf_file(stamp_pdf, border_width=0)
            signer = SimpleSigner.load_pkcs12(
                pfx_file=self.p12_path,
                passphrase=self.password,
            )

            current = tmp1.name
            for i, stamp in enumerate(self.stamps):
                self.progress.emit(f"Podepisuji razítko {i + 1}/{len(self.stamps)}…")

                if i < len(self.stamps) - 1:
                    tmp_next = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
                    tmp_next.close()
                    next_path = tmp_next.name
                    tmp_files.append(next_path)
                else:
                    next_path = self.output_path

                # Číst celý soubor do paměti
                with open(current, 'rb') as f:
                    current_data = f.read()
                print(f"[debug] Sig{i+1}: reading {len(current_data)} bytes from {current}")

                in_buf = io.BytesIO(current_data)
                w = IncrementalPdfFileWriter(in_buf)
                meta = PdfSignatureMetadata(field_name=f'Sig{i + 1}')
                pdf_signer = PdfSigner(meta, signer=signer, stamp_style=style)

                # Zapsat přímo do souboru
                with open(next_path, 'w+b') as out_file:
                    pdf_signer.sign_pdf(w, output=out_file)
                    out_file.flush()
                    os.fsync(out_file.fileno())

                size = os.path.getsize(next_path)
                print(f"[debug] Sig{i+1}: wrote {size} bytes to {next_path}")
                current = next_path

            self.finished.emit(True, f"Podepsáno → {self.output_path}")

        except Exception as e:
            traceback.print_exc()
            self.finished.emit(False, str(e))
        finally:
            if stamp_pdf and os.path.exists(stamp_pdf):
                os.unlink(stamp_pdf)
            for f in tmp_files[:-1]:
                if os.path.exists(f):
                    os.unlink(f)


# ── Hlavní okno ────────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF Signature Stamper")
        self.setMinimumSize(900, 650)
        self.settings   = QSettings("pawleeq", "PDFStamper")
        self._doc: Optional[fitz.Document] = None
        self._pdf_path: Optional[str]  = None
        self._cert_path: Optional[str] = None
        self._build_ui()
        self._restore_settings()
        self._update_state()

    def _build_ui(self):
        toolbar = QToolBar("Hlavní", self)
        toolbar.setMovable(False)
        toolbar.setStyleSheet("QToolBar { spacing: 6px; padding: 4px; }")
        self.addToolBar(toolbar)

        self.btn_open = QPushButton("📂  Otevřít PDF")
        self.btn_open.clicked.connect(self._open_pdf)
        toolbar.addWidget(self.btn_open)

        toolbar.addSeparator()

        self.btn_cert = QPushButton("🔑  Certifikát")
        self.btn_cert.clicked.connect(self._select_cert)
        toolbar.addWidget(self.btn_cert)

        self.lbl_cert = QLabel("—")
        self.lbl_cert.setStyleSheet("color: #666; padding: 0 8px;")
        toolbar.addWidget(self.lbl_cert)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)

        self.lbl_stamps = QLabel("Razítka: 0")
        self.lbl_stamps.setStyleSheet("padding: 0 8px;")
        toolbar.addWidget(self.lbl_stamps)

        self.btn_sign = QPushButton("✍  Podepsat…")
        self.btn_sign.setFixedHeight(32)
        f = self.btn_sign.font()
        f.setBold(True)
        self.btn_sign.setFont(f)
        self.btn_sign.clicked.connect(self._sign_flow)
        toolbar.addWidget(self.btn_sign)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.thumb_panel = ThumbnailPanel()
        self.thumb_panel.page_selected.connect(self._on_page_selected)
        splitter.addWidget(self.thumb_panel)

        self.page_view = PageView()
        self.page_view.stamps_changed.connect(self._on_stamps_changed)
        splitter.addWidget(self.page_view)

        splitter.setSizes([THUMB_W + 32, 800])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        self.setCentralWidget(splitter)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Otevřete PDF soubor pro začátek.")

    def _update_state(self):
        has_pdf    = self._doc is not None
        has_cert   = bool(self._cert_path)
        has_stamps = self.page_view.stamp_count() > 0 if has_pdf else False
        self.btn_sign.setEnabled(has_pdf and has_cert and has_stamps)
        self.lbl_cert.setText(
            os.path.basename(self._cert_path) if has_cert else "—")

    def _on_stamps_changed(self):
        self.lbl_stamps.setText(f"Razítka: {self.page_view.stamp_count()}")
        self._update_state()

    def _open_pdf(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Otevřít PDF", "", "PDF soubory (*.pdf)")
        if not path:
            return
        try:
            doc = fitz.open(path)
            self._doc      = doc
            self._pdf_path = path
            self.page_view.load_document(doc)
            self.thumb_panel.load_document(doc)
            self.setWindowTitle(f"PDF Signature Stamper – {os.path.basename(path)}")
            self.status_bar.showMessage(
                f"{os.path.basename(path)}  |  {len(doc)} stran  |  "
                "Klikněte na stránku pro umístění razítka.")
            self._update_state()
        except Exception as e:
            QMessageBox.critical(self, "Chyba", f"Nelze otevřít PDF:\n{e}")

    def _select_cert(self):
        start = os.path.dirname(self._cert_path) if self._cert_path else ""
        path, _ = QFileDialog.getOpenFileName(
            self, "Vybrat certifikát", start, "Certifikáty (*.p12 *.pfx)")
        if path:
            self._cert_path = path
            self.settings.setValue("cert_path", path)
            self._update_state()
            self.status_bar.showMessage(f"Certifikát: {os.path.basename(path)}")

    def _on_page_selected(self, idx: int):
        self.page_view.set_page(idx)
        self.status_bar.showMessage(f"Stránka {idx + 1}")

    def _sign_flow(self):
        stamps = self.page_view.get_stamps()
        if not stamps:
            QMessageBox.warning(self, "Chyba", "Žádná razítka nejsou umístěna.")
            return

        dlg = PasswordDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        password = dlg.password()

        base    = os.path.splitext(os.path.basename(self._pdf_path))[0]
        suggest = os.path.join(os.path.dirname(self._pdf_path), f"{base}_signed.pdf")
        out_path, _ = QFileDialog.getSaveFileName(
            self, "Uložit podepsaný PDF", suggest, "PDF soubory (*.pdf)")
        if not out_path:
            return

        page_heights = {i: self._doc[i].rect.height for i in range(len(self._doc))}

        self.btn_sign.setEnabled(False)
        self._worker = SignerThread(
            self._pdf_path, out_path,
            self._cert_path, password,
            stamps, page_heights,
        )
        self._worker.progress.connect(self.status_bar.showMessage)
        self._worker.finished.connect(self._on_sign_done)
        self._worker.start()

    def _on_sign_done(self, success: bool, message: str):
        self._update_state()
        if success:
            self.status_bar.showMessage(f"✓ {message}")
            QMessageBox.information(self, "Hotovo", message)
        else:
            self.status_bar.showMessage("✗ Chyba při podepisování")
            QMessageBox.critical(self, "Chyba při podepisování", message)

    def _restore_settings(self):
        cert = self.settings.value("cert_path", "")
        if cert and os.path.exists(cert):
            self._cert_path = cert


# ── Vstupní bod ────────────────────────────────────────────────────────────────
def main():
    os.environ.setdefault('QT_MAC_WANTS_LAYER', '1')
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
