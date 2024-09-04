from functools import partial
from PySide2.QtGui import *
from PySide2.QtCore import *
from PySide2.QtWidgets import *
import sys
import getpass
import uuid
import pymongo
import datetime
import nuke
import socket
import os
import nukescripts
import tempfile
from PySide2.QtCore import QThread, Signal

from version001.clipboardUi import ClipboardUi

SERVER = pymongo.MongoClient('SV22', 27017)
DB = SERVER['paint']
USER_COLLECTION = DB['users']
CLIPBOARD_COLLECTION = DB['clipboard']
SCRIPT_LOCATION = "c:/clipboard"
CURRENT_USER = getpass.getuser()
HOSTNAME = socket.gethostname().upper()
IP = socket.gethostbyname(HOSTNAME)
img_path = ".nuke/version001"
user_home = os.path.expanduser("~")


class MongoLiveThread(QThread):
    collection_changed = Signal()  # Tín hiệu sẽ phát khi collection có sự thay đổi

    def __init__(self, collection):
        super(MongoLiveThread, self).__init__()
        self.collection = collection

    def run(self):
        try:
            with self.collection.watch() as stream:
                for change in stream:
                    print(f"Collection clipboard has changed: {change}")
                    self.collection_changed.emit()  # Phát tín hiệu khi có sự thay đổi
        except Exception as e:
            print(f"Error monitoring MongoDB collection: {e}")


