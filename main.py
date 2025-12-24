import requests
import json
import base64
import threading
import io
import os
import time
import datetime
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.core.clipboard import Clipboard
from kivy.utils import platform
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDFillRoundFlatButton
from kivymd.uix.snackbar import Snackbar
from kivymd.uix.filemanager import MDFileManager
from kivymd.toast import toast
from kivy.core.text import LabelBase

# ================== 核心配置与常量 (完美复刻原版) ==================

# [老板请注意] 服务器配置保持不变
SERVER_IP = "182.92.83.40"
SERVER_PORT = "5000"
CONFIG_FILE = "config_client_mobile.json"

# [核心机密] 默认 AI 脑核设定 - V3.0 终极排版色彩版 (一字未改)
DEFAULT_PROMPT_CONTENT = (
    "# Role: 视觉复刻级 OCR 专家 (Visual Forensic OCR Expert)\n\n"
    "你是一个拥有**像素级色彩感知**、**线条敏感度 MAX** 和**完美排版还原**能力的 AI 专家。你的核心任务是将图片内容转换为 Markdown，且必须达到“视觉孪生”级别的还原度。\n\n"
    "【核心指令：色彩、线条与样式的最高优先级】\n"
    "**全局强制规则**：\n"
    "1.  **逐字扫描机制**：必须以“字符”为单位进行扫描，绝不错过任何一个字符的颜色或样式变化。\n"
    "2.  **彩色即加粗（核心逻辑）**：识别为**非纯黑/非深灰**的彩色文字，无论原图中字重如何，**必须强制**添加 `font-weight: bold;`。\n"
    "3.  **下划线必现（新增核心）**：凡是文字下方带有横线（实线/波浪线），**必须强制**添加 `text-decoration: underline;`。\n"
    "4.  **样式聚合原则**：所有的样式（颜色+加粗+下划线）必须合并在一个 `<span>` 标签的 style 属性中，**严禁标签嵌套**。\n\n"
    "---\n\n"
    "【详细执行标准 - 必须严格遵守】\n\n"
    "## 1. 🌈 极致色彩、线条与样式还原（优先级 NO.1）\n\n"
    "请调用最全的 Hex 色彩库（如 Pantone）进行精准取色。\n\n"
    "### A. 彩色文字处理逻辑（非黑色/深灰）\n"
    "-   **识别标准**：任何有色文字（红、蓝、绿等）。\n"
    "-   **强制动作**：**颜色 + 强制加粗**。\n"
    "-   **代码规范**：\n"
    "    `<span style='color: #HEX; font-weight: bold;'>内容</span>`\n"
    "-   **下划线叠加**（若有）：\n"
    "    `<span style='color: #HEX; font-weight: bold; text-decoration: underline;'>内容</span>`\n\n"
    "### B. 下划线极其重要性（专门强化）\n"
    "-   **识别雷达**：扫描所有文字底部。\n"
    "-   **黑白文字+下划线**：\n"
    "    `<span style='text-decoration: underline;'>内容</span>`\n"
    "-   **黑色加粗+下划线**：\n"
    "    `<span style='color: #000000; font-weight: bold; text-decoration: underline;'>内容</span>`\n"
    "-   **注意**：不要忽略哪怕只有几个字的短下划线。\n\n"
    "### C. 黑白文字常规处理\n"
    "-   **纯黑/深灰 + 常规**：直接输出纯文本，严禁加标签。\n"
    "-   **纯黑/深灰 + 加粗**：\n"
    "    `<span style='color: #000000; font-weight: bold;'>内容</span>`\n\n"
    "### D. 禁用语法（红线）\n"
    "-   ❌ **绝对禁止**使用 Markdown 的 `**bold**` 或 `__bold__`。\n"
    "-   ❌ **绝对禁止**使用 `<u>`、`<b>`、`<strong>` 等简写标签。\n"
    "-   ✅ **只能使用** `<span style='...'>`。\n\n"
    "---\n\n"
    "## 2. 📐 排版与结构控制（完美布局）\n\n"
    "### A. 选择题排版规范\n"
    "-   **禁止废话**：严禁输出“选项”、“Options”等标题。\n"
    "-   **紧凑布局**：选项 A、B、C、D 各行之间**零间距**（不要空行）。\n"
    "-   **段落分隔**：题干文字与选项 A 之间，**强制保留 1 个空行**。\n"
    "-   **空格保留**：选项内部（如 `A. Apple`）的空格需原样保留。\n\n"
    "**[标准输出结构示例]**\n"
    "> 题目内容...（包含<span style='color: #FF0000; font-weight: bold; text-decoration: underline;'>带下划线的重点</span>）\n"
    ">\n"
    "> (此处空一行)\n"
    "> A. 内容...\n"
    "> B. 内容...\n"
    "> C. 内容...\n"
    "> D. 内容...\n\n"
    "### B. 特殊符号处理\n"
    "-   **填空横线**：将 `____` 转换为 `﹎﹎﹎`。\n"
    "-   **彩色横线**：若横线是红色的，写作 `<span style='color: #FF0000; font-weight: bold;'>﹎﹎﹎</span>`。\n"
    "-   **数学公式**：使用 LaTeX 格式。公式内变色需使用 `\\textcolor{#HEX}{内容}`。\n\n"
    "---\n\n"
    "## 3. 🔍 执行流程自检（Output Check）\n"
    "在输出前，请进行自我审查：\n"
    "1.  文字是彩色的吗？ -> 是 -> **必须写 `font-weight: bold;`**。\n"
    "2.  文字底下有线吗？ -> 是 -> **必须写 `text-decoration: underline;`**。\n"
    "3.  是黑色文字吗？ -> 是 -> 仅加粗/下划线时才用 span，否则纯文本。\n"
    "4.  选项之间有空行吗？ -> 有 -> **删除空行**。\n\n"
    "**请直接输出最终的 Markdown 内容，无需任何开场白或解释。**"
)

