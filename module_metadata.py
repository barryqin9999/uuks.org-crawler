# -*- coding: utf-8 -*-
import re
import time
import requests

class MetadataFetcher:
    def __init__(self, page_driver):
        self.page = page_driver

    def _check_cloudflare(self):
        if "Just a moment" in self.page.title or "验证" in self.page.title:
            print("\n[注意] 触发 Cloudflare 盾，等待 10 秒自动验证...\n")
            time.sleep(10)

    def fetch_via_pc(self, book_id):
        """
        核心功能：输入ID，转换为www链接，采集5大核心要素
        """
        if not book_id: return None

        pc_url = f"https://www.uuks.org/b/{book_id}/"
        print(f"[爬虫] 正在访问 PC 详情页: {pc_url}")
        
        self.page.get(pc_url)
        time.sleep(2)
        self._check_cloudflare()

        # 初始化数据结构
        meta = {
            "title": "未知书籍",
            "author": "未知",
            "description": "暂无简介",
            "publish_date": "2000-01-01", 
            "cover_url": "",
            "book_id": book_id
        }

        try:
            # === A. 书名 (保留原逻辑) ===
            h1 = self.page.ele('tag:h1')
            if h1:
                raw = h1.text.strip()
                if '_' in raw: raw = raw.split('_')[0]
                meta['title'] = re.sub(r'[\\/:*?"<>|]', '_', raw).strip()

            # === B & D. 作者与简介 (关键修改：从混合文本块中正则提取) ===
            # 定位包含“作者：”的元素，获取其父级的完整文本块
            target_ele = self.page.ele('text:作者：') or self.page.ele('text:作者:')
            
            if target_ele:
                # 这一步会拿到包含 书名、作者、简介、最新章节 等的一大段文字
                block_text = target_ele.parent().text
                
                # 1. 精准提取作者
                # 逻辑：匹配 "作者：" 或 "作者:" 开头，捕获非换行字符，直到遇到换行符或字符串结束
                auth_match = re.search(r'作者[：:]\s*(.*?)(?:\n|\r|$)', block_text)
                if auth_match:
                    meta['author'] = auth_match.group(1).strip()

                # 2. 精准提取简介
                # 逻辑：匹配 "简介：" 之后的所有内容([\s\S]* 包含换行)
                desc_match = re.search(r'简介[：:]\s*([\s\S]*)', block_text)
                if desc_match:
                    full_desc = desc_match.group(1).strip()
                    
                    # 3. 简介清洗：去掉后面的“最新章节”、“更新时间”或分隔线
                    # 只要遇到这些词，就切断
                    clean_desc = re.split(r'(最新章节|更新时间|－－－|====)', full_desc)[0]
                    meta['description'] = clean_desc.strip()

            # 如果上面没提取到简介，再尝试备用方案 (针对某些只有 #bookintro 的情况)
            if meta['description'] == "暂无简介":
                desc_ele = self.page.ele('#bookintro') or self.page.ele('.book-intro')
                if desc_ele:
                    meta['description'] = desc_ele.text.strip()

            # === C. 出版时间 (源自网页的更新时间) ===
            time_ele = self.page.ele('text:更新时间：') or self.page.ele('text:更新时间:')
            if time_ele:
                full_text = time_ele.parent().text
                match = re.search(r'(\d{4}-\d{2}-\d{2}.*)', full_text)
                if match:
                    meta['publish_date'] = match.group(1).strip()

            # === E. 书封面图片 ===
            img = self.page.ele('.book-img img') or self.page.ele('div.pic img')
            if img:
                meta['cover_url'] = img.link 
                if not meta['cover_url']:
                    meta['cover_url'] = img.attr('src')

            return meta

        except Exception as e:
            print(f"[警告] 元数据采集部分失败: {e}")
            if meta['title'] != "未知书籍": return meta
            return None

    def download_cover(self, url, save_path):
        if not url or not url.startswith('http'): 
            print("[忽略] 无效的封面链接")
            return
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                with open(save_path, 'wb') as f:
                    f.write(resp.content)
                print("[成功] 封面已下载")
        except Exception as e:
            print(f"[失败] 封面下载出错: {e}")
