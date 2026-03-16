import sys
import json
import os
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
    QListWidget, QListWidgetItem, QLineEdit, QPushButton, 
    QLabel, QCheckBox, QMenu, QTabWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor, QAction

DATA_FILE = "todo.json"

class TodoListApp(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_data()

    def init_ui(self):
        # --- 窗口基础设置 ---
        self.setWindowTitle("Todo List")
        self.setFixedSize(300, 500)
        
        # 整体便利贴与标签页样式 (QSS)
        self.setStyleSheet("""
            QWidget {
                background-color: #FFF9C4; /* 经典便利贴浅黄色 */
                font-family: 'Segoe UI', 'Microsoft YaHei';
                font-size: 14px;
                color: #333333;
            }
            /* 列表样式 */
            QListWidget {
                background-color: transparent;
                border: none;
            }
            QListWidget::item {
                padding: 6px;
                border-bottom: 1px dashed #E0D492; 
            }
            QListWidget::item:selected {
                background-color: #FFF176;
                color: #333333;
            }
            /* 输入框与按钮样式 */
            QLineEdit {
                background-color: rgba(255, 255, 255, 180);
                border: 1px solid #E0D492;
                border-radius: 4px;
                padding: 6px;
            }
            QPushButton {
                background-color: #FFCA28;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #FFB300;
            }
            /* 标签页样式 */
            QTabWidget::pane {
                border: none;
                border-top: 2px solid #E0D492;
            }
            QTabBar::tab {
                background: transparent;
                padding: 6px 20px;
                border: none;
                color: #757575;
            }
            QTabBar::tab:selected {
                color: #333333;
                font-weight: bold;
                border-bottom: 3px solid #FFCA28;
            }
        """)

        main_layout = QVBoxLayout(self)

        # --- 顶部：标题和置顶选项 ---
        top_layout = QHBoxLayout()
        title_label = QLabel("📝 <b>Todo List</b>")
        title_label.setStyleSheet("font-size: 18px;")
        
        self.top_checkbox = QCheckBox("始终置顶")
        self.top_checkbox.setStyleSheet("font-size: 12px;")
        self.top_checkbox.stateChanged.connect(self.toggle_always_on_top)
        
        top_layout.addWidget(title_label)
        top_layout.addStretch()
        top_layout.addWidget(self.top_checkbox)
        main_layout.addLayout(top_layout)

        # --- 中间：标签页（待办 / 历史） ---
        self.tabs = QTabWidget()
        
        # 1. 待办列表 Widget
        self.todo_list = QListWidget()
        self.todo_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.todo_list.customContextMenuRequested.connect(self.show_context_menu)
        self.todo_list.itemChanged.connect(self.on_item_changed)
        
        # 2. 历史列表 Widget
        self.history_list = QListWidget()
        self.history_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.history_list.customContextMenuRequested.connect(self.show_context_menu)
        
        self.tabs.addTab(self.todo_list, "待办事项")
        self.tabs.addTab(self.history_list, "历史记录")
        main_layout.addWidget(self.tabs)

        # --- 底部：输入区域 ---
        bottom_layout = QHBoxLayout()
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("添加新任务...")
        self.input_edit.returnPressed.connect(self.add_task)
        
        self.add_btn = QPushButton("添加")
        self.add_btn.clicked.connect(self.add_task)
        
        bottom_layout.addWidget(self.input_edit)
        bottom_layout.addWidget(self.add_btn)
        main_layout.addLayout(bottom_layout)

        # --- 全局快捷键：Delete 删除选中任务 ---
        delete_action = QAction(self)
        delete_action.setShortcut("Del")
        delete_action.triggered.connect(self.delete_selected_task)
        self.addAction(delete_action)

    def add_task(self):
        """添加新任务到待办列表"""
        text = self.input_edit.text().strip()
        if not text:
            return
            
        # 构造任务数据字典
        task_data = {
            "text": text,
            "completed": False,
            "completed_at": None
        }
        self.create_todo_item(task_data)
        self.input_edit.clear()
        
        # 添加任务后自动切回"待办"页面
        self.tabs.setCurrentIndex(0)
        self.save_data()

    def create_todo_item(self, task_data):
        """在待办页面创建列表项"""
        item = QListWidgetItem(task_data["text"])
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        
        # 使用 Qt.UserRole 把完整数据绑定在 item 上
        item.setData(Qt.UserRole, task_data)
        
        # 设置勾选状态和样式
        if task_data.get("completed", False):
            item.setCheckState(Qt.Checked)
            self.apply_item_style(item, True)
        else:
            item.setCheckState(Qt.Unchecked)
            self.apply_item_style(item, False)
            
        self.todo_list.addItem(item)

    def create_history_item(self, task_data):
        """在历史页面创建列表项（不带复选框，包含完成时间）"""
        text = task_data.get("text", "未知任务")
        time_str = task_data.get("completed_at", "未知时间")
        display_text = f"{text}\n  🕒 {time_str}"
        
        item = QListWidgetItem(display_text)
        item.setData(Qt.UserRole, task_data)
        # 历史记录统一设为灰色
        item.setForeground(QColor("#9E9E9E")) 
        
        self.history_list.addItem(item)

    def on_item_changed(self, item):
        """当待办任务被勾选/取消勾选时触发"""
        is_completed = (item.checkState() == Qt.Checked)
        self.apply_item_style(item, is_completed)
        
        # 更新绑定的数据字典
        data = item.data(Qt.UserRole)
        data['completed'] = is_completed
        
        # 记录或清除完成时间
        if is_completed:
            if not data.get('completed_at'):
                data['completed_at'] = datetime.now().strftime("%Y-%m-%d %H:%M")
        else:
            data['completed_at'] = None
            
        item.setData(Qt.UserRole, data)
        self.save_data()

    def apply_item_style(self, item, is_completed):
        """设置待办任务已完成/未完成的文字样式（删除线、颜色）"""
        font = item.font()
        if is_completed:
            font.setStrikeOut(True)
            item.setFont(font)
            item.setForeground(QColor("#9E9E9E")) # 灰色
        else:
            font.setStrikeOut(False)
            item.setFont(font)
            item.setForeground(QColor("#333333")) # 恢复原色

    def get_current_list(self):
        """获取当前正在查看的列表（待办或历史）"""
        if self.tabs.currentIndex() == 0:
            return self.todo_list
        else:
            return self.history_list

    def delete_selected_task(self):
        """删除当前选中的任务"""
        current_list = self.get_current_list()
        current_row = current_list.currentRow()
        if current_row >= 0:
            current_list.takeItem(current_row)
            self.save_data()

    def show_context_menu(self, position):
        """右键菜单"""
        current_list = self.get_current_list()
        item = current_list.itemAt(position)
        if not item:
            return
            
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu { background-color: white; border: 1px solid #ccc; }
            QMenu::item { padding: 5px 20px; }
            QMenu::item:selected { background-color: #EEE; }
        """)
        
        delete_action = QAction("删除任务", self)
        delete_action.triggered.connect(self.delete_selected_task)
        menu.addAction(delete_action)
        
        menu.exec(current_list.mapToGlobal(position))

    def toggle_always_on_top(self, state):
        """切换窗口始终置顶"""
        if state == Qt.Checked.value:
            self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        else:
            self.setWindowFlag(Qt.WindowStaysOnTopHint, False)
        self.show()

    def save_data(self):
        """将待办和历史列表保存到 JSON 文件"""
        tasks = []
        
        # 1. 保存待办列表的数据
        for i in range(self.todo_list.count()):
            item = self.todo_list.item(i)
            tasks.append(item.data(Qt.UserRole))
            
        # 2. 保存历史列表的数据
        for i in range(self.history_list.count()):
            item = self.history_list.item(i)
            tasks.append(item.data(Qt.UserRole))
            
        try:
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(tasks, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"保存数据失败: {e}")

    def load_data(self):
        """程序启动时加载 JSON 数据，按完成状态分配到两个列表"""
        if not os.path.exists(DATA_FILE):
            return
            
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                tasks = json.load(f)
                
            # 暂时断开信号，防止频发 itemChanged 触发保存
            self.todo_list.blockSignals(True)
            
            for task in tasks:
                # 核心逻辑：如果下次打开时，检测到已经是完成状态，就放到“历史页”
                if task.get("completed", False):
                    self.create_history_item(task)
                else:
                    self.create_todo_item(task)
                    
            self.todo_list.blockSignals(False)
            
        except Exception as e:
            print(f"加载数据失败: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    window = TodoListApp()
    window.show()
    sys.exit(app.exec())