class ClipboardCore(ClipboardUi):
    _all_users_cache = None  # Khởi tạo cache ở cấp độ class

    def __init__(self):
        super(ClipboardCore, self).__init__()

        self.is_refreshing = False

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.build_history)
        self.refresh_timer.start(120000)  # Làm mới mỗi 2 phút

        self.monitor_thread = MongoLiveThread(CLIPBOARD_COLLECTION)
        self.monitor_thread.collection_changed.connect(self.build_history)  # Kết nối tín hiệu với hàm build_history

        # Sử dụng cache nếu đã tải user trước đó, nếu không, tải từ MongoDB
        if ClipboardCore._all_users_cache is None:
            ClipboardCore._all_users_cache = [user for user in USER_COLLECTION.find()]
        self.all_users = ClipboardCore._all_users_cache

        self.build_users_list_widget()

        self.users_search_line_edit.textChanged.connect(self.build_users_list_widget)
        self.send_close_push_button.clicked.connect(self.close)
        self.send_push_button.clicked.connect(self.send_clipboard)
        self.received_close_push_button.clicked.connect(self.close)
        self.paste_push_button.clicked.connect(self.paste_clipboard)
        self.history_table_widget.currentCellChanged.connect(self.set_note)
        self.refresh_button.clicked.connect(self.build_history)

        self.build_history()

        self.monitor_thread.start()

    def set_note(self, index):
        item = self.history_table_widget.item(index, 0)
        if item is None:
            print(f"No item found at index {index}.")
            return  # Ngừng thực thi nếu không tìm thấy item

        obj = item.data(32)
        if obj is None:
            print("No data found for the selected item.")
            return  # Ngừng thực thi nếu không có dữ liệu

        note = obj.get('note', "No note available")
        self.received_notes_text_edit.setPlainText(note)

    # def paste_clipboard(self, row):
    #     item = self.history_table_widget.item(row, 0)
    #     doc = item.data(32)
    #     script = doc['nuke_file']
    #     try:
    #         nuke.tcl(script)
    #         print("Pasted Nuke script successfully.")
    #
    #         # Cập nhật trạng thái pasted trong MongoDB
    #         CLIPBOARD_COLLECTION.update_one({'_id': doc['_id']}, {'$set': {'pasted': True}})
    #
    #         # Cập nhật style để hàng không còn nổi bật
    #         for col in range(4):  # Giả sử bạn muốn xóa tô đậm ở 4 cột đầu tiên
    #             self.history_table_widget.item(row, col).setFont(QFont('Arial', weight=QFont.Normal))
    #
    #     except Exception as e:
    #         QMessageBox.warning(self, "Error", f"Failed to paste Nuke script: {e}")

    def paste_clipboard(self, row):
        import time

        start_time = time.time()

        item = self.history_table_widget.item(row, 0)
        doc = item.data(32)
        script = doc['nuke_file']

        # Đo thời gian lấy dữ liệu từ MongoDB
        data_fetch_time = time.time()
        print("Data fetch time: %.2f seconds" % (data_fetch_time - start_time))

        try:
            # Paste vào Nuke
            nuke.tcl(script)
            print("Pasted Nuke script successfully.")

            # Cập nhật trạng thái pasted trong MongoDB
            CLIPBOARD_COLLECTION.update_one({'_id': doc['_id']}, {'$set': {'pasted': True}})

            # Cập nhật style để hàng không còn nổi bật
            for col in range(4):  # Giả sử bạn muốn xóa tô đậm ở 4 cột đầu tiên
                self.history_table_widget.item(row, col).setFont(QFont('Arial', weight=QFont.Normal))

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to paste Nuke script: {e}")

        # Đo thời gian paste dữ liệu vào Nuke
        paste_time = time.time()
        print("Paste time: %.2f seconds" % (paste_time - data_fetch_time))

        # Tổng thời gian
        print("Total time: %.2f seconds" % (paste_time - start_time))

    def replace_local_path_with_network(self, node):
        ip_address = IP

        file_path = node['file'].value()
        local_drive = os.path.splitdrive(file_path)[0]
        local_prefix = os.path.join(local_drive, *file_path.split(os.sep)[:3])

        network_prefix = f"//{ip_address}/{local_drive[0].lower()}{file_path[2:]}".replace("\\", "/")

        if local_prefix in file_path:
            network_path = file_path.replace(local_prefix, network_prefix, 1)
            node['file'].setValue(network_path)
            print(f"Updated {node.name()} path to {network_path}")
        else:
            nuke.message("Đường dẫn không phù hợp để thay đổi.")

    def send_clipboard(self):
        row_count = self.stack_list_widget.count()
        if row_count == 0:
            QMessageBox.information(self, "Warning", "Chưa chọn người để gửi")
            return

        now = datetime.datetime.now()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".nk") as temp_file:
            nuke.nodeCopy(temp_file.name)

        with open(temp_file.name, 'r') as file:
            script = file.read()

        modified_script_lines = []
        for line in script.splitlines():
            if 'xpos' in line or 'ypos' in line:
                continue

            if 'file ' in line:
                file_path = line.split(' ')[-1].strip('"')

                if not file_path.startswith(f"//{IP}"):
                    local_drive = os.path.splitdrive(file_path)[0]
                    if local_drive:
                        network_prefix = f"//{IP}/{local_drive[0].lower()}{file_path[2:]}".replace("\\", "/")
                        modified_line = line.replace(file_path, network_prefix)
                    else:
                        modified_line = line
                else:
                    modified_line = line
                modified_script_lines.append(modified_line)
            else:
                modified_script_lines.append(line)

        modified_script = "\n".join(modified_script_lines)
        # print("Modified TCL Script to save:")
        # print(modified_script)

        for i in range(row_count):
            obj = self.stack_list_widget.item(i).data(32)
            doc = {
                'sender': CURRENT_USER,
                'ip_sender': IP,
                'submitted_at': now,
                'destination_user': obj['hostname'],
                'nuke_file': modified_script,
                'note': self.text_note_text_edit.toPlainText()
            }
            CLIPBOARD_COLLECTION.insert_one(doc)
        self.close()

    def build_history(self):

        if self.is_refreshing:
            return
        self.is_refreshing = True

        try:

            query = list(CLIPBOARD_COLLECTION.find({"destination_user": str(HOSTNAME)}).sort("submitted_at", -1))
            # print(query)
            self.history_table_widget.setUpdatesEnabled(False)  # Vô hiệu hóa cập nhật

            self.history_table_widget.setRowCount(len(query))
            for x, i in enumerate(query):
                sender_info = next((user for user in self.all_users if user['hostname'] == i['hostname_sender']), None)
                # print(sender_info)
                item1 = QTableWidgetItem(sender_info.get('name', 'Unknown') if sender_info else 'Unknown')
                item1.setData(32, i)

                item2 = QTableWidgetItem(i.get('client', ''))

                shot_names = i.get('shot_name_qc', [])
                if isinstance(shot_names, list):
                    shot_names_str = '\n'.join(shot_names)
                else:
                    shot_names_str = shot_names
                item3 = QTableWidgetItem(shot_names_str)

                item4 = QTableWidgetItem(self.get_time_difference_as_string(i['submitted_at']))

                delete_button = QPushButton()
                delete_button.setIcon(QIcon(os.path.join(user_home, img_path, 'button_delete.png')))
                delete_button.clicked.connect(partial(self.delete_row, x))

                get_button = QPushButton()
                get_button.setIcon(QIcon(os.path.join(user_home, img_path, 'button_paste.png')))
                get_button.clicked.connect(partial(self.paste_clipboard, x))

                self.history_table_widget.setItem(x, 0, item1)
                self.history_table_widget.setItem(x, 1, item2)
                self.history_table_widget.setItem(x, 2, item3)
                self.history_table_widget.setItem(x, 3, item4)
                self.history_table_widget.setCellWidget(x, 4, get_button)
                self.history_table_widget.setCellWidget(x, 5, delete_button)

                if not i.get('pasted', False):
                    for col in range(4):
                        self.history_table_widget.item(x, col).setFont(QFont(weight=QFont.Bold))
                        self.history_table_widget.item(x, col).setBackground(QColor(119, 136, 153))

            self.history_table_widget.setUpdatesEnabled(True)  # Kích hoạt lại cập nhật

        except Exception as e:
            print(f"Error in build_history: {e}")
        finally:
            self.is_refreshing = False

    def get_time_difference_as_string(self, date):
        delta = datetime.datetime.today() - date
        if delta.days < 0:
            return "A few seconds ago"

        if delta.days:
            return "%s days" % delta.days
        seconds = delta.seconds
        if seconds < 60:
            return "A few seconds ago"
        elif seconds < 3600:
            return "%s minutes ago" % int(seconds / 60)
        elif seconds < 86400:
            return "%s hours ago" % int(seconds / 3600)

    def build_users_list_widget(self):
        self.users_list_widget.clear()
        search_pattern = self.users_search_line_edit.text().lower()
        for user in self.all_users:
            name = user['name']
            if search_pattern in name.lower():
                item = QListWidgetItem(name)
                item.setData(32, user)
                item.setToolTip(self.get_user_tooltip(user))
                self.users_list_widget.addItem(item)
        self.users_list_widget.sortItems()

    def get_user_tooltip(self, user):
        return "IP: %s" % (user['ip_address'])

    def delete_row(self, row):
        item = self.history_table_widget.item(row, 0)
        obj = item.data(32)

        if '_id' in obj:
            print(f"Deleting document with _id: {obj['_id']}")
            result = CLIPBOARD_COLLECTION.delete_one({"_id": obj['_id']})

            if result.deleted_count > 0:
                print("Document deleted successfully.")
            else:
                print("Document not found or already deleted.")
        else:
            print("Error: No _id found in the selected row data.")

        self.history_table_widget.removeRow(row)

    def closeEvent(self, event):
        # Dừng QTimer khi ứng dụng đóng
        self.refresh_timer.stop()

        # Gọi closeEvent của lớp cơ sở để xử lý các tác vụ đóng cửa sổ khác
        super(ClipboardCore, self).closeEvent(event)


def start():
    start.panel = ClipboardCore()
    start.panel.show()
