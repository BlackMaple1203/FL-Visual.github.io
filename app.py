import os
from flask import Flask, request, render_template, redirect, url_for, session, jsonify
import shutil
import threading
import time
from datetime import datetime
import queue
import io
import sys
import builtins

# 从您现有的脚本导入训练函数
# 确保 src 目录在 Python 路径中，或者调整导入方式
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
from federated_training import train_federated_model

app = Flask(__name__)
app.secret_key = "your_secret_key"  # 请更改为强密钥
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# 模拟用户数据库
users = {
    "server": {"password": "1", "role": "server"},
    "client1": {"password": "1", "role": "client"},
    "client2": {"password": "1", "role": "client"},
    "client3": {"password": "1", "role": "client"},
}

# 存储客户端文件上传状态和数据路径
# 这个变量将在initialize_client_data_status()函数中初始化
client_data_status = {}

# 全局训练状态和日志
training_status = {
    "is_training": False,
    "current_round": 0,
    "total_rounds": 0,
    "active_clients": 0,
    "start_time": None,
    "end_time": None,
    "progress": 0,
}

# 设置全局变量，让训练函数能够访问
builtins.app_training_status = training_status

# 日志队列
server_logs = queue.Queue(maxsize=1000)
training_logs = queue.Queue(maxsize=1000)

# 数据变化跟踪，用于触发页面刷新
data_change_timestamp = None


def add_server_log(message):
    """添加服务器日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    try:
        server_logs.put_nowait(log_entry)
    except queue.Full:
        # 如果队列满了，删除最旧的日志
        try:
            server_logs.get_nowait()
            server_logs.put_nowait(log_entry)
        except queue.Empty:
            pass


def add_training_log(message):
    """添加训练日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    try:
        training_logs.put_nowait(log_entry)
    except queue.Full:
        # 如果队列满了，删除最旧的日志
        try:
            training_logs.get_nowait()
            training_logs.put_nowait(log_entry)
        except queue.Empty:
            pass


