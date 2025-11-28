"""
Git引擎模块 (GitEngine)
负责调用PortableGit执行Git命令，处理差异分析和文件提取
"""

import os
import subprocess
import re
from typing import List, Dict, Tuple, Optional, NamedTuple
from dataclasses import dataclass


@dataclass
class DiffEntry:
    """Git差异条目"""
    status: str  # M=修改, A=新增, D=删除, T=类型变更, R=重命名
    old_path: str
    new_path: str
    similarity: int = 0  # 相似度百分比（重命名时使用）


@dataclass
class SubmoduleInfo:
    """子模块信息"""
    path: str
    old_sha: str
    new_sha: str
    old_commit: Optional[str] = None
    new_commit: Optional[str] = None


class GitEngine:
    """Git命令封装引擎"""

    def __init__(self, repo_path: str, portable_git_path: str = None):
        self.repo_path = os.path.abspath(repo_path)
        self.portable_git_path = portable_git_path or self._find_portable_git()
        self.git_exe = self._get_git_executable()

    def _find_portable_git(self) -> str:
        """查找PortableGit路径"""
        current_dir = os.path.dirname(os.path.dirname(__file__))
        portable_git_paths = [
            os.path.join(current_dir, "PortableGit", "bin", "git.exe"),
            os.path.join(current_dir, "PortableGit", "cmd", "git.exe"),
            os.path.join(current_dir, "PortableGit", "git.exe"),
        ]

        for path in portable_git_paths:
            if os.path.exists(path):
                return path

        # 回退到系统git
        return "git"

    def _get_git_executable(self) -> str:
        """获取Git可执行文件路径"""
        if self.portable_git_path and os.path.exists(self.portable_git_path):
            return self.portable_git_path
        return "git"

    def _run_git_command(self, args: List[str], capture_output: bool = True,
                        cwd: str = None, timeout: int = 300, binary_mode: bool = False) -> subprocess.CompletedProcess:
        """执行Git命令"""
        if cwd is None:
            cwd = self.repo_path

        try:
            # 设置环境变量以防止任何交互式提示
            env = os.environ.copy()
            env['GIT_CONFIG_NOSYSTEM'] = '1'
            env['GIT_TERMINAL_PROMPT'] = '0'
            env['GIT_EDITOR'] = ':'  # 设置为空操作符，防止打开编辑器
            env['EDITOR'] = ':'
            env['VISUAL'] = ':'
            env['GIT_MERGE_TOOL'] = 'merge'
            env['GIT_MERGE_VERBOSITY'] = '0'
            env['GIT_PAGER'] = 'cat'  # 防止分页器
            env['LESS'] = '-FRX'  # 防止less分页器等待
            env['PAGER'] = 'cat'

            # 确保不会触发交互式配置
            env['GIT_AUTHOR_NAME'] = 'Git Diff Tool'
            env['GIT_AUTHOR_EMAIL'] = 'tool@example.com'
            env['GIT_COMMITTER_NAME'] = 'Git Diff Tool'
            env['GIT_COMMITTER_EMAIL'] = 'tool@example.com'

            # 构建完整命令
            cmd = [self.git_exe] + args

            # 添加基本参数以防止交互
            if 'show' in args and '--no-pager' not in args:
                cmd.insert(1, '--no-pager')

            # 对于二进制文件，使用二进制模式
            if binary_mode:
                result = subprocess.run(
                    cmd,
                    cwd=cwd,
                    capture_output=True,
                    text=False,  # 使用二进制模式
                    env=env,
                    timeout=timeout,
                    stdin=subprocess.DEVNULL
                )
            else:
                result = subprocess.run(
                    cmd,
                    cwd=cwd,
                    capture_output=capture_output,
                    text=True,
                    encoding='utf-8',
                    errors='replace',  # 替换无法解码的字符而不是抛出异常
                    env=env,
                    timeout=timeout,
                    stdin=subprocess.DEVNULL
                )

            if capture_output and result.returncode != 0:
                # 处理错误信息（二进制模式时需要特殊处理）
                if binary_mode:
                    if result.stderr:
                        try:
                            error_msg = result.stderr.decode('utf-8', errors='replace')
                        except:
                            error_msg = f"Git命令返回错误代码: {result.returncode}"
                    else:
                        error_msg = f"Git命令返回错误代码: {result.returncode}"
                else:
                    error_msg = result.stderr or result.stdout
                    if not error_msg:
                        error_msg = f"Git命令返回错误代码: {result.returncode}"
                raise Exception(f"Git命令执行失败: {' '.join(args)}\n错误信息: {error_msg}")

            return result

        except subprocess.TimeoutExpired:
            raise Exception(f"Git命令执行超时: {' '.join(args)}")
        except FileNotFoundError:
            raise Exception(f"Git可执行文件未找到: {self.git_exe}")

    def validate_repository(self) -> bool:
        """验证是否为有效的Git仓库"""
        git_dir = os.path.join(self.repo_path, '.git')
        if os.path.exists(git_dir):
            return True

        # 检查是否为git worktree
        try:
            result = self._run_git_command(['rev-parse', '--is-inside-work-tree'])
            return result.stdout.strip() == 'true'
        except:
            return False

    def validate_sha(self, sha: str) -> bool:
        """验证SHA是否存在"""
        try:
            self._run_git_command(['rev-parse', sha])
            return True
        except:
            return False

    def get_diff_entries(self, old_sha: str, new_sha: str) -> List[DiffEntry]:
        """获取两个SHA之间的差异文件列表"""
        # 使用--name-status获取状态，-z以null分隔避免文件名空格问题
        result = self._run_git_command(['diff', '--name-status', '-z', old_sha, new_sha])

        entries = []
        content = result.stdout
        if not content:
            return entries

        # 解析-z格式的输出
        parts = content.split('\x00')
        i = 0

        while i < len(parts):
            if not parts[i]:
                i += 1
                continue

            # 解析状态行
            status_line = parts[i]
            i += 1

            if i >= len(parts):
                break

            # 文件路径
            file_path = parts[i]
            i += 1

            if not file_path:
                continue

            # 解析状态
            if len(status_line) >= 1:
                status = status_line[0]
                old_path = file_path
                new_path = file_path

                # 处理重命名或复制
                if status in ('R', 'C'):
                    # 格式为 R100 old_path new_path
                    match = re.match(r'^([RC])(\d+)$', status_line)
                    if match:
                        similarity = int(match.group(2))
                        if i < len(parts):
                            new_path = parts[i]
                            i += 1
                        entries.append(DiffEntry(status, old_path, new_path, similarity))
                    else:
                        entries.append(DiffEntry(status, old_path, new_path))
                else:
                    entries.append(DiffEntry(status, old_path, new_path))

        return entries

    def get_file_content(self, sha: str, file_path: str) -> bytes:
        """获取指定SHA和路径的文件内容（二进制安全）"""
        try:
            # 使用--no-pager来防止分页器，使用二进制模式处理所有文件
            args = ['--no-pager', 'show', f'{sha}:{file_path}']
            result = self._run_git_command(args, capture_output=True, timeout=60, binary_mode=True)
            return result.stdout if result.stdout else b''
        except subprocess.TimeoutExpired:
            raise Exception(f"获取文件内容超时: {file_path}")
        except Exception as e:
            if 'does not exist' in str(e) or 'fatal: path' in str(e) or 'invalid object' in str(e):
                return b''
            raise Exception(f"获取文件内容失败 {file_path}: {str(e)}")

    def get_submodule_info(self, old_sha: str, new_sha: str) -> List[SubmoduleInfo]:
        """获取子模块变更信息"""
        submodule_info = []

        # 获取old_sha的子模块信息
        try:
            result = self._run_git_command(['ls-tree', '-r', old_sha])
            old_submodules = self._parse_ls_tree_output(result.stdout)
        except:
            old_submodules = {}

        # 获取new_sha的子模块信息
        try:
            result = self._run_git_command(['ls-tree', '-r', new_sha])
            new_submodules = self._parse_ls_tree_output(result.stdout)
        except:
            new_submodules = {}

        # 比较找出变更的子模块
        all_paths = set(old_submodules.keys()) | set(new_submodules.keys())

        for path in all_paths:
            old_commit = old_submodules.get(path)
            new_commit = new_submodules.get(path)

            if old_commit != new_commit:  # 子模块有变更
                submodule_info.append(SubmoduleInfo(
                    path=path,
                    old_sha=old_sha,
                    new_sha=new_sha,
                    old_commit=old_commit,
                    new_commit=new_commit
                ))

        return submodule_info

    def _parse_ls_tree_output(self, output: str) -> Dict[str, str]:
        """解析ls-tree输出，返回路径到SHA的映射"""
        submodules = {}
        for line in output.strip().split('\n'):
            if line:
                parts = line.split()
                if len(parts) >= 4 and parts[1] == 'commit':
                    # 格式: mode type sha path
                    sha = parts[2]
                    path = ' '.join(parts[3:])
                    submodules[path] = sha
        return submodules

    def is_submodule_initialized(self, submodule_path: str) -> bool:
        """检查子模块是否已初始化"""
        submodule_full_path = os.path.join(self.repo_path, submodule_path)

        # 检查是否存在.git目录或文件
        git_path = os.path.join(submodule_full_path, '.git')
        if os.path.exists(git_path):
            # 如果是文件，说明是gitdir文件，读取实际路径
            if os.path.isfile(git_path):
                try:
                    with open(git_path, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if content.startswith('gitdir: '):
                            gitdir_path = content[8:]
                            if not os.path.isabs(gitdir_path):
                                gitdir_path = os.path.join(submodule_full_path, gitdir_path)
                            return os.path.exists(gitdir_path)
                except:
                    return False
            return True
        return False

    def get_submodule_engine(self, submodule_path: str) -> 'GitEngine':
        """为子模块创建新的GitEngine实例"""
        submodule_full_path = os.path.join(self.repo_path, submodule_path)
        return GitEngine(submodule_full_path, self.portable_git_path)

    def get_repository_root(self) -> str:
        """获取仓库根目录"""
        try:
            result = self._run_git_command(['rev-parse', '--show-toplevel'])
            return result.stdout.strip()
        except:
            return self.repo_path