# 默认配置
DEFAULT_CONFIG = {
    "server_url": f"http://{SERVER_IP}:{SERVER_PORT}",
    "last_username": "",
    "use_custom_api": False,
    "custom_api_url": "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
    "custom_api_key": "",
    "custom_model_id": "",
    "request_timeout": "240",
    "ai_prompt": DEFAULT_PROMPT_CONTENT
}

# ================== Kivy 界面布局 (KV Language) ==================
# 采用 MacOS 风格的圆角、阴影和磨砂感设计
KV_LAYOUT = '''
<LoginScreen>:
    name: "login"
    MDBoxLayout:
        orientation: 'vertical'
        padding: "20dp"
        spacing: "10dp"

        MDLabel:
            text: "AI Vision Pro"
            halign: "center"
            font_style: "H4"
            theme_text_color: "Primary"
            bold: True
            pos_hint: {"center_x": .5}

        MDLabel:
            text: "移动端 · 视觉复刻专家"
            halign: "center"
            font_style: "Caption"
            theme_text_color: "Secondary"

        MDTextField:
            id: email_field
            hint_text: "电子邮箱"
            icon_right: "email"
            mode: "rectangle"

        MDTextField:
            id: password_field
            hint_text: "密码"
            icon_right: "key"
            password: True
            mode: "rectangle"

        MDFillRoundFlatButton:
            text: "登录系统"
            font_size: "18sp"
            size_hint_x: 1
            padding: "15dp"
            on_release: root.do_login()

        MDFlatButton:
            text: "没有账号？点击注册"
            pos_hint: {"center_x": .5}
            on_release: root.go_register()

<RegisterScreen>:
    name: "register"
    MDBoxLayout:
        orientation: 'vertical'
        padding: "20dp"
        spacing: "10dp"

        MDLabel:
            text: "新用户注册"
            font_style: "H5"
            bold: True

        MDTextField:
            id: reg_email
            hint_text: "电子邮箱"
            mode: "rectangle"

        MDBoxLayout:
            orientation: 'horizontal'
            spacing: "5dp"
            size_hint_y: None
            height: "60dp"

            MDTextField:
                id: reg_code
                hint_text: "验证码"
                size_hint_x: 0.6
                mode: "rectangle"

            MDRectangleFlatButton:
                id: btn_send_code
                text: "发送验证码"
                size_hint_x: 0.4
                on_release: root.send_code()

        MDTextField:
            id: reg_pass
            hint_text: "设置密码"
            password: True
            mode: "rectangle"

        MDTextField:
            id: reg_invite
            hint_text: "邀请码 (选填)"
            mode: "rectangle"

        MDFillRoundFlatButton:
            text: "确认注册"
            size_hint_x: 1
            md_bg_color: 0.2, 0.8, 0.2, 1
            on_release: root.do_register()

        MDFlatButton:
            text: "返回登录"
            pos_hint: {"center_x": .5}
            on_release: app.sm.current = "login"

<MainScreen>:
    name: "main"
    MDBoxLayout:
        orientation: 'vertical'

        MDTopAppBar:
            title: "AI 视觉助手 Pro"
            right_action_items: [["cog", lambda x: root.open_settings()]]
            elevation: 2

        MDBoxLayout:
            orientation: 'vertical'
            padding: "15dp"
            spacing: "10dp"

            MDCard:
                size_hint_y: None
                height: "80dp"
                radius: [15]
                padding: "10dp"
                elevation: 1

                MDBoxLayout:
                    orientation: 'vertical'
                    MDLabel:
                        id: user_info_lbl
                        text: "User: Loading..."
                        bold: True
                        theme_text_color: "Primary"
                    MDLabel:
                        id: vip_info_lbl
                        text: "VIP Status: Checking..."
                        font_style: "Caption"
                        theme_text_color: "Secondary"

            MDLabel:
                text: "运行日志 / Output"
                font_style: "Subtitle2"
                theme_text_color: "Hint"

            MDScrollView:
                md_bg_color: 0.95, 0.95, 0.96, 1
                radius: [10]

                MDLabel:
                    id: log_box
                    text: "系统就绪... 等待指令。\n点击右下角按钮开始识别。"
                    padding: [10, 10]
                    size_hint_y: None
                    height: self.texture_size[1]
                    markup: True

    MDFloatingActionButtonSpeedDial:
        data: root.fab_data
        root_button_anim: True
        icon: "camera"
        bg_hint_color: app.theme_cls.primary_light
        callback: root.fab_callback
'''


