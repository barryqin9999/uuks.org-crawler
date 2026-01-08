# -*- coding: utf-8 -*-
import os
import re
from DrissionPage import ChromiumPage
from common import save_json
from module_metadata import MetadataFetcher

class MetadataInteractive:
    def __init__(self, base_path):
        self.base_path = base_path
        self.page = None

    def _init_browser(self):
        if not self.page:
            print("[系统] 正在启动浏览器...")
            self.page = ChromiumPage()

    def _manual_modify(self, meta):
        """手动修改元数据 (包含封面)"""
        print("\n" + "="*40)
        print("【 修改模式 】(直接回车表示不修改)")
        print("-" * 40)
        
        # 1. 书名
        new_t = input(f"书名 [{meta['title']}]: ").strip()
        if new_t: meta['title'] = new_t
        
        # 2. 作者
        new_a = input(f"作者 [{meta['author']}]: ").strip()
        if new_a: meta['author'] = new_a
        
        # 3. 出版时间
        new_d = input(f"出版时间 [{meta['publish_date']}]: ").strip()
        if new_d: meta['publish_date'] = new_d

        # 4. 封面链接 (新增)
        current_cover = meta.get('cover_url', '无')
        # 如果链接太长，只显示前段
        display_cover = current_cover if len(current_cover) < 40 else current_cover[:37] + "..."
        print(f"当前封面: {display_cover}")
        new_c = input(f"新封面链接 (回车跳过): ").strip()
        if new_c: meta['cover_url'] = new_c
        
        # 5. 简介
        print(f"当前简介: {meta['description'][:30]}...")
        new_desc = input(f"新简介 (回车跳过): ").strip()
        if new_desc: meta['description'] = new_desc

        print("--- 信息已更新 ---\n")
        return meta

    def run(self, input_url):
        match = re.search(r'/b/(\d+)', input_url)
        if not match:
            print("[错误] 无法从链接中提取书籍 ID。")
            return None

        book_id = match.group(1)
        self._init_browser()

        try:
            # 1. 采集信息
            fetcher = MetadataFetcher(self.page)
            print(">>> 正在从 www 端提取书籍信息...")
            meta = fetcher.fetch_via_pc(book_id)

            if not meta:
                print("[失败] 未能获取有效信息。")
                return None

            # 2. 交互循环
            while True:
                print("\n" + "="*50)
                print("【 书籍元数据确认 】")
                print("-" * 50)
                print(f" [1] 书名:     {meta['title']}")
                print(f" [2] 作者:     {meta['author']}")
                print(f" [3] 出版时间: {meta['publish_date']}")
                print(f" [4] 封面链接: {meta['cover_url']}")
                print(f" [5] 简介预览: {meta['description'][:60]}...")
                print("="*50)
                
                print("请选择操作:")
                print(" [S] 存储 (Save)")
                print(" [M] 修改 (Modify)")
                print(" [Q] 放弃 (Quit)")
                
                choice = input("\n请输入指令 (s/m/q): ").strip().lower()

                if choice == 's':
                    # === 存储流程 ===
                    book_dir = os.path.join(self.base_path, meta['title'])
                    if not os.path.exists(book_dir):
                        os.makedirs(book_dir)
                    
                    # 保存 json
                    info_path = os.path.join(book_dir, 'book_info.json')
                    save_json(info_path, meta)
                    print(f"[保存] 信息已写入: {info_path}")

                    # 下载封面 (使用确认后的 URL)
                    if meta['cover_url']:
                        cover_path = os.path.join(book_dir, 'cover.jpg')
                        fetcher.download_cover(meta['cover_url'], cover_path)
                    
                    return meta['title'] 

                elif choice == 'm':
                    # === 修改流程 ===
                    meta = self._manual_modify(meta)
                    continue 

                elif choice == 'q':
                    print("[取消] 操作已取消，返回主菜单。")
                    return None
                
                else:
                    print("[错误] 无效指令，请重新输入。")

        except Exception as e:
            print(f"[错误] {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            if self.page:
                self.page.quit()
                self.page = None
