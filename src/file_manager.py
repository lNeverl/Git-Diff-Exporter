"""
文件管理模块 (FileManager)
负责文件操作、目录结构和路径处理
"""

import os
import shutil
import tkinter.messagebox as messagebox
from typing import List, Tuple, Optional
from pathlib import Path


class FileManager:
    """文件操作管理器"""

    def __init__(self):
        self.copied_files = 0
        self.failed_files = []
        self.current_operation = ""

    def prepare_output_directory(self, output_path: str, folder_name: str,
                                force_overwrite: bool = False) -> Tuple[bool, str]:
        """
        准备输出目录结构
        返回: (是否成功, 错误信息)
        """
        try:
            output_path = os.path.abspath(output_path)
            full_output_path = os.path.join(output_path, folder_name)

            if os.path.exists(full_output_path):
                if not force_overwrite:
                    response = messagebox.askyesnocancel(
                        "目录已存在",
                        f"输出目录已存在:\n{full_output_path}\n\n是否删除并重新创建？\n"
                        f"点击 '是' 删除并重新创建\n"
                        f"点击 '否' 保留现有文件\n"
                        f"点击 '取消' 中止操作"
                    )

                    if response is None:  # 取消
                        return False, "用户取消操作"
                    elif not response:  # 否，保留现有文件
                        # 检查old和new子目录，不存在则创建
                        old_dir = os.path.join(full_output_path, "old")
                        new_dir = os.path.join(full_output_path, "new")
                        os.makedirs(old_dir, exist_ok=True)
                        os.makedirs(new_dir, exist_ok=True)
                        return True, ""
                    else:  # 是，删除并重新创建
                        shutil.rmtree(full_output_path)

            # 创建目录结构
            os.makedirs(full_output_path, exist_ok=True)
            old_dir = os.path.join(full_output_path, "old")
            new_dir = os.path.join(full_output_path, "new")
            os.makedirs(old_dir, exist_ok=True)
            os.makedirs(new_dir, exist_ok=True)

            return True, ""

        except Exception as e:
            return False, f"准备输出目录失败: {str(e)}"

    def copy_file_to_directory(self, content: bytes, target_path: str) -> bool:
        """
        将文件内容复制到目标路径
        自动创建必要的目录结构
        """
        try:
            # 确保目标目录存在
            target_dir = os.path.dirname(target_path)
            if target_dir:
                os.makedirs(target_dir, exist_ok=True)

            # 写入文件
            with open(target_path, 'wb') as f:
                f.write(content)

            self.copied_files += 1
            return True

        except Exception as e:
            self.failed_files.append((target_path, str(e)))
            return False

    def copy_file_with_structure(self, content: bytes, base_output_path: str,
                                file_path: str, version: str) -> bool:
        """
        按原目录结构复制文件
        base_output_path: 输出基础路径 (包含文件夹名的路径)
        file_path: 相对于仓库根目录的文件路径
        version: 'old' 或 'new'
        """
        try:
            # 构建完整目标路径
            target_path = os.path.join(base_output_path, version, file_path)

            # 标准化路径分隔符
            target_path = os.path.normpath(target_path)

            return self.copy_file_to_directory(content, target_path)

        except Exception as e:
            self.failed_files.append((file_path, str(e)))
            return False

    def normalize_path(self, path: str) -> str:
        """标准化路径，处理不同平台的路径分隔符"""
        return os.path.normpath(path).replace('\\', '/')

    def get_relative_path(self, file_path: str, repo_path: str) -> str:
        """获取文件相对于仓库根目录的路径"""
        try:
            # 使用Path对象处理相对路径
            repo_path = Path(repo_path).resolve()
            file_path = Path(file_path).resolve()

            # 计算相对路径
            relative_path = file_path.relative_to(repo_path)
            return str(relative_path).replace('\\', '/')
        except ValueError:
            # 如果计算相对路径失败，返回原始路径
            return file_path.replace('\\', '/')

    def validate_output_path(self, output_path: str, folder_name: str) -> Tuple[bool, str]:
        """
        验证输出路径是否有效
        返回: (是否有效, 错误信息)
        """
        try:
            if not output_path:
                return False, "输出路径不能为空"

            if not folder_name:
                return False, "输出文件夹名称不能为空"

            # 检查输出路径是否存在
            if not os.path.exists(output_path):
                return False, f"输出路径不存在: {output_path}"

            # 检查是否为目录
            if not os.path.isdir(output_path):
                return False, f"输出路径不是目录: {output_path}"

            # 检查写入权限
            test_file = os.path.join(output_path, '.write_test')
            try:
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
            except PermissionError:
                return False, f"输出路径没有写入权限: {output_path}"

            return True, ""

        except Exception as e:
            return False, f"验证输出路径失败: {str(e)}"

    def get_directory_size(self, path: str) -> int:
        """获取目录大小（字节）"""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total_size += os.path.getsize(filepath)
        except:
            pass
        return total_size

    def format_file_size(self, size_bytes: int) -> str:
        """格式化文件大小显示"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"

    def reset_statistics(self):
        """重置统计信息"""
        self.copied_files = 0
        self.failed_files = []
        self.current_operation = ""

    def get_statistics(self) -> dict:
        """获取操作统计信息"""
        return {
            'copied_files': self.copied_files,
            'failed_files_count': len(self.failed_files),
            'failed_files': self.failed_files,
            'current_operation': self.current_operation
        }

    def ensure_directory_structure(self, base_path: str, relative_path: str) -> str:
        """
        确保目录结构存在
        返回完整的目标路径
        """
        target_path = os.path.join(base_path, relative_path)
        target_dir = os.path.dirname(target_path)

        if target_dir:
            os.makedirs(target_dir, exist_ok=True)

        return target_path

    def is_binary_file(self, content: bytes, sample_size: int = 1024) -> bool:
        """
        简单检测文件是否为二进制文件
        """
        if not content:
            return False

        # 只检查前sample_size字节
        sample = content[:sample_size]

        # 检查是否包含空字节（二进制文件的典型特征）
        if b'\x00' in sample:
            return True

        # 检查文本文件中不常见的控制字符
        try:
            # 尝试解码为UTF-8
            sample.decode('utf-8')
            return False
        except UnicodeDecodeError:
            return True

    def backup_file(self, file_path: str) -> bool:
        """备份文件（添加.backup后缀）"""
        try:
            if os.path.exists(file_path):
                backup_path = file_path + '.backup'
                counter = 1
                while os.path.exists(backup_path):
                    backup_path = f"{file_path}.backup{counter}"
                    counter += 1
                shutil.copy2(file_path, backup_path)
                return True
        except:
            pass
        return False