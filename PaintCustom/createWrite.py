# Import các module cần thiết cho Nuke và PySide2
import shutil

import nuke
import nukescripts
import json
import os
import re
import csv
import socket
import pymongo
from datetime import datetime
import tempfile
import getpass
from PySide2 import QtWidgets, QtGui, QtCore

#Connect server

SERVER = pymongo.MongoClient('SV22', 27017)
DB = SERVER['paint']
USER_COLLECTION = DB['users']
CLIPBOARD_COLLECTION = DB['clipboard']
CURRENT_USER = getpass.getuser()
HOSTNAME = socket.gethostname().upper()
IP = socket.gethostbyname(HOSTNAME)

client_csv_path = r"\\192.168.2.22\DataVina\tasks2.csv"
codec_csv_path = r"\\192.168.2.22\DataVina\codec_mov2.csv"


# Các hàm tiện ích để xử lý đường dẫn và tên file
def get_shot_name(filename):
    path_src, file = os.path.split(filename)
    shot_name = file.split(".")[0]
    root, ext = os.path.splitext(filename)
    return path_src, shot_name, ext

def process_task_name(task_name, reduce_word):
    if reduce_word:
        parts = re.split("[_-]", task_name)
        try:
            reduce_word = int(reduce_word)
            if reduce_word < 0:
                newname = "_".join(parts[:reduce_word])
                return newname
        except ValueError:
            pass
    return task_name

def process_task_name_LUMA(shotname, ver):
    parts = shotname.split("_")
    if parts:
        prefix = "_".join(parts[:3])  # Lấy ba phần đầu tiên để tạo tiền tố
        plate = parts[3][0].upper() + parts[3][1:]  # Viết hoa ký tự đầu tiên
        identifier = parts[4]
        version = parts[4][0] + ver[1:]
        newname = f"{prefix}_paint{plate}.{identifier}_{version}_SEI"
        return newname
    return shotname

def process_task_name_SK(shotname, ver):
    parts = shotname.split("_")
    if parts:
        prefix = "_".join(parts[1:4])
        newname = f"{prefix}_INH_{ver}"
        return newname
    return shotname


def read_client_tasks_from_csv(csv_file):
    client_tasks = {}
    with open(csv_file, mode="r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            client_tasks[row["client"]] = {
                "task_name": row["task_name"],
                "reduce_word": row["reduce_word"],
                "version": row["version"],
            }
    return client_tasks

def get_client_path(client, csv_file):
    with open(csv_file, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)  # Đọc CSV dưới dạng từ điển

        for row in reader:
            if row['client'] == client:
                return row['Path']  # Trả về giá trị trong cột 'Path'

        raise ValueError(f"Client '{client}' không tồn tại trong danh sách.")

