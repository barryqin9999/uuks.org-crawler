# -*- coding: utf-8 -*-
import os
import sys

# 导入各模块
# 请根据您实际的文件名调整 import
from step1_catalog import CatalogManager
try:
    from step2_download import BatchDownloader  # 假设您的下载器文件名
    from step3_clean import TextCleaner         # 假设您的清洗器文件名
except ImportError:
    pass # 暂时忽略缺失的模块，防止报错
from step4_epub import EpubAdvancedGenerator
from step0_metadata import MetadataInteractive

# 配置基础存储路径
BASE_SAVE_PATH = "novels"

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    if not os.path.exists(BASE_SAVE_PATH):
        os.makedirs(BASE_SAVE_PATH)

    current_url = ""
    current_book_folder = None # 核心变量：存储书名/文件夹名

    while True:
        print("\n" + "="*50)
        print("   小说下载与处理工具 (集成优化版)")
        print("="*50)
        
        # 显示当前状态
        if current_url:
            print(f"当前链接: {current_url}")
        if current_book_folder:
            print(f"当前书籍: 《{current_book_folder}》")
        else:
            print(f"当前书籍: [未解析]")
        print("-" * 50)

        # 首次运行要求输入链接
        if not current_url:
            raw = input("请输入小说目录页链接 (或输入 q 退出): ").strip()
            if raw.lower() == 'q': break
            if not raw.startswith('http'):
                print("[错误] 链接格式不正确。")
                continue
            current_url = raw
            # 清空书名，等待重新解析
            current_book_folder = None 
            continue

        print("请选择操作模式:")
        print("   1. [目录] 抓取目录 + 锁定书籍 (常规起手)")
        print("   2. [下载] 批量下载章节")
        print("   3. [清洗] 修复与合并文本")
        print("   4. [EPUB] 制作电子书")
        print("   ----------------")
        print("   5. [元数据] 仅管理书籍信息")
        print("   6. 更换目标书籍")
        print("   0. 退出程序")
        
        choice = input("\n请输入选项 (0-6): ").strip()

        # ========================================================
        #  【关键修复逻辑】: 自动解析书名
        #  如果用户选了 2-5，但还不知道书名，先自动去取书名
        # ========================================================
        if choice in ['2', '3', '4', '5'] and not current_book_folder:
            print("\n[系统] 检测到目标未锁定，正在解析书名...")
            try:
                # 借用 Step1 的类，只做书名提取，不抓目录
                temp_step1 = CatalogManager(current_url, BASE_SAVE_PATH)
                temp_step1._init_browser()      # 启动浏览器
                title = temp_step1._fetch_book_title() # 获取书名
                temp_step1.page.quit()          # 立即关闭
                
                if title:
                    current_book_folder = title
                    print(f"[系统] 已锁定书籍: {current_book_folder}")
                else:
                    print("[错误] 无法解析书名，请先执行步骤 1。")
                    continue
            except Exception as e:
                print(f"[异常] 自动解析失败: {e}")
                print("建议先运行步骤 1。")
                continue

        # ========================================================
        #  功能分发
        # ========================================================
        if choice == '1':
            # Step 1: 抓目录
            step1 = CatalogManager(current_url, BASE_SAVE_PATH)
            # update_catalog 会返回 (书名, json路径)
            title, _ = step1.update_catalog()
            if title:
                current_book_folder = title

        elif choice == '2':
            # Step 2: 下载
            # 请确保 step2_download.py 类名正确
            try:
                from step2_download import BatchDownloader
                step2 = BatchDownloader(BASE_SAVE_PATH)
                step2.run(current_book_folder)
            except ImportError:
                print("[错误] step2_download.py 缺失或类名不匹配")

        elif choice == '3':
            # Step 3: 清洗
            try:
                from step3_clean import TextCleaner
                step3 = TextCleaner(BASE_SAVE_PATH)
                step3.run(current_book_folder)
            except ImportError:
                print("[错误] step3_clean.py 缺失或类名不匹配")

        elif choice == '4':
            # Step 4: EPUB (我们刚刚修改好的)
            step4 = EpubAdvancedGenerator(BASE_SAVE_PATH)
            step4.run(current_book_folder)

        elif choice == '5':
            # Step 0: 元数据管理
            step0 = MetadataInteractive(BASE_SAVE_PATH)
            step0.run(current_url) 
            # Step0 可能会修改书名，这里最好不要强行覆盖 current_book_folder，
            # 除非 Step0 返回了新的书名

        elif choice == '6':
            # 重置状态
            current_url = ""
            current_book_folder = None
            clear_screen()
        
        elif choice == '0':
            break
            
        else:
            print("无效选项，请重试。")
        
        input("\n按回车键继续...")
        clear_screen()

if __name__ == "__main__":
    main()