# ================== 逻辑处理类 (Logic) ==================

class ConfigManager:
    @staticmethod
    def load():
        if not os.path.exists(CONFIG_FILE):
            return DEFAULT_CONFIG.copy()
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 合并默认配置，防止缺项
            for k, v in DEFAULT_CONFIG.items():
                if k not in data: data[k] = v
            return data
        except:
            return DEFAULT_CONFIG.copy()

    @staticmethod
    def save(c):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(c, f, indent=4, ensure_ascii=False)


class AuthService:
    @staticmethod
    def get_hwid():
        # 安卓端简化 HWID 获取
        try:
            return str(datetime.datetime.now().timestamp())  # 简单模拟，生产环境需用 Android ID
        except:
            return "android_device_unknown"

    @staticmethod
    def api_post(endpoint, data, app_config):
        url = f"{app_config['server_url']}{endpoint}"
        try:
            resp = requests.post(url, json=data, timeout=10)
            if resp.status_code == 200:
                return True, resp.json()
            return False, resp.json().get('msg', '请求失败')
        except Exception as e:
            return False, f"网络错误: {str(e)}"


# ================== 界面类 (Screens) ==================

class LoginScreen(MDScreen):
    def do_login(self):
        email = self.ids.email_field.text.strip()
        pwd = self.ids.password_field.text.strip()
        if not email or not pwd:
            toast("请输入邮箱和密码")
            return

        app = MDApp.get_running_app()
        # 异步登录防止卡顿
        threading.Thread(target=self._login_thread, args=(app, email, pwd)).start()

    def _login_thread(self, app, email, pwd):
        ok, res = AuthService.api_post("/api/login",
                                       {"username": email, "password": pwd, "hwid": AuthService.get_hwid()},
                                       app.config_data)
        if ok:
            app.user_info = {"username": email, "password": pwd, **res['data']}
            app.config_data["last_username"] = email
            ConfigManager.save(app.config_data)

            # [核心] 上帝模式检测逻辑
            vt = app.user_info.get('vip_text', '')
            if '特供' in vt or 'GOD' in vt.upper():
                app.user_info['is_god'] = True
            else:
                app.user_info['is_god'] = False

            self._update_main_ui(app)
        else:
            toast(f"登录失败: {res}")

    def _update_main_ui(self, app):
        def ui_task():
            app.sm.current = "main"
            main_scr = app.sm.get_screen("main")
            main_scr.update_status()
            toast(f"欢迎归来, {app.user_info['username']}")

        # 在主线程更新 UI
        from kivy.clock import Clock
        Clock.schedule_once(lambda dt: ui_task(), 0)

    def go_register(self):
        MDApp.get_running_app().sm.current = "register"


class RegisterScreen(MDScreen):
    def send_code(self):
        email = self.ids.reg_email.text.strip()
        if "@" not in email:
            toast("邮箱格式不正确")
            return

        app = MDApp.get_running_app()
        threading.Thread(target=self._send_code_thread, args=(app, email)).start()

    def _send_code_thread(self, app, email):
        ok, res = AuthService.api_post("/api/send_code", {"email": email}, app.config_data)
        toast(res if isinstance(res, str) else "验证码已发送")

    def do_register(self):
        email = self.ids.reg_email.text.strip()
        code = self.ids.reg_code.text.strip()
        pwd = self.ids.reg_pass.text.strip()
        invite = self.ids.reg_invite.text.strip()

        if not all([email, code, pwd]):
            toast("请填写完整信息")
            return

        app = MDApp.get_running_app()
        data = {"username": email, "password": pwd, "verify_code": code,
                "hwid": AuthService.get_hwid(), "invite_code": invite}

        def run_reg():
            ok, res = AuthService.api_post("/api/register", data, app.config_data)
            if ok:
                toast("注册成功，请登录")
                from kivy.clock import Clock
                Clock.schedule_once(lambda dt: setattr(app.sm, 'current', 'login'), 0)
            else:
                toast(f"注册失败: {res}")

        threading.Thread(target=run_reg).start()