def get_logs_list(log_queue):
    """获取日志列表"""
    logs = []
    temp_logs = []

    # 取出所有日志
    while not log_queue.empty():
        try:
            log = log_queue.get_nowait()
            temp_logs.append(log)
        except queue.Empty:
            break

    # 保留最新的100条日志
    recent_logs = temp_logs[-100:] if len(temp_logs) > 100 else temp_logs

    # 重新放回队列
    for log in recent_logs:
        try:
            log_queue.put_nowait(log)
        except queue.Full:
            break

    return recent_logs


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username in users and users[username]["password"] == password:
            session["username"] = username
            session["role"] = users[username]["role"]
            add_server_log(f"用户 {username} ({users[username]['role']}) 登录成功")
            if users[username]["role"] == "server":
                return redirect(url_for("server_dashboard"))
            else:
                # 初始化客户端数据状态（如果尚不存在）
                if username not in client_data_status:
                    client_data_status[username] = {
                        "uploaded": False,
                        "data_path": None,
                        "last_login": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    }
                else:
                    client_data_status[username][
                        "last_login"
                    ] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                return redirect(url_for("client_dashboard"))
        add_server_log(f"用户 {username} 登录失败 - 无效凭据")
        # 对于AJAX请求，返回错误信息
        if (
            request.is_json
            or request.headers.get("Content-Type")
            == "application/x-www-form-urlencoded"
        ):
            return "无效的凭据", 400
        return redirect(url_for("login", error="1"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    username = session.get("username", "未知用户")
    add_server_log(f"用户 {username} 登出")
    session.pop("username", None)
    session.pop("role", None)
    return redirect(url_for("login"))


@app.route("/client/dashboard", methods=["GET"])
def client_dashboard():
    if "username" not in session or session["role"] != "client":
        return redirect(url_for("login"))

    status = client_data_status.get(
        session["username"], {"uploaded": False, "data_path": None}
    )
    return render_template(
        "client_dashboard.html", username=session["username"], status=status
    )  # 您需要创建此HTML文件


@app.route("/client/upload", methods=["POST"])
def upload_file():
    if "username" not in session or session["role"] != "client":
        return jsonify({"error": "未授权"}), 403

    username = session["username"]

    # 支持多文件上传 - 检查是否有文件
    uploaded_files = request.files.getlist("files")
    if not uploaded_files or len(uploaded_files) == 0:
        return jsonify({"error": "未选择文件"}), 400

    client_folder_name = f"{username}_data"
    client_upload_path = os.path.join(UPLOAD_FOLDER, client_folder_name)

    if not os.path.exists(client_upload_path):
        os.makedirs(client_upload_path)

    uploaded_count = 0
    mhd_count = 0
    raw_count = 0
    uploaded_filenames = []

    # 处理每个上传的文件
    for file in uploaded_files:
        if file.filename == "":
            continue

        filename = file.filename
        file_path = os.path.join(client_upload_path, filename)

        # 如果文件已存在，生成新的文件名
        counter = 1
        base_name, ext = os.path.splitext(filename)
        while os.path.exists(file_path):
            new_filename = f"{base_name}_{counter}{ext}"
            file_path = os.path.join(client_upload_path, new_filename)
            filename = new_filename
            counter += 1

        file.save(file_path)
        uploaded_filenames.append(filename)
        uploaded_count += 1

        # 统计文件类型
        if filename.lower().endswith(".mhd"):
            mhd_count += 1
        elif filename.lower().endswith(".raw"):
            raw_count += 1

    if uploaded_count == 0:
        return jsonify({"error": "没有成功上传文件"}), 400

    # 计算总文件数（包括之前上传的）
    all_files = os.listdir(client_upload_path)
    total_mhd = len([f for f in all_files if f.lower().endswith(".mhd")])
    total_raw = len([f for f in all_files if f.lower().endswith(".raw")])
    total_files = len(all_files)

    # 更新客户端状态
    client_data_status[username] = {
        "uploaded": True,
        "data_path": client_upload_path,
        "upload_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "file_count": total_files,
        "mhd_count": total_mhd,
        "raw_count": total_raw,
        "file_pairs": min(total_mhd, total_raw),  # 有效的文件对数
        "last_login": client_data_status.get(username, {}).get("last_login", "未知"),
    }

    add_server_log(
        f"客户端 {username} 上传 {uploaded_count} 个文件: {', '.join(uploaded_filenames[:3])}{('...' if len(uploaded_filenames) > 3 else '')}"
    )

    # 更新数据变化时间戳，用于触发页面刷新
    global data_change_timestamp
    data_change_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return jsonify(
        {
            "message": f"成功上传 {uploaded_count} 个文件",
            "data_path": client_upload_path,
            "uploaded_files": uploaded_filenames,
            "total_files": total_files,
            "mhd_count": total_mhd,
            "raw_count": total_raw,
            "file_pairs": min(total_mhd, total_raw),
        }
    )


@app.route("/server/dashboard", methods=["GET"])
def server_dashboard():
    if "username" not in session or session["role"] != "server":
        return redirect(url_for("login"))

    # 获取已登录的客户端（这是一个简化版本，实际应用中可能需要更复杂的会话管理）
    # 这里我们假设所有定义在users字典中的客户端都是潜在的客户端
    active_clients_info = []
    for uname, uinfo in users.items():
        if uinfo["role"] == "client":
            status = client_data_status.get(
                uname,
                {
                    "uploaded": False,
                    "data_path": None,
                    "last_login": "从未登录",
                    "upload_time": "从未上传",
                    "file_count": 0,
                },
            )
            active_clients_info.append(
                {
                    "username": uname,
                    "logged_in": True,  # 简化：假设如果存在于users就可能登录
                    "file_uploaded": status["uploaded"],
                    "last_login": status.get("last_login", "从未登录"),
                    "upload_time": status.get("upload_time", "从未上传"),
                    "file_count": status.get("file_count", 0),
                    "data_path": status.get("data_path", "无"),
                }
            )

    return render_template(
        "server_dashboard.html",
        clients=active_clients_info,
        training_status=training_status,
    )  # 您需要创建此HTML文件


@app.route("/server/start_training", methods=["POST"])
def start_training():
    if "username" not in session or session["role"] != "server":
        return jsonify({"error": "未授权"}), 403

    if training_status["is_training"]:
        return jsonify({"error": "训练正在进行中"}), 400

    client_paths_for_training = []
    for client_name, status in client_data_status.items():
        if status.get("uploaded") and status.get("data_path"):
            client_paths_for_training.append(status["data_path"])

    if not client_paths_for_training:
        add_server_log("训练启动失败 - 没有客户端上传数据")
        return jsonify({"error": "没有客户端上传数据用于训练"}), 400

    num_active_clients = len(client_paths_for_training)

    # 更新训练状态
    training_status.update(
        {
            "is_training": True,
            "current_round": 0,
            "total_rounds": 5,
            "active_clients": num_active_clients,
            "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": None,
            "progress": 0,
        }
    )

    add_server_log(f"开始联邦学习训练 - {num_active_clients} 个客户端参与")
    add_training_log(f"训练初始化 - 客户端数据目录: {client_paths_for_training}")

    def run_training():
        try:
            # 不再重定向stdout，让print只在终端输出
            # 保持原始的stdout，不进行任何重定向

            add_training_log("正在启动联邦学习训练...")
            add_training_log(f"参与训练的客户端数量: {num_active_clients}")
            add_training_log(f"客户端数据路径: {client_paths_for_training}")

            coordinator = train_federated_model(
                num_clients=num_active_clients,
                global_rounds=5,
                local_epochs=2,
                client_data_dirs=client_paths_for_training,
            )

            # 更新训练状态
            training_status.update(
                {
                    "is_training": False,
                    "current_round": 5,
                    "end_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "progress": 100,
                }
            )

            if coordinator:
                add_server_log("联邦学习训练成功完成")
                add_training_log("训练完成，模型已保存")
            else:
                add_server_log("联邦学习训练失败")
                add_training_log("训练失败 - 协调器未成功初始化")

        except Exception as e:
            training_status.update(
                {
                    "is_training": False,
                    "end_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            )
            add_server_log(f"训练过程中发生错误: {e}")
            add_training_log(f"训练异常终止: {str(e)}")

    # 在后台线程中运行训练
    training_thread = threading.Thread(target=run_training)
    training_thread.daemon = True
    training_thread.start()

    return jsonify({"message": "训练已启动，请查看训练日志获取进度"})


@app.route("/api/server/status", methods=["GET"])
def get_server_status():
    """获取服务器状态API"""
    if "username" not in session or session["role"] != "server":
        return jsonify({"error": "未授权"}), 403

    # 添加调试输出
    # print(f"[DEBUG] 当前训练状态: {training_status}")

    client_count = len([c for c in client_data_status.values() if c.get("uploaded")])
    total_clients = len([u for u, info in users.items() if info["role"] == "client"])

    response_data = {
        "training_status": training_status,
        "client_count": client_count,
        "total_clients": total_clients,
        "server_logs": get_logs_list(server_logs),
        "training_logs": get_logs_list(training_logs),
        "data_change_timestamp": data_change_timestamp,  # 添加数据变化时间戳
    }

    # print(f"[DEBUG] 返回状态数据: {response_data}")

    return jsonify(response_data)


@app.route("/api/server/logs", methods=["GET"])
def get_logs():
    """获取日志API"""
    if "username" not in session or session["role"] != "server":
        return jsonify({"error": "未授权"}), 403

    log_type = request.args.get("type", "server")

    if log_type == "training":
        logs = get_logs_list(training_logs)
    else:
        logs = get_logs_list(server_logs)

    return jsonify({"logs": logs})


# 自动检测和初始化客户端数据状态
def initialize_client_data_status():
    """自动检测uploads目录中的客户端数据并初始化状态"""
    global client_data_status

    print("正在检测客户端数据...")

    for username in users:
        if users[username]["role"] == "client":
            client_data_dir = os.path.join(UPLOAD_FOLDER, f"{username}_data")

            # 检查客户端数据目录是否存在
            if os.path.exists(client_data_dir):
                # 检查是否有有效的数据文件
                files = os.listdir(client_data_dir)
                mhd_files = [f for f in files if f.endswith(".mhd")]
                raw_files = [f for f in files if f.endswith(".raw")]

                if mhd_files and raw_files:
                    client_data_status[username] = {
                        "uploaded": True,
                        "data_path": client_data_dir,
                        "last_login": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "file_count": len(mhd_files),
                    }
                    print(f"✅ 检测到 {username} 的数据: {len(mhd_files)} 个文件")
                else:
                    print(f"⚠️ {username} 的数据目录存在但无有效数据文件")
            else:
                print(f"❌ {username} 的数据目录不存在: {client_data_dir}")


# 在应用启动时初始化客户端数据状态
initialize_client_data_status()

if __name__ == "__main__":
    # 添加一些初始日志
    add_server_log("服务器启动")
    add_server_log("等待客户端连接和上传数据")

    app.run(debug=True, port=5050)
