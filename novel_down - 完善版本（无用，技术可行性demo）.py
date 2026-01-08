# -*- coding: utf-8 -*-
from DrissionPage import ChromiumPage
import os
import time
import re
import random

class NovelDownloader:
    def __init__(self, target_url, base_save_path):
        self.target_url = target_url
        self.base_save_path = base_save_path
        print("[系统] 正在启动浏览器...")
        self.page = ChromiumPage()
        self.page.set.timeouts(15)

    def validate_filename(self, filename):
        return re.sub(r'[\\/:*?"<>|]', '_', filename).strip()

    def clean_title(self, text):
        match = re.search(r'(第[0-9零一二三四五六七八九十百千万两]+章.+)', text)
        if match:
            return match.group(1).strip()
        return text.strip()

    def find_catalog_container(self):
        print("[系统] 正在智能识别目录区域...")
        candidates = self.page.eles('tag:div') + self.page.eles('tag:dl') + self.page.eles('tag:ul')
        best_container = None
        max_chapter_count = 0
        
        for ele in candidates:
            try:
                if len(ele.text) < 200: continue
                links = ele.eles('tag:a')
                count = 0
                for link in links:
                    if "第" in link.text or "章" in link.text:
                        count += 1
                if count > max_chapter_count:
                    max_chapter_count = count
                    best_container = ele
            except:
                continue
        return best_container

    def parse_catalog(self):
        print(f"[1/2] 正在访问目录页: {self.target_url}")
        self.page.get(self.target_url)
        
        if "Just a moment" in self.page.title or "验证" in self.page.title:
            print("\n[注意] 请在浏览器中手动通过 Cloudflare 验证！等待 15 秒...\n")
            time.sleep(15)

        try:
            h1 = self.page.ele('tag:h1')
            book_title = h1.text if h1 else "未知小说"
        except:
            book_title = "未知小说"
        book_title = self.validate_filename(book_title)
        print(f"[系统] 识别书名: {book_title}")

        container = self.find_catalog_container()
        if not container:
            container = self.page

        print("[系统] 正在抓取章节列表...")
        chapters = []
        seen_urls = set()
        
        all_links = container.eles('tag:a')
        special_keywords = ['序', '引子', '楔子', '尾声', '后记', '感言', '番外', '完本']

        for link in all_links:
            try:
                raw_text = link.text
                url = link.link
                if not url or url in seen_urls: continue
                
                clean_name = self.clean_title(raw_text)
                is_standard = "第" in clean_name and "章" in clean_name
                is_special = any(k in clean_name for k in special_keywords)
                
                if not is_standard and not is_special:
                    continue
                if clean_name in ["最新章节", "全部章节", "分卷阅读", "加入书架"]:
                    continue

                chapters.append({'name': clean_name, 'url': url})
                seen_urls.add(url)
            except:
                continue

        count = len(chapters)
        if count == 0:
            print("[错误] 未抓取到章节链接。")
            return None, None

        print(f"[系统] 成功解析到 {count} 个章节。")
        return book_title, chapters

    def parse_content(self, chapter_url):
        self.page.get(chapter_url)
        content_ele = None
        selectors = ['#contentbox', '.contentbox', '#content', '.content', '.read-content']
        
        for selector in selectors:
            try:
                if self.page.ele(selector, timeout=5):
                    ele = self.page.ele(selector)
                    if len(ele.text) > 50:
                        content_ele = ele
                        break
            except:
                continue
        
        if not content_ele:
            try:
                divs = self.page.eles('tag:div')
                max_len = 0
                for div in divs:
                    if len(div.eles('tag:a')) > 5: continue
                    txt_len = len(div.text)
                    if txt_len > max_len:
                        max_len = txt_len
                        content_ele = div
            except:
                pass

        if not content_ele:
            return None

        lines = []
        p_tags = content_ele.eles('tag:p')
        if p_tags:
            for p in p_tags:
                text = p.text.strip()
                if text: lines.append(text)
        else:
            raw_text = content_ele.text
            for line in raw_text.split('\n'):
                line = line.strip()
                if line: lines.append(line)

        clean_lines = []
        for line in lines:
            if any(ad in line for ad in ["UU看书", "uuks.org", "javascript", "请收藏", "本站"]):
                continue
            clean_lines.append(line)
        
        return '\n\n'.join(clean_lines)

    def generate_download_queue(self, chapters, novel_dir):
        """
        【新增功能】生成智能下载队列
        对比本地文件，决定哪些需要下载
        """
        print("[系统] 正在校验本地文件完整性...")
        download_queue = []
        skipped_count = 0
        incomplete_count = 0

        # 这里使用 start=1 确保和之前的命名逻辑一致
        for index, chapter in enumerate(chapters, start=1):
            safe_name = self.validate_filename(chapter['name'])
            # 保持 0001_xxx.txt 的命名格式
            file_name = f"{str(index).zfill(4)}_{safe_name}.txt"
            file_path = os.path.join(novel_dir, file_name)

            should_download = False
            
            if not os.path.exists(file_path):
                # 情况1：文件不存在
                should_download = True
            else:
                # 情况2：文件存在，但体积过小（小于300字节视为不完整/报错）
                file_size = os.path.getsize(file_path)
                if file_size < 300:
                    should_download = True
                    incomplete_count += 1
                else:
                    skipped_count += 1
            
            if should_download:
                # 将 序号、文件名、URL 打包存入队列
                download_queue.append({
                    'index': index,
                    'name': safe_name,
                    'file_path': file_path,
                    'url': chapter['url']
                })

        return download_queue, skipped_count, incomplete_count

    def run(self):
        # 1. 解析目录
        result = self.parse_catalog()
        if not result or not result[1]:
            return

        book_title, chapters = result
        novel_dir = os.path.join(self.base_save_path, book_title)
        
        if not os.path.exists(novel_dir):
            os.makedirs(novel_dir, exist_ok=True)

        # 2. 生成下载队列 (智能校验)
        queue, skipped, incomplete = self.generate_download_queue(chapters, novel_dir)

        total_chapters = len(chapters)
        total_tasks = len(queue)
        
        print("\n" + "="*50)
        print(f" 📚 书名: {book_title}")
        print(f" 📑 总章节: {total_chapters}")
        print(f" ✅ 已完成: {skipped}")
        print(f" ⚠️ 不完整: {incomplete} (将重新下载)")
        print(f" ⬇️ 待下载: {total_tasks}")
        print("="*50 + "\n")

        if total_tasks == 0:
            print("[恭喜] 所有章节校验完整，无需下载！")
            return

        print(f"[2/2] 开始执行下载任务...")
        
        success_count = 0
        # 遍历下载队列
        for i, task in enumerate(queue, start=1):
            
            print(f"进度 ({i}/{total_tasks}) | 正在下载: {task['name']}")
            
            content = None
            for retry in range(3):
                try:
                    content = self.parse_content(task['url'])
                    if content: break
                    time.sleep(1)
                except:
                    pass
            
            if content:
                try:
                    with open(task['file_path'], 'w', encoding='utf-8') as f:
                        f.write(content)
                    success_count += 1
                except Exception as e:
                    print(f"  [写入错误] {e}")
            else:
                print(f"  [下载失败] {task['url']}")
                with open(os.path.join(novel_dir, "error_log.txt"), "a", encoding="utf-8") as log:
                    log.write(f"{task['name']}: {task['url']}\n")
            
            # 随机延时
            time.sleep(random.uniform(0.1, 0.3))

        print(f"\n[完成] 任务结束！本轮成功下载 {success_count} 章。")

if __name__ == "__main__":
    TARGET_URL = "https://www.uuks.org/b/73220/"
    BASE_PATH = r"E:\Programme\lncrawl\down" 

    print("=== 小说下载器启动 (智能增量更新版) ===")
    downloader = NovelDownloader(TARGET_URL, BASE_PATH)
    downloader.run()
    input("按回车键退出...")
