from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QAction, QFileDialog, QGridLayout, QSpinBox, QDockWidget, QFrame
from PyQt5 import QtGui
from PyQt5 import QtCore

import matplotlib as mpl
mpl.use("Qt5Agg")
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt

import sys
import os
import numpy as np
import cv2


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()

        # 初期値
        self.setGeometry(0, 0, 1200, 700)
        self.image = QtGui.QImage()
        
        # canvas
        self.canvas = Canvas()
        self.setCentralWidget(self.canvas)

        # zoomwidge
        self.zoomWidget = ZoomWidget()
        self.zoomWidget.valueChanged.connect(self.paintCanvas)

        # qdockwidget
        self.right_dock = QDockWidget('right', self)
        self.right_dock.setStyleSheet('QFrame {background-color: white}')
        self.graph_window = GraphWindow()
        self.right_dock.setWidget(self.graph_window)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.right_dock)

        # menubarを作成
        self.createMenubar()

        # trigger
        self.canvas.targetAreaSelected.connect(self.createHist)



    def createMenubar(self):
        # menubar
        self.menubar = self.menuBar()

        # menubarにメニューを追加
        self.filemenu = self.menubar.addMenu('File')
        
        # viewbarにメニューを追加
        self.viewmenu = self.menubar.addMenu('View')

        # アクションの追加
        self.openAction()
        self.viewAction()

    def openAction(self):
        # アクションの作成
        self.open_act = QAction('開く')
        self.open_act.setShortcut('Ctrl+O') # shortcut
        self.open_act.triggered.connect(self.openFile) # open_actとメソッドを紐づける

        # メニューにアクションを割り当てる
        self.filemenu.addAction(self.open_act)

    def viewAction(self):
        self.viewmenu.addAction(self.right_dock.toggleViewAction())

    def openFile(self):
        self.filepath = QFileDialog.getOpenFileName(self, 'open file', '', 'Images (*.jpeg *.jpg *.png *.bmp)')[0]
        if self.filepath:
            self.canvas.openImage(self.filepath)
            self.paintCanvas()

    def paintCanvas(self):
        # canvasのスケールを更新
        self.canvas.scale = self.scaleFitWindow()
        self.canvas.update()

    def scaleFitWindow(self):
        # MainWindowのウィンドウサイズ
        e = 2.0 # 余白
        w1 = self.centralWidget().width() - e
        h1 = self.centralWidget().height() - e
        a1 = w1 / h1
        
        # pixmapのサイズ
        w2 = self.canvas.pixmap.width()
        h2 = self.canvas.pixmap.height()
        a2 = w2 / h2

        # a1が大きい -> 高さに合わせる
        # a2が大きい -> 幅に合わせる
        return w1 / w2 if a2 >= a1 else h1 / h2

    def adjustScale(self):
        value = self.scaleFitWindow()
        value = int(100 * value)
        self.zoomWidget.setValue(value)

    def resizeEvent(self, event):
        # canvasがTrue かつ pixmapがnullじゃない場合
        if self.canvas and not self.canvas.pixmap.isNull():
            self.adjustScale()
        super(MainWindow, self).resizeEvent(event)

    def createHist(self):
        self.graph_window.axes.clear()
        colors = ['r', 'g', 'b']
        for i, color in enumerate(colors):
            hist = cv2.calcHist([np.uint8(self.canvas.target_area)], [i], None, [256], [0, 256])
            hist = np.sqrt(hist)

            self.graph_window.axes.plot(hist, color = color)
            self.graph_window.fig.canvas.draw()


class GraphWindow(QFrame):
    def __init__(self):
        super(GraphWindow, self).__init__()
        # layout
        self.graph_window_layout = QGridLayout()

        # set layout
        self.setLayout(self.graph_window_layout)

        # graph_window
        self.fig = plt.Figure()
        self.fig_canvas = FigureCanvas(self.fig)
        self.graph_window_layout.addWidget(self.fig_canvas)
        self.axes = self.fig.add_subplot(111)



