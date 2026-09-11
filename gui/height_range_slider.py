"""Float-valued, two-handle Qt slider; no additional UI dependencies."""
import math
from PySide6.QtCore import Qt, Signal, QSize, QPointF
from PySide6.QtGui import QPainter, QPen, QColor
from PySide6.QtWidgets import QWidget


class HeightRangeSlider(QWidget):
    values_changed = Signal(float, float)
    margin = 13

    def __init__(self, parent=None):
        super().__init__(parent)
        self.minimum, self.maximum = 0.0, 10.0
        self.lower, self.upper = 0.0, 3.0
        self.active_handle = 'lower'
        self.dragging = False
        self.setMinimumHeight(52)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName('楼层高度双滑块：左地面，右天花板')
        self.setToolTip('拖动左侧地面或右侧天花板；方向键微调，Shift 加速，空格切换端点。')

    def sizeHint(self):
        return QSize(260, 52)

    def set_values(self, lower, upper, minimum=None, maximum=None):
        if not all(math.isfinite(v) for v in (lower,upper)) or lower >= upper:
            raise ValueError('天花板必须高于地面。')
        minimum = self.minimum if minimum is None else minimum
        maximum = self.maximum if maximum is None else maximum
        self.minimum = min(minimum,lower)
        self.maximum = max(maximum,upper)
        if self.maximum <= self.minimum:
            self.maximum = self.minimum + 1
        self.lower,self.upper = lower,upper
        self.update()

    def x_for_value(self, value):
        width=max(1,self.width()-2*self.margin)
        return self.margin + (value-self.minimum)/(self.maximum-self.minimum)*width

    def value_for_x(self, x):
        t=max(0.0,min(1.0,(x-self.margin)/max(1,self.width()-2*self.margin)))
        return self.minimum+t*(self.maximum-self.minimum)

    def paintEvent(self,event):
        painter=QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        y=19
        low,high=self.x_for_value(self.lower),self.x_for_value(self.upper)
        painter.setPen(QPen(QColor('#354653'),5,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap))
        painter.drawLine(QPointF(self.margin,y),QPointF(self.width()-self.margin,y))
        painter.setPen(QPen(QColor('#559b88') if self.isEnabled() else QColor('#45525c'),5))
        painter.drawLine(QPointF(low,y),QPointF(high,y))
        for name,x,color in [('lower',low,'#75dfbd'),('upper',high,'#f0b16b')]:
            painter.setBrush(QColor(color) if self.isEnabled() else QColor('#63717a'))
            painter.setPen(QPen(QColor('#f1f7fa') if self.hasFocus() and self.active_handle==name else QColor('#18232c'),2))
            painter.drawEllipse(QPointF(x,y),7,9)
        painter.setPen(QColor('#93a8b8'))
        painter.drawText(0,34,self.width()//2,16,Qt.AlignmentFlag.AlignLeft,f'{self.minimum:.2f} m')
        painter.drawText(self.width()//2,34,self.width()//2,16,Qt.AlignmentFlag.AlignRight,f'{self.maximum:.2f} m')

    def _move(self,value):
        lower,upper=self.lower,self.upper
        if self.active_handle=='lower':
            lower=max(self.minimum,min(round(value,6),upper-.000001))
        else:
            upper=min(self.maximum,max(round(value,6),lower+.000001))
        if (lower,upper)!=(self.lower,self.upper):
            self.lower,self.upper=lower,upper
            self.update()
            self.values_changed.emit(lower,upper)

    def mousePressEvent(self,event):
        if event.button()!=Qt.MouseButton.LeftButton:
            return super().mousePressEvent(event)
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        x=event.position().x()
        dl,du=abs(x-self.x_for_value(self.lower)),abs(x-self.x_for_value(self.upper))
        self.active_handle=('upper' if self.active_handle=='lower' else 'lower') if abs(dl-du)<.5 else ('lower' if dl<du else 'upper')
        self.dragging=True
        self._move(self.value_for_x(x))
        self.update()
        event.accept()

    def mouseMoveEvent(self,event):
        if self.dragging:
            self._move(self.value_for_x(event.position().x()))
            event.accept()

    def mouseReleaseEvent(self,event):
        if self.dragging and event.button()==Qt.MouseButton.LeftButton:
            self._move(self.value_for_x(event.position().x()))
            self.dragging=False
            event.accept()

    def keyPressEvent(self,event):
        if event.key()==Qt.Key.Key_Space:
            self.active_handle='upper' if self.active_handle=='lower' else 'lower'
            self.update()
            event.accept()
        elif event.key() in (Qt.Key.Key_Left,Qt.Key.Key_Right,Qt.Key.Key_Down,Qt.Key.Key_Up):
            step=.1 if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else .01
            direction=-1 if event.key() in (Qt.Key.Key_Left,Qt.Key.Key_Down) else 1
            self._move((self.lower if self.active_handle=='lower' else self.upper)+direction*step)
            event.accept()
        else:
            super().keyPressEvent(event)

    def focusInEvent(self,event):
        super().focusInEvent(event)
        self.update()

    def focusOutEvent(self,event):
        super().focusOutEvent(event)
        self.update()
