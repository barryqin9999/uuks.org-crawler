# -*- coding: utf-8 -*-
import os
import time
import re
from DrissionPage import ChromiumPage
from common import save_json

class CatalogManager:
    def __init__(self, target_url, base_save_path):
        self.raw_input_url = target_url
        self.base_save_path = base_save_path
        self.page = None
        # 提取 ID
        self.book_id = self._extract_book_id(target_url)

    def _init_browser(self):
        if not self.page:
            print("[系统] 启动浏览器 (Step1-目录抓取)...")
            self.page = ChromiumPage()
            self.page.set.timeouts(15)

    def _extract_book_id(self, url):
        match = re.search(r'/b/(\d+)', url)
        if match: return match.group(1)
        return None

    def _check_cloudflare(self):
        if "Just a moment" in self.page.title or "验证" in self.page.title:
            print("\n[注意] 触发 Cloudflare 盾，等待 10 秒自动验证...\n")
            time.sleep(10)

    # ==========================================================
    #  核心逻辑 1: 仅获取书名 (用于确定存储路径)
    # ==========================================================
    def _fetch_book_title(self):
        """访问 PC 详情页，只为了提取书名"""
        if not self.book_id: return f"Book_Unknown"

        pc_url = f"https://www.uuks.org/b/{self.book_id}/"
        print(f"[目录] 正在访问 PC 页获取书名: {pc_url}")
        
        self.page.get(pc_url)
        time.sleep(1.5) # 稍作等待确保加载
        self._check_cloudflare()

        title = f"Book_{self.book_id}" # 默认后备书名

        try:
            # 仅提取 H1 标签作为书名
            h1 = self.page.ele('tag:h1')
            if h1:
                raw = h1.text.strip()
                # 去除可能的后缀 (如 "书名_作者_...")
                if '_' in raw: raw = raw.split('_')[0]
                # 清洗文件名非法字符
                title = re.sub(r'[\\/:*?"<>|]', '_', raw).strip()
                print(f"[成功] 识别书名: 《{title}》")
            else:
                print(f"[警告] 未找到 H1 标签，使用默认目录名: {title}")

        except Exception as e:
            print(f"[警告] 书名提取失败: {e}，使用默认ID命名")
        
        return title

    # ==========================================================
    #  核心逻辑 2: 目录采集与交互 (保持不变)
    # ==========================================================
    def _normalize_to_pc_url(self, mobile_url):
        if not self.book_id: return mobile_url
        match = re.search(r'/(\d+\.html)', mobile_url)
        if match:
            return f"https://www.uuks.org/b/{self.book_id}/{match.group(1)}"
        return mobile_url

    def _clean_chapter_title(self, text):
        # 简单的标题清洗，去掉 "第xxx章" 之前多余的空格等
        match = re.search(r'(第[0-9零一二三四五六七八九十百千万两]+章.+)', text)
        if match: return match.group(1).strip()
        return text.strip()

    def _interactive_select(self, chapters):
        total = len(chapters)
        if total == 0: return []

        print("\n" + "="*50)
        print("【 章节预览 & 范围选择 】")
        print("-" * 50)
        
        limit = 10
        # 预览头尾
        if total <= limit * 2:
            for i in range(total):
                print(f" [{i+1}] {chapters[i]['title']}")
        else:
            for i in range(limit):
                print(f" [{i+1}] {chapters[i]['title']}")
            print(f"\n ... (共 {total} 章，中间省略) ...\n")
            for i in range(total - limit, total):
                print(f" [{i+1}] {chapters[i]['title']}")
        
        print("-" * 50)
        
        # 交互选择
        while True:
            start_input = input(f"请输入【起始】序号 (默认 1): ").strip()
            if not start_input:
                start_idx = 1
                break
            if start_input.isdigit() and 1 <= int(start_input) <= total:
                start_idx = int(start_input)
                break

        while True:
            end_input = input(f"请输入【结束】序号 (默认 {total}): ").strip()
            if not end_input:
                end_idx = total
                break
            if end_input.isdigit() and start_idx <= int(end_input) <= total:
                end_idx = int(end_input)
                break

        print(f"[系统] 已选定范围: {start_idx} - {end_idx} (共 {end_idx - start_idx + 1} 章)")
        return chapters[start_idx-1 : end_idx]

    def parse_mobile_catalog(self):
        """跳转移动端抓取目录"""
        url = f"https://m.uuks.org/b/{self.book_id}/all.html"
        print(f"\n[策略] 跳转移动端全本页抓取目录: {url}")
        
        self.page.get(url)
        time.sleep(1)
        self._check_cloudflare()

        # 寻找包含最多链接的容器
        candidates = self.page.eles('tag:div') + self.page.eles('tag:ul')
        best_container = None
        max_count = 0
        valid_kws = ["第", "章", "节", "回", "尾声"]

        for ele in candidates:
            links = ele.eles('tag:a')
            if not links: continue
            count = sum(1 for l in links if any(k in l.text for k in valid_kws) or l.text.strip().isdigit())
            if count > max_count:
                max_count = count
                best_container = ele
        
        container = best_container if best_container else self.page
        all_links = container.eles('tag:a')
        
        raw_list = []
        seen = set()
        trash = ["分卷阅读", "加入书架", "投推荐票", "直达底部", "返回顶部", "首页"] 

        for link in all_links:
            try:
                t = link.text.strip()
                u = link.link
                if not u or "javascript" in u: continue
                if any(k in t for k in trash): continue

                pc_url = self._normalize_to_pc_url(u)
                if pc_url in seen: continue

                clean_t = self._clean_chapter_title(t)
                if len(clean_t) < 2: continue

                seen.add(pc_url)
                raw_list.append({"title": clean_t, "url": pc_url, "status": "pending"})
            except: continue
        
        return self._interactive_select(raw_list)

    # ==========================================================
    #  主程序入口
    # ==========================================================
    def update_catalog(self):
        self._init_browser()
        
        try:
            # 1. 仅获取书名
            book_title = self._fetch_book_title()
            
            # 2. 创建目录 (如果 Step0 已创建，这里是用来确认路径)
            novel_dir = os.path.join(self.base_save_path, book_title)
            if not os.path.exists(novel_dir):
                os.makedirs(novel_dir)
                print(f"[系统] 创建新目录: {novel_dir}")
            else:
                print(f"[系统] 目标目录已存在: {novel_dir}")
            
            # (注意：此处不再保存 book_info.json 和 cover.jpg)
            
            # 3. 抓取目录
            chapters = self.parse_mobile_catalog()
            
            if not chapters:
                print("[取消] 未选择任何章节或抓取失败。")
                return None, None

            # 4. 生成文件名
            width = len(str(len(chapters)))
            width = max(width, 4)
            for idx, ch in enumerate(chapters):
                # 预生成文件名，供 Step2 下载使用
                ch['file_name'] = f"{str(idx+1).zfill(width)}_{ch['title']}.txt"

            # 5. 保存目录文件 (catalog.json)
            json_path = os.path.join(novel_dir, 'catalog.json')
            data = {
                "title": book_title,
                "url": self.raw_input_url,
                "chapters": chapters
            }
            save_json(json_path, data)
            
            print(f"[完成] 目录文件已生成: {json_path}")
            return book_title, json_path

        except Exception as e:
            print(f"[异常] {e}")
            import traceback
            traceback.print_exc()
            return None, None
        finally:
            if self.page:
                self.page.quit()
                self.page = None