def read_codec_info_from_csv(csv_file):
    codec_info = {}
    with open(csv_file, mode="r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            codec_name = row["codec_name"].strip()
            codec_index = None
            profile_index = None
            codec_profile = (
                row["codec_profile"].strip() if "codec_profile" in row else None
            )
            try:
                if row["codec_index"] and int(row["codec_index"]) != -1:
                    codec_index = int(row["codec_index"])
                if row["profile_index"] and int(row["profile_index"]) != -1:
                    profile_index = int(row["profile_index"])
            except ValueError:
                print(f"Dữ liệu không hợp lệ cho codec_name: {codec_name}")

            codec_info[codec_name] = {
                "codec_index": codec_index,
                "profile_index": profile_index,
                "codec_profile": codec_profile,
            }
    return codec_info

def generate_render_path(metadata, type_name, version, reduce_word, client, custom_path, set_version):
    digit_frames = metadata.get('digit_frames', 4)  # Giả sử 4 là giá trị mặc định nếu không tồn tại
    frame_placeholder = f"%0{digit_frames}d"
    path_folder = custom_path
    ver = str(format_version(version, set_version))
    shot_name_final = process_task_name(metadata["shotname"], reduce_word)

    if client == "LUMA":
        shot_name_render = process_task_name_LUMA(shot_name_final, ver)

    elif client == "SK":
        shot_name_render = process_task_name_SK(shot_name_final, ver)
    else:
        if shot_name_final:
            if not type_name:
                shot_name_render = f"{shot_name_final}_{ver}"
            else:
                shot_name_render = (
                    f"{shot_name_final}_{type_name}_{ver}"
                )
        else:
            shot_name_render = (
                f"{metadata['shotname']}_{type_name}_{ver}"
            )


    if metadata["ext"] in [".exr", ".dpx", ".jpg", ".png"]:
        if client == "LUMA":
            render_path = os.path.join(
                path_folder,
                shot_name_render,
                f"{shot_name_render}_exr.{frame_placeholder}{metadata['ext']}",
            )
        else:
            render_path = os.path.join(
                path_folder,
                shot_name_render,
                f"{shot_name_render}.{frame_placeholder}{metadata['ext']}",
            )
    else:
        render_path = os.path.join(
            path_folder, f"{shot_name_render}{metadata['ext']}"
        )

    render_path = os.path.normpath(render_path).replace("\\", "/")
    path_folder = os.path.normpath(path_folder).replace("\\", "/")

    return render_path, shot_name_render, path_folder

def format_version(version,set_version):
    ver_int = int(version)
    if ver_int < 10:
        ver = f"00{ver_int}"
    elif ver_int < 100:
        ver = f"0{ver_int}"
    else:
        ver = f"{ver_int}"

    if set_version:
        if set_version == -1:
            ver_final = str(ver)
        else:
            ver_final = f"{set_version}{ver}"
    else:
        ver_final = f"v{str(ver)}"
    return ver_final

def format_metadata_info(metadata):
    formatted_info = json.dumps(metadata, indent=4)
    return formatted_info

# def my_after_render(write_node_name):
#     write_node = nuke.toNode(write_node_name)
#     if write_node:
#         rendered_file = write_node['file'].value()
#         read_node = nuke.createNode('Read', 'file {}'.format(rendered_file))
#         read_node.setXYpos(write_node.xpos(), write_node.ypos() + 100)
#         print("Created Read node for rendered file:", rendered_file)


class MetadataHandler:
    def __init__(self, panel):
        self.panel = panel

    def get_metadata_from_node(self, node):
        metadata = node.metadata()
        input_filename = metadata.get("input/filename")
        path_src, shotname, ext = get_shot_name(input_filename)

        if not shotname:
            nuke.message("Không thể lấy được tên shot từ filename.")
            return None

        client = "default"
        task_info = self.panel.client_tasks.get(
            client, {"task_name": "Unknow Task", "reduce_word": None, "version": None}
        )
        task_name = task_info["task_name"]
        reduce_word = task_info["reduce_word"]
        set_version = task_info["version"]
        type_selected = self.panel.type_enum.value()
        version = self.panel.version_input.value()
        type_name = task_name if type_selected == "FINAL" else type_selected
        path_render = reduce_path_by_one_unit(path_src, ext)
        # print(f"path_render sau khi giam 1: {path_render}")
        digit_frames = self.extract_digits_frames(node["file"].value())

        metadata_dict = {
            "digit_frames": digit_frames,
            "shotname": shotname,  # Đảm bảo shotname được truyền vào
            "ext": ext
        }

        path_file, shot_name_render, path_folder = generate_render_path(
            metadata_dict,
            type_name,
            version,
            reduce_word,
            client,
            path_render,
            set_version,
        )

        colorspace = self.extract_colorspace(node["colorspace"].value())
        mov64_fps = round(metadata.get("input/frame_rate", 0), 3)
        codec = metadata.get("quicktime/codec_name")
        compression = metadata.get("exr/compressionName") if ext == ".exr" else None
        datatype = metadata.get("input/bitsperchannel")
        first_frame = node["first"].value()
        last_frame = node["last"].value()

        return {
            "input_filename": input_filename,
            "path_src": path_src,
            "shotname": shotname,
            "ext": ext,
            "colorspace": colorspace,
            "digit_frames": digit_frames,
            "mov64_fps": mov64_fps,
            "codec": codec,
            "compression": compression,
            "datatype": datatype,
            "first_frame": first_frame,
            "last_frame": last_frame,
            "client": client,
            # "path_file": path_render,
            "path_render_delivery": path_file,
            "parent_folder": path_folder,
            # "shot_name_render": shot_name_render,
            "shot_name_delivery": shot_name_render,
            "version": version,
        }

    def store_metadata(self, metadata):
        # print(f"Storing metadata for: {metadata['input_filename']}")
        if not metadata["input_filename"]:
            nuke.message("Không tìm thấy tên shot trong metadata.")
            return

        metadata_node = nuke.toNode("metadata_storage") or nuke.createNode(
            "NoOp", inpanel=False
        )
        metadata_node.setName("metadata_storage")
        metadata_node["hide_input"].setValue(True)

        # Load existing metadata
        existing_metadata = self.load_existing_metadata(metadata_node)
        if existing_metadata is None:
            existing_metadata = {}

        # Prevent adding metadata to itself and causing recursion
        input_filename = metadata["input_filename"]
        if input_filename in existing_metadata:
            existing_metadata[input_filename].update(metadata)
        else:
            existing_metadata[input_filename] = metadata

        try:
            updated_metadata_str = json.dumps(existing_metadata, indent=4)
            metadata_knob = metadata_node.knob("metadata")
            if not metadata_knob:
                metadata_knob = nuke.Text_Knob("metadata", "Metadata", updated_metadata_str)
                metadata_node.addKnob(metadata_knob)
            else:
                metadata_knob.setValue(updated_metadata_str)
        except RecursionError:
            print("RecursionError: Quá trình mã hóa JSON vượt quá giới hạn đệ quy.")
        except Exception as e:
            print(f"Lỗi khi lưu metadata: {e}")

    def load_existing_metadata(self, metadata_node):
        metadata_knob = metadata_node.knob("metadata")
        if metadata_knob:
            metadata_str = metadata_knob.value()
            try:
                return json.loads(metadata_str)
            except RecursionError:
                print("RecursionError: Quá trình giải mã JSON vượt quá giới hạn đệ quy.")
                return {}
            except json.JSONDecodeError as e:
                print(f"Lỗi giải mã JSON: {e}")
                return {}
        else:
            return {}

    def extract_colorspace(self, value):
        match = re.search(r"\(([^)]+)\)", value)
        return match.group(1) if match else value

    def extract_digits_frames(self, filepath):
        match = re.search(r"%0(\d+)d", filepath)
        return int(match.group(1)) if match else None

class NodeConfigurator:


    def initialize_write_node(self, metadata):
        write_node = nuke.createNode("Write")
        write_node["file_type"].setValue(metadata["ext"].lstrip("."))
        # Gán đoạn mã TCL vào afterRender để tạo Read node sau khi render xong
        # tcl_code = '''
        #         set rendered_file [value [topnode].file]
        #         Read {
        #             file $rendered_file
        #             name "auto_read_node"
        #         }
        #         '''
        # write_node['afterRender'].setValue(tcl_code)

        self._force_refresh_ui(write_node)
        return write_node

    def configure_write_node(self, write_node, metadata, codec_info):
        write_node["colorspace"].setValue(metadata["colorspace"])
        write_node["create_directories"].setValue(True)

        if metadata["ext"] == ".mov":
            self._configure_mov_write_node(write_node, metadata, codec_info)
        elif metadata["ext"] == ".exr":
            self._configure_exr_write_node(write_node, metadata)
        elif metadata["ext"] == ".dpx":
            self._configure_dpx_write_node(write_node, metadata)
        elif metadata["ext"] == ".jpg":
            self._configure_jpg_write_node(write_node)

    def _configure_mov_write_node(self, write_node, metadata, codec_info):
        if metadata.get("mov64_fps"):
            write_node["mov64_fps"].setValue(metadata["mov64_fps"])

        if metadata.get("codec"):
            codec_info = codec_info.get(metadata["codec"])
            if codec_info:
                if "codec_index" in codec_info:
                    write_node["mov64_codec"].setValue(codec_info["codec_index"])
                if "profile_index" in codec_info:
                    profile_knob = codec_info.get("codec_profile")
                    if profile_knob and profile_knob != "None":
                        write_node[profile_knob].setValue(codec_info["profile_index"])
                        self._force_refresh_ui(write_node)

    def _configure_exr_write_node(self, write_node, metadata):
        write_node["metadata"].setValue(4)
        if metadata.get("datatype"):
            write_node["datatype"].setValue(metadata["datatype"])
        if metadata.get("compression"):
            write_node["compression"].setValue(metadata["compression"])

    def _configure_dpx_write_node(self, write_node, metadata):
        if metadata.get("datatype"):
            write_node["datatype"].setValue(metadata["datatype"])

    def _configure_jpg_write_node(self, write_node):
        write_node["_jpeg_quality"].setValue(1)

    def _force_refresh_ui(self, write_node):
        write_node.forceValidate()
        nuke.root().forceValidate()
        nuke.updateUI()

class MetadataPanel(nukescripts.PythonPanel):
    def __init__(self):
        super(MetadataPanel, self).__init__("Paint Tools", "com.example.MetadataPanel")
        self._create_ui_elements()
        self.client_tasks = read_client_tasks_from_csv(client_csv_path)
        self.codec_info = read_codec_info_from_csv(codec_csv_path)
        self.metadata_handler = MetadataHandler(self)
        self.node_configurator = NodeConfigurator()
        self.info_text = []  # Khởi tạo biến self.info_text

        # Check for metadata_storage node and update info
        self.check_and_update_metadata()


        # Xu ly tab giao shot
        self.all_users = [user for user in USER_COLLECTION.find()]

        self.build_lead_users_enum()
        # self.sendqc_button.clicked.connect(self.send_clipboard)

    def _create_ui_elements(self):
        self.general_tab = nuke.Tab_Knob("setupWrite_tab", "Setup Node Write")
        self.addKnob(self.general_tab)

        self.save_button = nuke.PyScript_Knob("save_metadata", "Import Metadata")
        self.delete_button = nuke.PyScript_Knob("delete_metadata", "Delete Metadata")
        self.save_nuke_button = nuke.PyScript_Knob("save_nuke_script", "Save Nuke Script")
        self.load_button = nuke.PyScript_Knob("load_metadata", "Create Write Node")
        self.client_enum = nuke.Enumeration_Knob("client_enum", "Client", ["default", "client1", "client2"])
        self.type_enum = nuke.Enumeration_Knob(
            "type_enum", "Render for", ["FINAL", "REN", "DENOISE", "WIP"]
        )
        self.version_input = nuke.Int_Knob("version_input", "Version")
        self.version_input.setValue(1)

        self.filename_enum = nuke.Enumeration_Knob("filename_enum", "Shot", [])
        self.path_input = nuke.File_Knob("path_input", "Render Path")

        self.info = nuke.Multiline_Eval_String_Knob("info")
        # self.info.setEnabled(False)



        self.save_button.setFlag(nuke.STARTLINE)
        self.delete_button.clearFlag(nuke.STARTLINE)
        self.save_nuke_button.clearFlag(nuke.STARTLINE)

        self.version_input.setFlag(nuke.STARTLINE)
        self.client_enum.clearFlag(nuke.STARTLINE)
        self.type_enum.clearFlag(nuke.STARTLINE)

        self.filename_enum.setFlag(nuke.STARTLINE)
        self.load_button.clearFlag(nuke.STARTLINE)

        self.addKnob(self.save_button)
        self.addKnob(self.delete_button)
        self.addKnob(self.save_nuke_button)
        self.addKnob(self.path_input)
        self.addKnob(self.version_input)
        self.addKnob(self.client_enum)
        self.addKnob(self.type_enum)
        self.addKnob(self.filename_enum)
        self.addKnob(self.load_button)

        self.addKnob(nuke.Text_Knob("label2", "", "   "))
        div1 = nuke.Text_Knob("divider", "Qc & Giao shot")
        self.addKnob(div1)
        self.addKnob(nuke.Text_Knob("label2", "", "   "))



        self.leadQCChoice = nuke.Enumeration_Knob("leadQCChoice", "Lead QC", [])
        self.sendqc_button = nuke.PyScript_Knob('sendqc', 'Gửi link QC')
        self.delivery_path = nuke.File_Knob("delivery_path", "Delivery Path")
        self.send_shot_button = nuke.PyScript_Knob('send_shot_button', 'Giao shot')

        self.leadQCChoice.setFlag(nuke.STARTLINE)
        self.sendqc_button.setFlag(nuke.STARTLINE)
        self.delivery_path.setFlag(nuke.STARTLINE)
        self.send_shot_button.setFlag(nuke.STARTLINE)

        self.addKnob(self.leadQCChoice)
        self.addKnob(self.sendqc_button)
        self.addKnob(nuke.Text_Knob("label2", "", "   "))
        self.addKnob(self.delivery_path)
        self.addKnob(self.send_shot_button)

        self.addKnob(nuke.Text_Knob("label2", "", "   "))
        # update group
        beginGroup = nuke.Tab_Knob('begin', 'Metadata Info', nuke.TABBEGINCLOSEDGROUP)
        self.addKnob(beginGroup)

        self.addKnob(self.info)

        endGroup = nuke.Tab_Knob('', None, nuke.TABENDGROUP)
        self.addKnob(endGroup)

        self.general_tab = nuke.Tab_Knob("replaceFootage", "Thay Đường Dẫn")
        self.addKnob(self.general_tab)

        # CREATE KNOBS
        self.nodeTypeChoice = nuke.Enumeration_Knob('node_type', 'Node', ['Write & Read', 'Read', 'Write'])
        self.searchStr = nuke.File_Knob('searchStr', 'Search for:')
        self.update = nuke.PyScript_Knob('update', 'Search')
        self.writeInfo = nuke.Multiline_Eval_String_Knob('writeInfo', 'Write Nodes Selected')
        self.writeInfo.setEnabled(False)
        self.readInfo = nuke.Multiline_Eval_String_Knob('readInfo', 'Read Nodes Selected')
        self.readInfo.setEnabled(False)
        self.replaceStr = nuke.File_Knob('replaceStr', 'Replace with:')
        self.replace = nuke.PyScript_Knob('replace', 'Replace')

        # ADD KNOBS
        self.addKnob(self.nodeTypeChoice)
        self.addKnob(self.searchStr)
        self.addKnob(self.update)
        self.addKnob(self.replaceStr)
        self.addKnob(self.replace)
        self.addKnob(self.writeInfo)
        self.addKnob(self.readInfo)

        #QC tab

        # self.general_tab = nuke.Tab_Knob("QCandDelivery", "QC & Giao Shot")
        # self.addKnob(self.general_tab)

    def build_lead_users_enum(self):
        choices = []

        for user in self.all_users:
            name = user['name']
            level = user['level'].lower()  # Lấy giá trị level của user

            if level == 'lead':  # Chỉ thêm vào danh sách nếu level là 'lead'
                choices.append(name)

        choices.reverse()
        # Cập nhật danh sách lựa chọn cho Enumeration_Knob
        self.leadQCChoice.setValues(choices)


    def send_clipboard(self):

        selected_nodes = nuke.selectedNodes()
        if not selected_nodes:
            nuke.message("Vui lòng chọn footage gốc và bản final để gửi link QC.")
            return

        # Lấy giá trị đã chọn từ self.leadQCChoice
        selected_lead = self.leadQCChoice.value()
        get_name_from_tcl =[]
        if not selected_lead:
            nuke.message(f"Vui lòng chọn lead qc")
            return

        # Lấy đối tượng người dùng từ lựa chọn
        selected_user = USER_COLLECTION.find_one({"name": selected_lead})
        if not selected_user:
            nuke.message("Không tìm thấy người dùng trong cơ sở dữ liệu")
            return

        if USER_COLLECTION.find_one({"hostname": HOSTNAME.upper()}) is None:
            nuke.message("Tên của bạn không có trong hệ thống, vui lòng liên hệ IT để cập nhật.")
            return

        now = datetime.now()

        # Tạo một file tạm để lưu mã TCL
        with tempfile.NamedTemporaryFile(delete=False, suffix=".nk") as temp_file:
            nuke.nodeCopy(temp_file.name)  # Sao chép các node đã chọn vào file tạm thời

        # Đọc mã TCL từ file tạm thời
        with open(temp_file.name, 'r') as file:
            script = file.read()

        # Thay đổi đường dẫn trong TCL script trước khi lưu vào MongoDB
        modified_script_lines = []
        for line in script.splitlines():
            if 'xpos' in line or 'ypos' in line:
                continue

            if 'file ' in line:  # Kiểm tra dòng chứa đường dẫn file
                file_path = line.split(' ')[-1].strip('"')
                shot_name = self.extract_shot_name(file_path)  # Lấy tên shot từ file_path
                get_name_from_tcl.append(shot_name)


                # Kiểm tra xem đường dẫn đã là một đường dẫn mạng (IP-based) hay chưa
                if not file_path.startswith("//"):
                    local_drive = os.path.splitdrive(file_path)[0]
                    if local_drive:  # Nếu có ổ đĩa, thì đây là đường dẫn cục bộ
                        network_prefix = f"//{IP}/{local_drive[0].lower()}{file_path[2:]}".replace("\\", "/")
                        modified_line = line.replace(file_path, network_prefix)
                    else:
                        # Nếu không có ổ đĩa và cũng không bắt đầu bằng IP, giữ nguyên đường dẫn
                        modified_line = line
                else:
                    # Đường dẫn đã có IP, không cần thay đổi
                    modified_line = line
                modified_script_lines.append(modified_line)
            else:
                modified_script_lines.append(line)

        modified_script = "\n".join(modified_script_lines)

        # print("Modified TCL Script to save:")
        # print(modified_script)

        # shotname = self.filename_enum.value()

        # metadata_node, metadata = self.get_metadata_for_shot(shotname)
        get_client = self.client_enum.value()



        if get_name_from_tcl and get_client:
            #shot_name_final = metadata["shot_name_delivery"]
            shot_name_final = get_name_from_tcl
            client = get_client
        else:
            shot_name_final = ""
            client = ""

        # Chỉ gửi tới người dùng được chọn từ leadQCChoice
        doc = dict()
        doc['sender'] = CURRENT_USER
        doc['hostname_sender'] = HOSTNAME
        doc['submitted_at'] = now
        doc['destination_user'] = selected_user['hostname'].upper()
        doc['shot_name_qc'] = shot_name_final
        doc['client'] = client
        doc['pasted'] = False
        doc['nuke_file'] = modified_script
        # doc['note'] = self.text_note_text_edit.toPlainText()
        result = CLIPBOARD_COLLECTION.insert_one(doc)

        # Kiểm tra nếu insert thành công
        if result.acknowledged:
            # Tạo hoặc cập nhật Text_Knob để thông báo gửi thành công
            if not hasattr(self, 'send_status_knob'):
                self.send_status_knob = nuke.Text_Knob("send_status", "Status:", "")
                self.addKnob(self.send_status_knob)

            self.send_status_knob.setValue(
                f"Gửi thành công tới {selected_lead} tại {now.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            self.send_status_knob.setValue( f"Gửi thất bại. Vui lòng thử lại.")


    def set_delivery_path(self):
        client = self.client_enum.value()  # Lấy giá trị của client từ Enumeration_Knob
        fixed_destination_path = get_client_path(client, client_csv_path)  # Lấy đường dẫn cố định từ file CSV
        today = datetime.today()
        folder_date = today.strftime('%Y%m%d')
        if client  == "Auto_London" or client == "Auto_Berlin" or client == "THE POST":
            shotname = self.filename_enum.value()
            parts = shotname.split("_")
            if parts:
                folder_show = parts[0]
                destination_folder_path = os.path.join(fixed_destination_path, folder_show, folder_date).replace("\\", "/")
        else:
            destination_folder_path = os.path.join(fixed_destination_path, folder_date).replace("\\", "/")

        self.delivery_path.setValue(destination_folder_path)

    def extract_shot_name(self, file_path):
        # Tách tên file từ đường dẫn
        file_name = os.path.basename(file_path)

        # Bỏ phần đuôi file (.####.exr) nếu có
        shot_name, _ = os.path.splitext(file_name)
        shot_name = re.sub(r'\.\d+$', '', shot_name)
        shot_name = re.sub(r'\.%\d+d$', '', shot_name)

        return shot_name

    def send_shot_to_fixed_path(self):
        # Đảm bảo rằng một hoặc nhiều node Read đã được chọn
        selected_nodes = nuke.selectedNodes('Read')
        if not selected_nodes:
            nuke.message("Không có node Read nào được chọn.")
            return

        # Xác định đường dẫn đến đích (thư mục theo ngày)
        destination_folder_path = self.delivery_path.value()

        try:
            if not os.path.exists(destination_folder_path):
                os.makedirs(destination_folder_path)

            def should_copy_file(src_file, dest_file):
                if not os.path.exists(dest_file):
                    return True

                src_stat = os.stat(src_file)
                dest_stat = os.stat(dest_file)

                # Kiểm tra ngày chỉnh sửa và kích thước tệp
                return src_stat.st_mtime > dest_stat.st_mtime or src_stat.st_size != dest_stat.st_size

            total_copied_files = 0

            # Xử lý cho nhiều node Read được chọn
            for node in selected_nodes:
                # Lấy đường dẫn file từ node
                file_path = node['file'].value()

                # Lấy đuôi mở rộng của tệp
                file_extension = os.path.splitext(file_path)[1].lower()

                # Chuyển đổi dấu gạch chéo xuôi thành dấu gạch chéo ngược
                file_path = file_path.replace("/", "\\")

                if '%' in file_path or '#' in file_path:
                    # Xử lý cho file sequence
                    directory_path = os.path.dirname(file_path)
                    folder_name = os.path.basename(directory_path)

                    # Đếm số lượng file cần sao chép
                    total_files = 0
                    for root, dirs, files in os.walk(directory_path):
                        total_files += len([f for f in files if f.endswith(file_extension)])

                    # Tạo ProgressTask
                    task = nuke.ProgressTask(f"Sending Shot - {folder_name}")
                    copied_files = 0

                    # Sao chép toàn bộ thư mục chứa file sequence
                    for root, dirs, files in os.walk(directory_path):
                        for file in files:
                            if file.endswith(file_extension):
                                src_file = os.path.join(root, file)
                                relative_path = os.path.relpath(src_file, directory_path)
                                dest_file = os.path.join(destination_folder_path, folder_name, relative_path)
                                dest_dir = os.path.dirname(dest_file)

                                if not os.path.exists(dest_dir):
                                    os.makedirs(dest_dir)

                                if should_copy_file(src_file, dest_file):
                                    shutil.copy2(src_file, dest_file)
                                    copied_files += 1
                                    total_copied_files += 1

                                # copied_files += 1

                                # Cập nhật thanh tiến trình
                                task.setProgress(int((copied_files / total_files) * 100))

                                if task.isCancelled():
                                    nuke.message("Quá trình gửi shot bị hủy.")
                                    return

                    # nuke.message(f"Thư mục đã được sao chép đến {destination_folder_path}")

                else:
                    # Xử lý nếu là file video (ví dụ: .mov hoặc .mp4)
                    if file_extension in ['.mov', '.mp4']:
                        dest_file = os.path.join(destination_folder_path, os.path.basename(file_path))

                        # Tạo ProgressTask
                        task = nuke.ProgressTask(f"Sending Shot - {os.path.basename(file_path)}")

                        if should_copy_file(file_path, dest_file):
                            shutil.copy2(file_path, dest_file)
                            task.setProgress(100)  # Vì chỉ có 1 file, set progress thành 100%
                            total_copied_files += 1
                            # nuke.message(f"File video đã được sao chép đến {destination_folder_path}")

                    else:
                        nuke.message("Định dạng file không được hỗ trợ.")

            if total_copied_files > 0:
                nuke.message(f"Đã up {total_copied_files} files lên {destination_folder_path}")
            else:
                nuke.message("Không có files nào đc up.")

        except PermissionError as e:
            nuke.message(f"Không thể tạo folder hoặc sao chép files: {str(e)}")
        except Exception as e:
            nuke.message(f"Lỗi khi sao chép folder: {str(e)}")


    def check_and_update_metadata(self):
        metadata_node = nuke.toNode("metadata_storage")
        if metadata_node:
            self.update_info()

    def save_metadata(self):
        selected_nodes = nuke.selectedNodes()
        if not selected_nodes:
            nuke.message("Chưa chọn footage hoặc footage không phải là node Read.")
            return

        for node in selected_nodes:
            if node.Class() == "Read":
                metadata = self.metadata_handler.get_metadata_from_node(node)
                self.metadata_handler.store_metadata(metadata)
                self.update_filename_enum()


    def update_filename_enum(self):
        metadata_node = nuke.toNode("metadata_storage")
        if metadata_node:
            existing_metadata = self.metadata_handler.load_existing_metadata(metadata_node)
            shotnames = [
                get_shot_name(filename)[1] for filename in existing_metadata.keys()
            ]
            self.filename_enum.setValues(shotnames[::-1])
        else:
            nuke.message("Không tìm thấy metadata, vui lòng import lại.")

    def load_metadata(self):
        metadata_node = nuke.toNode("metadata_storage")
        if not metadata_node:
            nuke.message("Không tìm thấy node 'metadata_storage' trong Nuke script.")
            return

        existing_metadata = self.metadata_handler.load_existing_metadata(metadata_node)
        shotname = self.filename_enum.value() if self.filename_enum.value() else None

        if shotname:
            input_filename = next(
                (
                    filename
                    for filename in existing_metadata.keys()
                    if get_shot_name(filename)[1] == shotname
                ),
                None,
            )

            if input_filename and input_filename in existing_metadata:
                metadata = existing_metadata[input_filename]
                self._create_write_node(metadata)
            else:
                nuke.message(f"Không tìm thấy metadata cho shot: {shotname}")

    def knobChanged(self, knob):
        if knob is self.save_button:
            self.info_text = []
            self.version_input.setValue(1)
            self.save_metadata()
            self.client_enum.value()
            self.update_info()
            self.update_info_metadata()
        elif knob is self.load_button:
            self.load_metadata()
            # self.update_info()
        elif knob is self.filename_enum:
            self.info_text = []
            self.update_info()
            self.update_info_metadata()
        elif knob is self.delete_button:
            self.delete_metadata_storage()
            self.reset_form_to_initial_state()
        elif knob is self.save_nuke_button:
            self.save_with_dialog()
        elif knob in [self.client_enum, self.type_enum, self.version_input, self.path_input]:
            self.info_text = []
            self.update_path_and_shot_name()
            self.update_info_metadata()
            self.set_delivery_path()
        if knob in (self.update, self.searchStr, self.nodeTypeChoice):
            self.perform_update()
        elif knob is self.replace and (self.writeMatches is not None or self.readMatches is not None):
            self.perform_replace()

        if knob is self.sendqc_button:
            self.send_clipboard()
        elif knob is self.send_shot_button:
            self.send_shot_to_fixed_path()

    def save_with_dialog(self):
        # Fetch metadata for the current shot
        shotname = self.filename_enum.value()
        metadata_node, metadata = self.get_metadata_for_shot(shotname)

        if metadata:
            parent_folder = metadata.get("parent_folder", "")
            shot_name_delivery = metadata.get("shot_name_delivery", "default_shot")

            p = nuke.Panel("Save File")
            p.addFilenameSearch("Select Path", parent_folder)
            p.addSingleLineInput("File Name", shot_name_delivery)
            # p.setMinimumSize(600, 100)  # Adjust the width and height as needed
            # p.showModalDialog()

            if p.show():
                selected_path = p.value("Select Path")
                delivery_name = p.value("File Name")
                if delivery_name and selected_path:
                    self.save_nuke_file(selected_path, delivery_name)

        else:
            nuke.message("Vui lòng import metadata trước khi save")

    def save_nuke_file(self, selected_path, delivery_name):
        # Ensure the delivery name ends with '.nk'
        if not delivery_name.endswith(".nk"):
            delivery_name += ".nk"

        # Combine the selected path and the delivery name to create the full file path
        full_file_path = os.path.join(selected_path, delivery_name)

        # Set the script name to the delivery name before saving
        nuke.root()["name"].setValue(full_file_path)
        nuke.scriptSaveAs(full_file_path)

    def update_path_and_shot_name(self):
        shotname = self.filename_enum.value()
        metadata_node = nuke.toNode("metadata_storage")
        if shotname and metadata_node and metadata_node.knob("metadata").value():
            metadata_str = metadata_node["metadata"].value()
            existing_metadata = json.loads(metadata_str) if metadata_str else {}

            input_filename = next(
                (
                    filename
                    for filename in existing_metadata.keys()
                    if get_shot_name(filename)[1] == shotname
                ),
                None,
            )

            if input_filename and input_filename in existing_metadata:
                metadata = existing_metadata[input_filename]

                client = self.client_enum.value()
                task_info = self.client_tasks.get(
                    client, {"task_name": "Unknow Task", "reduce_word": None}
                )
                task_name = task_info["task_name"]
                reduce_word = task_info["reduce_word"]
                type_selected = self.type_enum.value()
                version = self.version_input.value()
                set_version = task_info["version"]
                type_name = task_name if type_selected == "FINAL" else type_selected
                path_render, shot_name, parent_folder = generate_render_path(
                    metadata,
                    type_name,
                    version,
                    reduce_word,
                    client,
                    self.path_input.value(),
                    set_version
                )
                # print(f"from update_path_name => {path_render, shot_name, parent_folder}")
                if path_render != metadata['path_render_delivery']:
                    metadata['path_render_delivery'] = path_render
                # metadata['path_render_delivery'] = path_render
                metadata['shot_name_delivery'] = shot_name
                metadata['version'] = version
                metadata['client'] = client
                metadata['parent_folder'] = parent_folder
                self.metadata_handler.store_metadata(metadata)
            else:
                nuke.message(f"Không tìm thấy metadata cho shot: {shotname}")
        else:
            self.info.setValue("Không tìm thấy metadata cho shot được chọn.")

    def update_info(self):
        # self.info_text = []
        shotname = self.filename_enum.value()
        metadata_node, metadata = self.get_metadata_for_shot(shotname)

        if metadata_node and metadata:
            self.update_ui_elements_from_metadata(metadata)
        else:
            self.info.setValue("Không tìm thấy metadata cho shot được chọn.")

    def update_info_metadata(self):
        self.info_text = []
        shotname = self.filename_enum.value()

        metadata_node, metadata = self.get_metadata_for_shot(shotname)

        if metadata_node and metadata:
            shot_name_final = metadata["shotname"]
            first_frame = metadata["first_frame"]
            last_frame = metadata["last_frame"]
            file_type = metadata["ext"].lstrip(".")
            colorspace = metadata["colorspace"]
            codec = metadata.get("codec", None) if file_type == "mov" else None
            compression = metadata.get("compression", None) if file_type == "exr" else None
            datatype = metadata["datatype"]
            fps = metadata["mov64_fps"] if file_type == "mov" else None

            new_info = [
                f"Shot name: {shot_name_final} -- {file_type}",
                f"Frame range: {first_frame} - {last_frame}",
                f"Colorspace: {colorspace}",
            ]

            if file_type == "mov":
                new_info.append(f"Codec: {codec}")
                new_info.append(f"FPS: {fps}")

            if file_type == "exr":
                new_info.append(f"Compression: {compression}")
                new_info.append(f"Data type: {datatype}")

            new_info.append(f"Source folder: {metadata['path_src']}")

            # # Only update these UI elements if needed
            # self.update_ui_elements_from_metadata(metadata)

            self.info_text.append(f"Render Path: {metadata.get('path_render_delivery', '')}")
            self.info_text.append(f"Shot Name Delivery: {metadata.get('shot_name_delivery', '')}")

            # Add additional info to the info_text
            self.info_text.extend(info for info in new_info if info not in self.info_text)

            # Update the info field with the new information
            self.info.setValue("\n".join(self.info_text))
        else:
            self.info.setValue("Không tìm thấy metadata cho shot được chọn.")

    def update_ui_elements_from_metadata(self, metadata):
        version = metadata.get("version")
        path_input = metadata.get("parent_folder", "")
        client = metadata.get("client", "default")

        if self.path_input.value() != path_input:
            self.path_input.setValue(path_input)
        if self.version_input.value() != int(version):
            self.version_input.setValue(int(version))
        if self.client_enum.value() != client:
            self.client_enum.setValue(client)

    def get_metadata_for_shot(self, shotname):
        metadata_node = nuke.toNode("metadata_storage")

        if not shotname or not metadata_node:
            return None, None

        metadata_str = metadata_node["metadata"].value()
        existing_metadata = json.loads(metadata_str) if metadata_str else {}

        input_filename = next(
            (
                filename
                for filename in existing_metadata.keys()
                if get_shot_name(filename)[1] == shotname
            ),
            None,
        )

        # Kết hợp kiểm tra và lấy metadata
        metadata = existing_metadata.get(input_filename) if input_filename else None

        return metadata_node, metadata

    def _create_write_node(self, metadata):
        try:
            if metadata:
                write_node = self.node_configurator.initialize_write_node(metadata)
                self.node_configurator.configure_write_node(
                    write_node, metadata, self.codec_info
                )
                render_path_final = metadata["path_render_delivery"]
                write_node["file"].setValue(render_path_final)

        except Exception as e:
            nuke.message(f"Error creating Write node: {str(e)}")

    def delete_metadata_storage(self):
        metadata_node = nuke.toNode("metadata_storage")
        if metadata_node:
            nuke.delete(metadata_node)
            nuke.message("Metadata storage node has been deleted.")
        else:
            nuke.message("Metadata storage node does not exist.")

    def reset_form_to_initial_state(self):
        self.path_input.setValue("")
        self.version_input.setValue(1)
        self.client_enum.setValue("default")
        self.type_enum.setValue("FINAL")
        self.filename_enum.setValues([])
        self.info.setValue("")
        self.info_text = []

    def search(self, nodes, node_type, search_string):
        writeMatches, writeKnobMatches = search(search_string, nodes, 'Write')
        readMatches, readKnobMatches = search(search_string, nodes, 'Read')

        if node_type in ['Write & Read', 'Write']:
            writeNodes = [n.name() for n in writeMatches]
            writeInfoStr = '%s Write nodes found:\n%s' % (len(writeNodes), ', '.join(writeNodes))
            self.writeInfo.setValue(writeInfoStr)
        else:
            self.writeInfo.setValue('')

        if node_type in ['Write & Read', 'Read']:
            readNodes = [n.name() for n in readMatches]
            readInfoStr = '%s Read nodes found:\n%s' % (len(readNodes), ', '.join(readNodes))
            self.readInfo.setValue(readInfoStr)
        else:
            self.readInfo.setValue('')

        return writeKnobMatches, readKnobMatches

    def perform_update(self):
        selected_nodes = nuke.selectedNodes()
        nodes_to_search = selected_nodes if len(selected_nodes) > 1 else nuke.allNodes()

        node_type = self.nodeTypeChoice.value()
        search_string = self.searchStr.value().replace('\\', '/')

        if node_type == 'Write & Read':
            self.writeMatches, self.readMatches = self.search(nodes_to_search, node_type, search_string)
        elif node_type == 'Write':
            self.writeMatches, self.readMatches = self.search(nodes_to_search, 'Write', search_string)
            self.readMatches = []
        elif node_type == 'Read':
            self.writeMatches, self.readMatches = self.search(nodes_to_search, 'Read', search_string)
            self.writeMatches = []

    def perform_replace(self):
        search_string = self.searchStr.value().replace('\\', '/')
        replace_string = self.replaceStr.value().replace('\\', '/')

        total_replacements = 0

        if self.writeMatches:
            for k in self.writeMatches:
                newStr = re.sub(re.escape(search_string), replace_string, k.value())
                if newStr != k.value():
                    total_replacements += 1
                k.setValue(newStr)

        if self.readMatches:
            for k in self.readMatches:
                newStr = re.sub(re.escape(search_string), replace_string, k.value())
                if newStr != k.value():
                    total_replacements += 1
                k.setValue(newStr)

def search(searchstr, nodes, node_type):
    if node_type == 'Write':
        targetNodes = [n for n in nodes if n.Class() == 'Write']
    elif node_type == 'Read':
        targetNodes = [n for n in nodes if n.Class() == 'Read']
    else:
        targetNodes = [n for n in nodes if n.Class() in ['Write', 'Read']]

    nodeMatches = set()
    knobMatches = []

    for node in targetNodes:
        for knobName in ['file', 'proxy']:
            if node_has_knob_with_name(node, knobName):
                if find_node(searchstr, node[knobName]):
                    nodeMatches.add(node)
                    knobMatches.append(node[knobName])

    return list(nodeMatches), knobMatches

def node_has_knob_with_name(node, knobName):
    try:
        node[knobName]
        return True
    except KeyError:
        return False

def find_node(searchstr, knob):
    return searchstr in knob.value()

def reduce_path_by_one_unit(path, ext):
    if ext in [".exr", ".dpx", ".jpg", ".png"]:
        path_parts = path.split("/")
        path_parts = [
            part for part in path_parts if not re.match(r"^\d+x\d+$", part) and part != "exr-comp" and part != "EXR"
        ]
        if len(path_parts) > 2:
            path_parts.pop()
        return "/".join(path_parts)
    else:
        return path