class Canvas(QWidget):

    targetAreaSelected = QtCore.pyqtSignal()

    def __init__(self):
        super(Canvas, self).__init__()

        # 初期値
        self.painter = QtGui.QPainter()
        self.pixmap = QtGui.QPixmap()
        self.scale = 1.0

        self.shapes = []
        self.rectangle = Shape()
        self.current = None

        # canvasのレイアウト
        self.canvas_layout = QGridLayout()
        
        # canvas_layoutをQWidget(self)にセット
        self.setLayout(self.canvas_layout)


    def openImage(self, filepath):
        img = QtGui.QImage()
        
        # 画像ファイルの読み込み
        if not img.load(filepath):
            return False

        # QImage -> QPixmap
        self.pixmap = QtGui.QPixmap.fromImage(img)


    def paintEvent(self, event):
        if not self.pixmap:
            return super(Canvas, self).paintEvent(event)

        # paintオブジェクトの生成（描画するためのもの）
        p = self.painter

        # paintができる状態にする
        p.begin(self)

        # 画像のスケール情報
        p.scale(self.scale, self.scale)

        # 原点の設定
        p.translate(self.offsetToCenter())

        # 画像を描画する
        p.drawPixmap(0, 0, self.pixmap)

        Shape.scale = self.scale
        # 四角を描画
        if self.current:
            self.current.paint(p)
            self.rectangle.paint(p)
            
        # 描画したものを表示
        for shape in self.shapes:
            shape.paint(p)
        
        # paintの終了
        p.end()
    
    # 原点補正
    def offsetToCenter(self):
        scale = self.scale 
        area = super(Canvas, self).size()
        w, h = self.pixmap.width() * scale, self.pixmap.height() * scale
        aw, ah = area.width(), area.height()
        x = (aw - w) / (2 * scale) if aw > w else 0
        y = (ah - h) / (2 * scale) if ah > h else 0

        return QtCore.QPoint(int(x), int(y))

    # Pixmap外
    def outOfPixmap(self, point):
        w = self.pixmap.width()
        h = self.pixmap.height()
        return not (0 <= point.x() < w and 0 <= point.y() < h)

    # 交点
    def intersectionPoint(self, point1, point2):
        size = self.pixmap.size()
        points = [
            (0, 0),
            (size.width(), 0),
            (size.width(), size.height()),
            (0, size.height()),
        ]

        x1, y1 = point1.x(), point1.y()
        x2, y2 = point2.x(), point2.y()
        x, y = self.intersectingEdges((x1, y1), (x2, y2), points)

        return QtCore.QPoint(x, y)

    # 交点の座標を求める
    def intersectingEdges(self, point1, point2, points):
        # クリックした位置
        (x1, y1) = point1

        # マウスを移動させた位置
        (x2, y2) = point2
        
        for i in range(4):
            # points: [(0, 0), (w, 0), (w. h), (0, h)]
            # p1-p2を結んだ線と交差
            x3, y3 = points[i]
            x4, y4 = points[(i + 1) % 4]

            # 交差する点を求めるときに使う式
            denom = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)
            nua = (x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)
            nub = (x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3)

            # 交差しない場合
            if denom == 0:
                continue

            # 交差する点を求める
            ua, ub = nua / denom, nub / denom
            if 0 <= ua <= 1 and 0 <= ub <= 1:
                x = x1 + ua * (x2 - x1)
                y = y1 + ua * (y2 - y1)
    
        return x, y


    # press_event(マウスをクリックしたときに発生)
    def mousePressEvent(self, event):
        # クリックした場所の位置(x, y)を取得
        pos = self.transformPos(event.localPos())

        # 左クリックが押された場合
        if event.button() == QtCore.Qt.LeftButton:
            # 画像の範囲内の場合
            if not self.outOfPixmap(pos):
                self.current = Shape()
                self.current.addPoint(pos)

    # move_event(クリックした状態でマウスを移動したときに発生)
    def mouseMoveEvent(self, event):
        pos = self.transformPos(event.localPos())
        if not self.current:
            return

        # 画像の範囲外の場合
        if self.outOfPixmap(pos):
            # 四角を描画するための位置情報
            pos = self.intersectionPoint(self.current[0], pos)
        self.rectangle.points = [self.current[0], pos]
        
        # 四角を可視化するために必要
        self.repaint()

    # release_event(クリックを離したときに発生)
    def mouseReleaseEvent(self, event):
        if self.current:
            self.current.points = self.rectangle.points
            self.getTargetArea(self.current.points)
            self.initialize()

    def getTargetArea(self, points):
        self.x = int(min(points[0].x(), points[1].x()))
        self.y = int(min(points[0].y(), points[1].y()))
        self.w = int(abs(points[0].x() - points[1].x()))
        self.h = int(abs(points[0].y() - points[1].y()))

        rgbs = []
        for w in range(self.w):
            for h in range(self.h):
                # pixmap -> QImageからQRGB値を取得
                qrgb = self.pixmap.toImage().pixel(self.x + w, self.y + h)
                rgb = [QtGui.qRed(qrgb), QtGui.qGreen(qrgb), QtGui.qBlue(qrgb)]
                rgbs.append(rgb)
        
        # 選択した範囲のrgb情報
        self.target_area = np.array(rgbs).reshape(self.h, self.w, 3)
        

    # 初期化関数
    def initialize(self):
        self.shapes = [self.current]
        self.current = None
        self.targetAreaSelected.emit()
        self.update()

    # 画像左上を(0, 0)に補正
    def transformPos(self, point):
        return point / self.scale - self.offsetToCenter()
    

