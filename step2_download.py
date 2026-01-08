# -*- coding: utf-8 -*-
import os
import time
import random
from DrissionPage import ChromiumPage
from common import load_json, save_json

# 尝试引入整理模块，兼容 step3_clean.py
try:
    from step3_clean import TextCleaner as FileOrganizer
except ImportError:
    print("[警告] 未找到 step3_clean.py，将跳过自动整理步骤。")
    FileOrganizer = None

class BatchDownloader:
    def __init__(self, base_save_path):
        self.base_save_path = base_save_path
        self.page = None

    def _init_browser(self):
        """懒加载浏览器"""
        if not self.page:
            print("[系统] 正在启动浏览器引擎...")
            try:
                self.page = ChromiumPage()
                # 设置超时防止卡死
                self.page.set.timeouts(10)
            except Exception as e:
                print(f"[错误] 浏览器启动失败: {e}")

    def close_browser(self):
        if self.page:
            self.page.quit()
            self.page = None

    def parse_content(self, url):
        """智能解析正文"""
        if not self.page: return None
        try:
            self.page.get(url)
            
            # 1. 尝试常见的小说正文ID/Class
            selectors = ['#contentbox', '.contentbox', '#content', '.content', '.read-content', '#chaptercontent']
            content_ele = None
            for sel in selectors:
                if self.page.ele(sel):
                    ele = self.page.ele(sel)
                    if len(ele.text) > 50:
                        content_ele = ele
                        break
            
            # 2. 兜底：找字数最多的 div
            if not content_ele:
                divs = self.page.eles('tag:div')
                # 过滤掉链接太多的导航栏
                candidates = [d for d in divs if len(d.eles('tag:a')) < 10]
                if candidates:
                    content_ele = max(candidates, key=lambda x: len(x.text))

            if not content_ele: return None

            # 3. 提取并清洗
            # 优先提取 p 标签，如果没有则按行分割
            p_tags = content_ele.eles('tag:p')
            if p_tags:
                lines = [p.text.strip() for p in p_tags if p.text.strip()]
            else:
                lines = [line.strip() for line in content_ele.text.split('\n') if line.strip()]

            clean_lines = []
            # 广告词过滤
            ad_keywords = ["UU看书", "uuks.org", "javascript", "请收藏", "本站", "APP", "http"]
            for line in lines:
                if not any(ad in line for ad in ad_keywords):
                    clean_lines.append(line)
            
            return '\n\n'.join(clean_lines)

        except Exception as e:
            print(f"[解析异常] {e}")
            return None

    def run(self, specific_book=None):
        """主入口"""
        if not specific_book:
            print("[错误] 未指定书籍。")
            return

        novel_dir = os.path.join(self.base_save_path, specific_book)
        json_path = os.path.join(novel_dir, 'catalog.json')

        if not os.path.exists(json_path):
            print(f"[错误] 找不到目录文件: {json_path}")
            return

        # === 阶段零：调用 Step3 进行文件名整理 ===
        if FileOrganizer:
            try:
                print("\n" + "="*40)
                print("[前置] 正在检查本地文件序号...")
                # 实例化并调用 run()，保持接口统一
                organizer = FileOrganizer(self.base_save_path)
                organizer.run(specific_book)
                print("="*40 + "\n")
            except Exception as e:
                print(f"[警告] 自动整理失败: {e}")

        # === 阶段一：准备任务 ===
        data = load_json(json_path)
        chapters = data['chapters']
        
        download_queue = []
        print(f"[检查] 扫描 {len(chapters)} 个章节...")
        
        for ch in chapters:
            file_path = os.path.join(novel_dir, ch['file_name'])
            # 如果文件存在且有内容，标记成功
            if os.path.exists(file_path) and os.path.getsize(file_path) > 300:
                ch['status'] = 'success'
            else:
                ch['status'] = 'pending'
                download_queue.append(ch)

        save_json(json_path, data)
        
        if not download_queue:
            print("[恭喜] 所有章节已存在，无需下载。")
            return

        # === 阶段二：开始下载 ===
        print(f"[开始] 待下载: {len(download_queue)} 章")
        self._init_browser()
        
        success_count = 0
        total = len(download_queue)
        
        try:
            for i, ch in enumerate(download_queue, 1):
                print(f"[{i}/{total}] 下载: {ch['file_name']}")
                
                content = None
                # 重试机制
                for retry in range(3):
                    content = self.parse_content(ch['url'])
                    if content: break
                    time.sleep(1)
                
                if content:
                    file_path = os.path.join(novel_dir, ch['file_name'])
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    ch['status'] = 'success'
                    success_count += 1
                else:
                    print(f"  -> 失败: 无法提取内容")
                    ch['status'] = 'failed'
                
                if i % 10 == 0: save_json(json_path, data)
                time.sleep(random.uniform(0.2, 0.5))

        except KeyboardInterrupt:
            print("\n[停止] 用户手动中断。")
        except Exception as e:
            print(f"\n[出错] {e}")
        finally:
            save_json(json_path, data)
            print(f"\n[报告] 成功: {success_count} / 失败: {total - success_count}")
            # self.close_browser() # 可选：任务结束后关闭浏览器
