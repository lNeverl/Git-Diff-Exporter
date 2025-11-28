"""
Git 差异提取工具主程序
作者：lNeverl
功能：使用PortableGit对比两个SHA，提取差异文件到指定目录
"""

import sys
import os

# 添加src目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

def main():
    """主函数"""
    try:
        print("正在导入GUI模块...")
        from gui_window import MainWindow
        print("GUI模块导入成功")

        print("正在创建主窗口...")
        app = MainWindow()
        print("主窗口创建成功")

        print("正在启动GUI应用...")
        app.run()
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except ImportError as e:
        print(f"导入模块失败: {e}")
        print("请确保所有依赖模块都已正确安装")
        import traceback
        traceback.print_exc()
        input("按Enter键退出...")
    except Exception as e:
        print(f"程序运行时发生错误: {e}")
        import traceback
        traceback.print_exc()
        input("按Enter键退出...")


if __name__ == "__main__":
    main()