class ZoomWidget(QSpinBox):
    def __init__(self, value=100):
        super(ZoomWidget, self).__init__()

# 四角を描画するためのShapeクラス
class Shape(object):
    def __init__(self):
        # 初期値
        self.scale = 1.0
        self.point_size = 8
        self.points = []
        self.rectangle_color = QtGui.QColor(0, 255, 0, 128)
        self.x = None
        self.y = None
        self.w = None
        self.h = None

    # リストのようにShapeクラスのインスタンスから取得する情報
    def __getitem__(self, key):
        return self.points[key]

    # Canvasで実装したQPainterを受け取って四角を描画する関数
    def paint(self, painter):
        # pointsがTrueの場合
        if self.points:
            # paintEventで使用するpenを設定
            pen = QtGui.QPen(self.rectangle_color)
            pen.setWidth(max(1, int(round(5 / self.scale))))
            painter.setPen(pen)

            # ウィンドウに可視化するための位置情報
            line_path = QtGui.QPainterPath()
            vrtx_path = QtGui.QPainterPath()

            if len(self.points) == 2:
                # 四角形の情報(x, y, w, h)
                rectangle = self.getRectFromLine(*self.points)
                line_path.addRect(rectangle)
                # クリックした位置と離した位置を丸で表現
                for i in range(len(self.points)):
                    self.drawVrtx(vrtx_path, i)
            
            # ウィンドウ上に描画
            painter.drawPath(line_path)
            painter.drawPath(vrtx_path)

    # クリックした位置と離した位置をアウトラインとして提供する関数
    def drawVrtx(self, path, i):
        d = self.point_size / self.scale
        point = self.points[i]
        path.addEllipse(point, d / 2.0, d / 2.0)

    # クリックした位置を保持する関数
    def addPoint(self, point):
        self.points.append(point)

    # クリックした位置と離した位置から四角形の情報を取得する関数
    def getRectFromLine(self, point1, point2):
        x1, y1 = point1.x(), point1.y()
        x2, y2 = point2.x(), point2.y()
        w = x2 - x1
        h = y2 - y1

        return QtCore.QRectF(x1, y1, w, h)

def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())

main()
