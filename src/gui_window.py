"""
GUI界面模块 (MainWindow)
实现图形用户界面，处理用户交互
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os
import queue
from typing import Optional, Dict, Any

from config_manager import ConfigManager
from git_engine import GitEngine, DiffEntry, SubmoduleInfo
from file_manager import FileManager


class MainWindow:
    """主窗口类"""

    def __init__(self):
        self.root = tk.Tk()
        self.config_manager = ConfigManager()
        self.file_manager = FileManager()
        self.git_engine: Optional[GitEngine] = None

        # 工作线程队列
        self.work_queue = queue.Queue()
        self.progress_queue = queue.Queue()

        # 加载配置
        self.config = self.config_manager.load_config()

        # 设置窗口
        self._setup_window()
        self._create_widgets()
        self._load_config_to_ui()

        # 启动进度监控
        self.root.after(100, self._check_progress_queue)

    def _setup_window(self):
        """设置窗口属性"""
        self.root.title("Git 差异提取工具")
        self.root.geometry("800x700")

        # 恢复窗口大小和位置
        if self.config.get("window_geometry"):
            try:
                self.root.geometry(self.config["window_geometry"])
            except:
                pass

        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _create_widgets(self):
        """创建界面控件"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        # 仓库路径
        row = 0
        ttk.Label(main_frame, text="仓库路径:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.repo_path_var = tk.StringVar()
        repo_frame = ttk.Frame(main_frame)
        repo_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        repo_frame.columnconfigure(0, weight=1)

        self.repo_path_entry = ttk.Entry(repo_frame, textvariable=self.repo_path_var, width=60)
        self.repo_path_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))

        ttk.Button(repo_frame, text="浏览", command=self._browse_repo_path).grid(row=0, column=1, padx=2)
        ttk.Button(repo_frame, text="打开", command=self._open_repo_path).grid(row=0, column=2, padx=2)

        # SHA输入
        row += 1
        ttk.Label(main_frame, text="Old SHA:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.old_sha_var = tk.StringVar()
        self.old_sha_entry = ttk.Entry(main_frame, textvariable=self.old_sha_var, width=60)
        self.old_sha_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)

        row += 1
        ttk.Label(main_frame, text="New SHA:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.new_sha_var = tk.StringVar()
        self.new_sha_entry = ttk.Entry(main_frame, textvariable=self.new_sha_var, width=60)
        self.new_sha_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)

        # 分隔线
        row += 1
        ttk.Separator(main_frame, orient='horizontal').grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)

        # 输出设置
        row += 1
        ttk.Label(main_frame, text="输出路径:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.output_path_var = tk.StringVar()
        output_frame = ttk.Frame(main_frame)
        output_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        output_frame.columnconfigure(0, weight=1)

        self.output_path_entry = ttk.Entry(output_frame, textvariable=self.output_path_var, width=60)
        self.output_path_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))

        ttk.Button(output_frame, text="浏览", command=self._browse_output_path).grid(row=0, column=1, padx=2)
        ttk.Button(output_frame, text="打开", command=self._open_output_path).grid(row=0, column=2, padx=2)

        row += 1
        ttk.Label(main_frame, text="文件夹名称:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.folder_name_var = tk.StringVar()
        self.folder_name_entry = ttk.Entry(main_frame, textvariable=self.folder_name_var, width=60)
        self.folder_name_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)

        # 操作按钮
        row += 1
        ttk.Separator(main_frame, orient='horizontal').grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)

        row += 1
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, columnspan=2, pady=10)

        self.list_diff_btn = ttk.Button(button_frame, text="List Diff", command=self._list_diff)
        self.list_diff_btn.grid(row=0, column=0, padx=5)

        self.copy_btn = ttk.Button(button_frame, text="Copy", command=self._copy_files)
        self.copy_btn.grid(row=0, column=1, padx=5)

        self.clear_btn = ttk.Button(button_frame, text="Clear", command=self._clear_inputs)
        self.clear_btn.grid(row=0, column=2, padx=5)

        # 进度条
        row += 1
        self.progress_var = tk.StringVar(value="就绪")
        ttk.Label(main_frame, textvariable=self.progress_var).grid(row=row, column=0, columnspan=2, sticky=tk.W)

        row += 1
        self.progress_bar = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress_bar.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        # 输出日志区域
        row += 1
        ttk.Label(main_frame, text="输出日志:").grid(row=row, column=0, sticky=tk.W, pady=(10, 5))

        row += 1
        self.log_text = scrolledtext.ScrolledText(main_frame, height=15, wrap=tk.WORD)
        self.log_text.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        main_frame.rowconfigure(row, weight=1)

    def _load_config_to_ui(self):
        """将配置加载到界面"""
        self.repo_path_var.set(self.config.get("repo_path", ""))
        self.old_sha_var.set(self.config.get("old_sha", ""))
        self.new_sha_var.set(self.config.get("new_sha", ""))
        self.output_path_var.set(self.config.get("output_path", ""))
        self.folder_name_var.set(self.config.get("output_folder_name", ""))

    def _save_config_from_ui(self):
        """从界面保存配置"""
        updates = {
            "repo_path": self.repo_path_var.get(),
            "old_sha": self.old_sha_var.get(),
            "new_sha": self.new_sha_var.get(),
            "output_path": self.output_path_var.get(),
            "output_folder_name": self.folder_name_var.get(),
            "window_geometry": self.root.geometry()
        }
        self.config_manager.update_config(updates)

    def _log_message(self, message: str):
        """在日志区域显示消息"""
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def _browse_repo_path(self):
        """浏览仓库路径"""
        path = filedialog.askdirectory(title="选择Git仓库目录")
        if path:
            self.repo_path_var.set(path)

    def _open_repo_path(self):
        """在资源管理器中打开仓库路径"""
        path = self.repo_path_var.get()
        if path and os.path.exists(path):
            os.startfile(path)

    def _browse_output_path(self):
        """浏览输出路径"""
        path = filedialog.askdirectory(title="选择输出目录")
        if path:
            self.output_path_var.set(path)

    def _open_output_path(self):
        """在资源管理器中打开输出路径"""
        path = self.output_path_var.get()
        if path and os.path.exists(path):
            os.startfile(path)

    def _clear_inputs(self):
        """清空输入框"""
        self.repo_path_var.set("")
        self.old_sha_var.set("")
        self.new_sha_var.set("")
        self.output_path_var.set("")
        self.folder_name_var.set("")
        self.log_text.delete(1.0, tk.END)

    def _validate_inputs(self) -> tuple[bool, str]:
        """验证输入参数"""
        if not self.repo_path_var.get():
            return False, "请选择仓库路径"

        if not os.path.exists(self.repo_path_var.get()):
            return False, "仓库路径不存在"

        if not self.old_sha_var.get():
            return False, "请输入Old SHA"

        if not self.new_sha_var.get():
            return False, "请输入New SHA"

        if not self.output_path_var.get():
            return False, "请选择输出路径"

        if not self.folder_name_var.get():
            return False, "请输入输出文件夹名称"

        return True, ""

    def _list_diff(self):
        """列出差异文件"""
        self._log_message("List Diff按钮被点击")

        valid, error = self._validate_inputs()
        if not valid:
            self._log_message(f"输入验证失败: {error}")
            messagebox.showerror("输入错误", error)
            return

        self._log_message("输入验证通过，保存配置")

        # 保存配置
        self._save_config_from_ui()

        # 在工作线程中执行
        try:
            thread = threading.Thread(target=self._list_diff_worker, daemon=True)
            thread.start()
            self._log_message("List Diff工作线程已启动")
        except Exception as e:
            self._log_message(f"启动List Diff工作线程失败: {e}")
            messagebox.showerror("错误", f"启动工作线程失败: {e}")

    def _list_diff_worker(self):
        """工作线程：列出差异"""
        try:
            self.progress_queue.put(("start", "正在分析Git差异..."))

            # 初始化Git引擎
            self.git_engine = GitEngine(self.repo_path_var.get())

            # 验证仓库
            if not self.git_engine.validate_repository():
                self.progress_queue.put(("error", "无效的Git仓库"))
                return

            # 验证SHA
            old_sha = self.old_sha_var.get()
            new_sha = self.new_sha_var.get()

            if not self.git_engine.validate_sha(old_sha):
                self.progress_queue.put(("error", f"Old SHA不存在: {old_sha}"))
                return

            if not self.git_engine.validate_sha(new_sha):
                self.progress_queue.put(("error", f"New SHA不存在: {new_sha}"))
                return

            # 获取差异
            diff_entries = self.git_engine.get_diff_entries(old_sha, new_sha)
            self.progress_queue.put(("log", f"找到 {len(diff_entries)} 个文件变更"))

            # 获取子模块信息
            submodules = self.git_engine.get_submodule_info(old_sha, new_sha)
            if submodules:
                self.progress_queue.put(("log", f"发现 {len(submodules)} 个子模块变更"))

            # 显示差异
            self.progress_queue.put(("diff_result", diff_entries, submodules))
            self.progress_queue.put(("complete", "差异分析完成"))

        except Exception as e:
            self.progress_queue.put(("error", f"分析差异时发生错误: {str(e)}"))

    def _copy_files(self):
        """复制文件"""
        self._log_message("Copy按钮被点击")

        valid, error = self._validate_inputs()
        if not valid:
            self._log_message(f"输入验证失败: {error}")
            messagebox.showerror("输入错误", error)
            return

        self._log_message("输入验证通过")

        # 保存配置
        self._save_config_from_ui()
        self._log_message("配置已保存")

        # 确认操作
        response = messagebox.askyesno(
            "确认操作",
            f"即将从 {self.old_sha_var.get()} 提取差异到 {self.new_sha_var.get()}\n\n"
            f"输出到: {os.path.join(self.output_path_var.get(), self.folder_name_var.get())}\n\n"
            "是否继续？"
        )

        if not response:
            self._log_message("用户取消操作")
            return

        self._log_message("用户确认操作，开始启动工作线程")

        # 在工作线程中执行
        try:
            thread = threading.Thread(target=self._copy_files_worker, daemon=True)
            thread.start()
            self._log_message("工作线程已启动")
        except Exception as e:
            self._log_message(f"启动工作线程失败: {e}")
            messagebox.showerror("错误", f"启动工作线程失败: {e}")

    def _copy_files_worker(self):
        """工作线程：复制文件"""
        try:
            self.progress_queue.put(("start", "开始提取文件..."))

            # 初始化Git引擎
            self.git_engine = GitEngine(self.repo_path_var.get())

            # 验证仓库
            if not self.git_engine.validate_repository():
                self.progress_queue.put(("error", "无效的Git仓库"))
                return

            # 获取参数
            old_sha = self.old_sha_var.get()
            new_sha = self.new_sha_var.get()
            output_path = self.output_path_var.get()
            folder_name = self.folder_name_var.get()

            # 准备输出目录
            success, error = self.file_manager.prepare_output_directory(output_path, folder_name)
            if not success:
                self.progress_queue.put(("error", error))
                return

            full_output_path = os.path.join(output_path, folder_name)

            # 获取差异
            diff_entries = self.git_engine.get_diff_entries(old_sha, new_sha)
            self.progress_queue.put(("log", f"找到 {len(diff_entries)} 个文件变更"))

            # 处理普通文件
            self._process_diff_files(diff_entries, old_sha, new_sha, full_output_path)

            # 处理子模块
            submodules = self.git_engine.get_submodule_info(old_sha, new_sha)
            for submodule in submodules:
                self.progress_queue.put(("log", f"处理子模块: {submodule.path}"))
                self._process_submodule(submodule, full_output_path)

            # 显示统计信息
            stats = self.file_manager.get_statistics()
            self.progress_queue.put(("log", f"复制完成: 成功 {stats['copied_files']} 个文件"))
            if stats['failed_files']:
                self.progress_queue.put(("log", f"失败 {stats['failed_files_count']} 个文件"))

            self.progress_queue.put(("complete", "文件提取完成"))

        except Exception as e:
            self.progress_queue.put(("error", f"提取文件时发生错误: {str(e)}"))

    def _process_diff_files(self, diff_entries: list, old_sha: str, new_sha: str, output_path: str):
        """处理差异文件"""
        total_files = len(diff_entries)
        processed_files = 0

        for entry in diff_entries:
            try:
                processed_files += 1
                self.progress_queue.put(("log", f"处理文件 {processed_files}/{total_files}: {entry.new_path}"))

                if entry.status in ['M', 'T']:  # 修改或类型变更
                    # 复制old版本
                    self.progress_queue.put(("log", f"  获取旧版本: {entry.old_path}"))
                    old_content = self.git_engine.get_file_content(old_sha, entry.old_path)
                    self.file_manager.copy_file_with_structure(old_content, output_path, entry.old_path, "old")

                    # 复制new版本
                    self.progress_queue.put(("log", f"  获取新版本: {entry.new_path}"))
                    new_content = self.git_engine.get_file_content(new_sha, entry.new_path)
                    self.file_manager.copy_file_with_structure(new_content, output_path, entry.new_path, "new")

                elif entry.status == 'A':  # 新增
                    # 只复制new版本
                    self.progress_queue.put(("log", f"  获取新文件: {entry.new_path}"))
                    new_content = self.git_engine.get_file_content(new_sha, entry.new_path)
                    self.file_manager.copy_file_with_structure(new_content, output_path, entry.new_path, "new")

                elif entry.status == 'D':  # 删除
                    # 只复制old版本
                    self.progress_queue.put(("log", f"  获取已删除文件: {entry.old_path}"))
                    old_content = self.git_engine.get_file_content(old_sha, entry.old_path)
                    self.file_manager.copy_file_with_structure(old_content, output_path, entry.old_path, "old")

                elif entry.status in ['R', 'C']:  # 重命名或复制
                    # 复制old路径
                    self.progress_queue.put(("log", f"  获取重命名前: {entry.old_path}"))
                    old_content = self.git_engine.get_file_content(old_sha, entry.old_path)
                    self.file_manager.copy_file_with_structure(old_content, output_path, entry.old_path, "old")

                    # 复制new路径
                    self.progress_queue.put(("log", f"  获取重命名后: {entry.new_path}"))
                    new_content = self.git_engine.get_file_content(new_sha, entry.new_path)
                    self.file_manager.copy_file_with_structure(new_content, output_path, entry.new_path, "new")

                self.progress_queue.put(("log", f"  ✅ 完成: {entry.new_path or entry.old_path}"))

            except Exception as e:
                error_msg = f"处理文件失败: {entry.new_path or entry.old_path} - {str(e)}"
                self.progress_queue.put(("log", f"  ❌ {error_msg}"))
                self.file_manager.failed_files.append((entry.new_path or entry.old_path, str(e)))
                # 继续处理下一个文件，不中断整个过程

    def _process_submodule(self, submodule: SubmoduleInfo, output_path: str):
        """处理子模块"""
        try:
            # 检查子模块是否已初始化
            if not self.git_engine.is_submodule_initialized(submodule.path):
                self.progress_queue.put(("error", f"子模块未初始化或未拉取代码: {submodule.path}"))
                return

            # 获取子模块的Git引擎
            sub_engine = self.git_engine.get_submodule_engine(submodule.path)

            if not sub_engine.validate_repository():
                self.progress_queue.put(("error", f"子模块不是有效的Git仓库: {submodule.path}"))
                return

            # 获取子模块差异
            sub_diff_entries = sub_engine.get_diff_entries(
                submodule.old_commit or submodule.old_sha,
                submodule.new_commit or submodule.new_sha
            )

            self.progress_queue.put(("log", f"子模块 {submodule.path} 包含 {len(sub_diff_entries)} 个变更"))

            # 处理子模块文件，保持原有目录结构
            for entry in sub_diff_entries:
                # 映射到主项目的路径
                mapped_old_path = os.path.join(submodule.path, entry.old_path)
                mapped_new_path = os.path.join(submodule.path, entry.new_path)

                if entry.status in ['M', 'T']:
                    old_content = sub_engine.get_file_content(submodule.old_commit, entry.old_path)
                    self.file_manager.copy_file_with_structure(old_content, output_path, mapped_old_path, "old")

                    new_content = sub_engine.get_file_content(submodule.new_commit, entry.new_path)
                    self.file_manager.copy_file_with_structure(new_content, output_path, mapped_new_path, "new")

                elif entry.status == 'A':
                    new_content = sub_engine.get_file_content(submodule.new_commit, entry.new_path)
                    self.file_manager.copy_file_with_structure(new_content, output_path, mapped_new_path, "new")

                elif entry.status == 'D':
                    old_content = sub_engine.get_file_content(submodule.old_commit, entry.old_path)
                    self.file_manager.copy_file_with_structure(old_content, output_path, mapped_old_path, "old")

        except Exception as e:
            self.progress_queue.put(("error", f"处理子模块 {submodule.path} 时发生错误: {str(e)}"))

    def _check_progress_queue(self):
        """检查进度队列"""
        try:
            while True:
                item = self.progress_queue.get_nowait()
                self._handle_progress_item(item)
        except queue.Empty:
            pass

        # 继续检查
        self.root.after(100, self._check_progress_queue)

    def _handle_progress_item(self, item):
        """处理进度队列项目"""
        if item[0] == "start":
            status = item[1]
            self.progress_var.set(status)
            self.progress_bar.start()
            self._log_message(f"开始: {status}")

        elif item[0] == "log":
            message = item[1]
            self._log_message(message)

        elif item[0] == "error":
            error = item[1]
            self.progress_var.set("错误")
            self.progress_bar.stop()
            self._log_message(f"错误: {error}")
            messagebox.showerror("错误", error)

        elif item[0] == "complete":
            message = item[1]
            self.progress_var.set("完成")
            self.progress_bar.stop()
            self._log_message(f"完成: {message}")

        elif item[0] == "diff_result":
            diff_entries, submodules = item[1], item[2]
            self._show_diff_result(diff_entries, submodules)

    def _show_diff_result(self, diff_entries: list, submodules: list):
        """显示差异结果"""
        # 创建新窗口显示差异
        diff_window = tk.Toplevel(self.root)
        diff_window.title("差异文件列表")
        diff_window.geometry("800x600")

        # 创建文本框
        text_frame = ttk.Frame(diff_window, padding="10")
        text_frame.pack(fill=tk.BOTH, expand=True)

        text_widget = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD)
        text_widget.pack(fill=tk.BOTH, expand=True)

        # 显示差异文件
        text_widget.insert(tk.END, f"=== 差异文件列表 (共 {len(diff_entries)} 个文件) ===\n\n")

        for entry in diff_entries:
            status_desc = {
                'M': '修改',
                'A': '新增',
                'D': '删除',
                'T': '类型变更',
                'R': f'重命名 ({entry.similarity}%)',
                'C': f'复制 ({entry.similarity}%)'
            }

            desc = status_desc.get(entry.status, entry.status)
            text_widget.insert(tk.END, f"{desc:8} {entry.new_path}\n")

        # 显示子模块
        if submodules:
            text_widget.insert(tk.END, f"\n=== 子模块变更 (共 {len(submodules)} 个) ===\n\n")
            for submodule in submodules:
                text_widget.insert(tk.END, f"子模块变更: {submodule.path}\n")
                text_widget.insert(tk.END, f"  旧SHA: {submodule.old_commit or 'N/A'}\n")
                text_widget.insert(tk.END, f"  新SHA: {submodule.new_commit or 'N/A'}\n")

        text_widget.config(state=tk.DISABLED)

    def _on_closing(self):
        """窗口关闭事件"""
        # 保存配置
        self._save_config_from_ui()
        # 关闭窗口
        self.root.destroy()

    def run(self):
        """运行应用程序"""
        self.root.mainloop()


if __name__ == "__main__":
    app = MainWindow()
    app.run()