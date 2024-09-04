from PySide2.QtGui import *
from PySide2.QtCore import *
import sys
import os
from PySide2.QtWidgets import *


img_path = ".nuke/version001"
user_home = os.path.expanduser("~")

class ClipboardUi(QTabWidget):
    def __init__(self):
        super(ClipboardUi, self).__init__()

        self.setWindowTitle("QC List")
        # self.setWindowFlag(Qt.WindowStaysOnTopHint)
        self.resize(770,600)
        self.setMinimumSize(770,600)

        #Widgets

        users_label =  QLabel("Users")
        self.users_list_widget = QListWidget()
        self.users_list_widget.setDragEnabled(True)
        search_label = QLabel("Search")
        self.users_search_line_edit = QLineEdit()
        stack_label = QLabel("Stack")
        self.stack_list_widget = QListWidget()
        self.stack_list_widget.setAcceptDrops(True)
        self.text_note_text_edit = QPlainTextEdit()
        self.send_push_button = QPushButton("Send")
        self.send_close_push_button = QPushButton("Close")

        history_label = QLabel("History")
        self.history_table_widget = HistoryTableWidget()
        notes_label = QLabel("Notes")
        self.received_notes_text_edit = QPlainTextEdit()
        self.paste_push_button = QPushButton("Paste")
        # self.paste_push_button.setShortcut(Space)
        self.received_close_push_button = QPushButton("Close")
        icon_path = os.path.join(user_home, img_path, 'button_refesh.png')
        self.refresh_button = QPushButton()
        self.refresh_button.setIcon(QIcon(icon_path))
        self.refresh_button.setIconSize(QSize(27, 27))
        self.refresh_button.setFixedSize(27, 27)
        # self.refresh_button.setFlat(True)  # Loại bỏ khung nền của button


        self.send_main_widget = QWidget()
        self.receive_main_widget = QWidget()


        # Layout

        send_layout = QHBoxLayout()
        send_layout_left = QVBoxLayout()
        send_layout_left.addWidget(users_label)
        send_layout_left.addWidget(self.users_list_widget)
        search_layout = QHBoxLayout()
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.users_search_line_edit)
        send_layout_left.addLayout(search_layout)

        send_layout_right = QVBoxLayout()
        send_layout_right.addWidget(stack_label)
        send_layout_right.addWidget(self.stack_list_widget)
        send_layout_right.addWidget(self.text_note_text_edit)
        send_action_layout = QHBoxLayout()
        send_action_layout.addWidget(self.send_push_button)
        send_action_layout.addWidget(self.send_close_push_button)
        send_layout_right.addLayout(send_action_layout)

        send_layout.addLayout(send_layout_left)
        send_layout.addLayout(send_layout_right)

        receive_layout = QVBoxLayout()
        receive_layout_left = QVBoxLayout()
        receive_layout1 = QHBoxLayout()
        receive_layout1.addWidget(history_label)
        receive_layout1.addWidget(self.refresh_button)
        receive_layout_left.addLayout(receive_layout1)
        receive_layout_left.addWidget(self.history_table_widget)
        # receive_layout_left.addWidget(self.refresh_button)
        # receive_action_layout = QHBoxLayout()
        # receive_action_layout.addWidget(self.paste_push_button)
        # receive_action_layout.addWidget(self.received_close_push_button)
        # receive_layout_left.addLayout(receive_action_layout)

        # receive_layout_right = QVBoxLayout()
        # receive_layout_right.addWidget(notes_label)
        # receive_layout_right.addWidget(self.received_notes_text_edit)

        receive_layout.addLayout(receive_layout_left)
        # receive_layout.addLayout(receive_layout_right)

        self.send_main_widget.setLayout(send_layout)
        self.receive_main_widget.setLayout(receive_layout)

        # self.addTab(self.send_main_widget, "Send")
        self.addTab(self.receive_main_widget, "QC")

        # self.refresh_button.setStyleSheet(self.get_style_sheet())
        # # self.users_search_line_edit.setStyleSheet(self.get_style_sheet())
        # self.refresh_button.setIconSize(QSize(24, 24))  # Điều chỉnh kích thước icon nếu cần
        # self.refresh_button.setFixedSize(100, 40)  # Điều chỉnh kích thước button nếu cần



class HistoryTableWidget(QTableWidget):
    def __init__(self):
        super(HistoryTableWidget, self).__init__()

        self.setColumnCount(6) # them 3 cot
        # self.setColumnCount(len(self.header))
        self.setAlternatingRowColors(True)
        self.setColumnWidth(0, 125)
        self.setColumnWidth(1, 100)
        self.setColumnWidth(2, 325)
        self.setColumnWidth(3, 100)
        self.setColumnWidth(4, 50)
        self.setColumnWidth(5, 50)
        self.horizontalHeader().setStretchLastSection(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setHorizontalHeaderItem(0, QTableWidgetItem("Name"))
        self.setHorizontalHeaderItem(1, QTableWidgetItem("Show"))
        self.setHorizontalHeaderItem(2, QTableWidgetItem("Shot QC"))
        self.setHorizontalHeaderItem(3, QTableWidgetItem("Date"))
        self.setHorizontalHeaderItem(4, QTableWidgetItem("Paste"))
        self.setHorizontalHeaderItem(5, QTableWidgetItem("Delete"))
        self.verticalHeader().setVisible(False)
        # self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        # Uncomment the following line if you want the last column to stretch