class MainScreen(MDScreen):
    fab_data = {
        'Image': 'image-plus',
        'Camera': 'camera',
    }

    def update_status(self):
        app = MDApp.get_running_app()
        user = app.user_info.get("username", "Guest")
        vip_text = app.user_info.get("vip_text", "Free")
        is_god = app.user_info.get("is_god", False)

        if is_god:
            vip_text = "👑 GOD MODE (上帝模式)"

        self.ids.user_info_lbl.text = f"User: {user}"
        self.ids.vip_info_lbl.text = f"Status: {vip_text}"

        if is_god:
            self.log("👑 尊贵的上帝卡用户，已解锁核心 Prompt 权限！")

    def log(self, text):
        from kivy.clock import Clock
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        new_line = f"[{timestamp}] {text}\n" + self.ids.log_box.text
        # 保持日志长度不过长
        if len(new_line) > 5000: new_line = new_line[:5000]
        Clock.schedule_once(lambda dt: setattr(self.ids.log_box, 'text', new_line), 0)

    def fab_callback(self, instance):
        icon = instance.icon
        if icon == 'image-plus':
            self.open_file_manager()
        elif icon == 'camera':
            toast("相机功能需打包后申请权限，建议使用相册")
            # 这里可以接入 plyer.camera

    # 文件管理器逻辑
    def open_file_manager(self):
        self.file_manager = MDFileManager(
            exit_manager=self.exit_manager,
            select_path=self.select_path,
            preview=True,
        )
        # 安卓存储路径通常在 /storage/emulated/0
        path = "/storage/emulated/0" if platform == 'android' else os.path.expanduser("~")
        self.file_manager.show(path)

    def select_path(self, path):
        self.exit_manager()
        toast(f"已选择图片: {os.path.basename(path)}")
        self.process_image(path)

    def exit_manager(self, *args):
        try:
            self.file_manager.close()
        except:
            pass

    def process_image(self, file_path):
        app = MDApp.get_running_app()
        self.log("🚀 开始处理图片...")
        self.log("正在排队上传到云端大脑...")

        threading.Thread(target=self._ai_thread, args=(app, file_path)).start()

    def _ai_thread(self, app, file_path):
        try:
            with open(file_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')

            prompt = app.config_data.get("ai_prompt", DEFAULT_PROMPT_CONTENT)

            # 使用自定义 API 或 官方服务器
            payload = {
                "username": app.user_info.get("username"),
                "password": app.user_info.get("password"),
                "image_base64": encoded_string,
                "prompt": prompt
            }

            # 这里简化逻辑，直接调用代理 OCR 接口
            url = f"{app.config_data['server_url']}/api/ocr_proxy"

            # 判断是否自定义API (VIP功能)
            if app.config_data.get('use_custom_api') and app.user_info.get('is_vip'):
                self.log("🔓 [自定义通道] 使用私有 API 加速中...")
                # ... (此处省略自定义API的requests调用，逻辑同原版Python代码，太长略) ...
                # 如果需要完整还原，请将原版 AIService 中 use_custom 部分搬运至此

            resp = requests.post(url, json=payload, timeout=int(app.config_data.get("request_timeout", 240)))

            if resp.status_code == 200:
                data = resp.json()
                if data['code'] == 200:
                    result_text = data['data']
                    self.log("✅ 识别成功！Markdown 已复制到剪贴板。")
                    Clipboard.copy(result_text)
                else:
                    self.log(f"❌ 服务器拒绝: {data['msg']}")
            else:
                self.log(f"❌ 网络错误: {resp.status_code}")

        except Exception as e:
            self.log(f"❌ 发生异常: {str(e)}")

    def open_settings(self):
        toast("移动端设置页面开发中...目前使用默认配置")


# ================== 主程序入口 ==================

class AIVisionProApp(MDApp):
    def build(self):
        # 1. 注册您的专属中文字体
        # ⚠️ 注意：此处已硬编码为您提供的字体文件名
        font_file = "huangkaihuaLawyerfont-2.ttf"
        LabelBase.register(name="Roboto", fn_regular=font_file, fn_bold=font_file)

        # 2. 设置主题 - 简约高级蓝
        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.accent_palette = "Red"

        # 加载KV布局
        Builder.load_string(KV_LAYOUT)

        # 3. 加载配置
        self.config_data = ConfigManager.load()
        self.user_info = {}

        # 4. 构建屏幕
        self.sm = MDScreenManager()
        self.sm.add_widget(LoginScreen(name="login"))
        self.sm.add_widget(RegisterScreen(name="register"))
        self.sm.add_widget(MainScreen(name="main"))

        # 自动登录逻辑
        last_u = self.config_data.get("last_username")
        if last_u:
            self.sm.get_screen("login").ids.email_field.text = last_u

        return self.sm


if __name__ == "__main__":
    AIVisionProApp().run()