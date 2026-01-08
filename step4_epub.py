# -*- coding: utf-8 -*-
import os
import time
import requests
import re
from ebooklib import epub
from common import load_json, save_json, validate_filename

# 引入 Step0 的交互类
try:
    from step0_metadata import MetadataInteractive
except ImportError:
    MetadataInteractive = None

class EpubAdvancedGenerator:
    def __init__(self, base_path):
        self.base_path = base_path

    def _download_cover(self, url, save_path):
        """辅助方法：下载封面图片"""
        if not url or not url.startswith('http'):
            return False
        
        print(f"[系统] 正在尝试下载封面: {url}")
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                with open(save_path, 'wb') as f:
                    f.write(res.content)
                print("[成功] 封面已下载。")
                return True
            else:
                print(f"[失败] 下载返回状态码: {res.status_code}")
                return False
        except Exception as e:
            print(f"[出错] 封面下载异常: {e}")
            return False

    def _manual_verify_modify(self, meta, cover_path):
        """人工核对与修改"""
        while True:
            # 自动补全封面
            if not os.path.exists(cover_path):
                url = meta.get('cover_url')
                if url:
                    self._download_cover(url, cover_path)

            pub_date = meta.get('publish_date') or meta.get('update_time') or '未知'
            has_cover = os.path.exists(cover_path)
            cover_status = "[已存在]" if has_cover else "[缺失]"
            desc = meta.get('description', '')
            
            print("\n" + "="*50)
            print(f"【 EPUB 元数据最终核对 】")
            print("-" * 50)
            print(f" [1] 书名:     {meta.get('title', '未知')}")
            print(f" [2] 作者:     {meta.get('author', '未知')}")
            print(f" [3] 更新时间: {pub_date}") 
            print(f" [4] 封面状态: {cover_status}")
            print(f" [5] 简介长度: {len(desc)} 字")
            print("="*50)
            
            print("指令: [Enter]确认生成  [M]修改信息  [Q]退出")
            choice = input("请选择: ").strip().lower()

            if choice == 'm':
                print("\n--- 快速修正模式 (直接回车保持原值) ---")
                
                new_t = input(f"书名 [{meta.get('title', '')}]: ").strip()
                if new_t: meta['title'] = new_t
                
                new_a = input(f"作者 [{meta.get('author', '')}]: ").strip()
                if new_a: meta['author'] = new_a
                
                # 修改封面 URL
                new_url = input(f"新封面URL (回车跳过): ").strip()
                if new_url.startswith('http'):
                    meta['cover_url'] = new_url
                    if os.path.exists(cover_path):
                        try: os.remove(cover_path)
                        except: pass
                
                print("--- 信息已更新 ---")
                continue
            
            elif choice == 'q':
                return None
            else:
                if 'publish_date' not in meta:
                    meta['publish_date'] = pub_date
                return meta

    def run(self, specific_book=None):
        if not specific_book:
            print("[错误] 未指定书籍目录名。")
            return

        novel_dir = os.path.join(self.base_path, specific_book)
        catalog_path = os.path.join(novel_dir, 'catalog.json')
        info_path = os.path.join(novel_dir, 'book_info.json')
        cover_path = os.path.join(novel_dir, 'cover.jpg')
        
        # 1. 基础检查
        if not os.path.exists(catalog_path):
            print(f"[错误] 目录文件不存在: {catalog_path}")
            return
        
        catalog_data = load_json(catalog_path)
        chapters = catalog_data.get('chapters', [])
        book_url = catalog_data.get('url', '')

        # 2. 元数据检查
        if not os.path.exists(info_path):
            print(f"[提示] 缺少 book_info.json，尝试调用采集工具...")
            if MetadataInteractive:
                step0 = MetadataInteractive(self.base_path)
                step0.run(book_url)
            else:
                print("[警告] step0_metadata 模块缺失，使用默认元数据")
                save_json(info_path, {"title": specific_book, "author": "Unknown"})
        
        if not os.path.exists(info_path):
            print("[错误] 无法获取元数据，请检查网络或手动创建 book_info.json")
            return

        # 3. 读取并核对
        meta = load_json(info_path)
        meta = self._manual_verify_modify(meta, cover_path)
        if not meta:
            print("[取消] 已放弃生成。")
            return
            
        save_json(info_path, meta)

        # === 4. 生成 EPUB ===
        
        safe_book_title = validate_filename(meta['title'])
        if not safe_book_title:
            safe_book_title = "output_book"

        output_filename = f"{safe_book_title}.epub"
        output_file_path = os.path.join(novel_dir, output_filename)
        abs_path = os.path.abspath(output_file_path)

        print(f"\n[开始生成] 目标路径: {abs_path}")
        
        book = epub.EpubBook()
        book.set_identifier(str(int(time.time())))
        book.set_title(meta['title'])
        book.set_language('zh')
        book.add_author(meta['author'])
        
        # 封面
        if os.path.exists(cover_path):
            try:
                with open(cover_path, 'rb') as f:
                    book.set_cover("cover.jpg", f.read())
            except Exception as e:
                print(f"[警告] 封面读取失败: {e}")
        
        # 简介
        desc_text = meta.get('description', '暂无简介')
        desc_html = desc_text.replace('\n', '<br/>')
        pub_date_str = meta.get('publish_date', '')
        
        intro_html = f"""
            <div style="text-align: center;">
                <h1>{meta['title']}</h1>
                <p><b>作者：</b>{meta['author']}</p>
                <p><b>更新：</b>{pub_date_str}</p>
            </div>
            <hr/>
            <h3>简介</h3>
            <p style="line-height:1.5;">{desc_html}</p>
        """
        c_intro = epub.EpubHtml(title='书籍信息', file_name='intro.xhtml', lang='zh')
        c_intro.content = intro_html
        book.add_item(c_intro)

        # 章节
        epub_items = []
        valid_count = 0
        missing_count = 0
        print(f"[打包] 正在处理 {len(chapters)} 个章节...")
        
        # 计算序号宽度，用于备用文件名匹配
        width = len(str(len(chapters)))
        width = max(width, 4)

        for idx, ch in enumerate(chapters):
            # 1. 尝试使用 JSON 中记录的文件名
            file_name = ch.get('file_name', '')
            txt_file = os.path.join(novel_dir, file_name)
            
            # 2. 如果文件不存在，尝试构建“安全文件名”进行备选查找
            # (防止 Step1 记录了非法字符，但 Step2 保存时已经替换成了下划线)
            if not os.path.exists(txt_file):
                safe_title = validate_filename(ch['title'])
                num_str = str(idx + 1).zfill(width)
                backup_name = f"{num_str}_{safe_title}.txt"
                backup_path = os.path.join(novel_dir, backup_name)
                
                if os.path.exists(backup_path):
                    txt_file = backup_path # 找到了备份文件
                    print(f"[修正] 章节 {idx+1} 使用修正后的文件名: {backup_name}")
                else:
                    print(f"!!! [缺失] 找不到文件 (第{idx+1}章): {file_name}")
                    missing_count += 1
                    continue
            
            try:
                with open(txt_file, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                print(f"[错误] 读取文件失败 {txt_file}: {e}")
                continue
            
            lines = [f"<p>{line.strip()}</p>" for line in content.split('\n') if line.strip()]
            html_body = "".join(lines)
            
            # 兼容 EPUB 文件名规范
            c = epub.EpubHtml(title=ch['title'], file_name=f"ch_{valid_count:04d}.xhtml", lang='zh')
            c.content = f"<h2>{ch['title']}</h2>{html_body}"
            book.add_item(c)
            epub_items.append(c)
            valid_count += 1

        print("-" * 30)
        print(f"处理结果: 成功 {valid_count} 章 / 缺失 {missing_count} 章")

        if valid_count == 0:
            print("[错误] 未找到任何有效的章节文件，停止生成。")
            print("请尝试运行 [2. 下载] 步骤来补充缺失的文件。")
            return

        book.toc = [c_intro] + epub_items
        book.spine = ['nav', c_intro] + epub_items
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        try:
            epub.write_epub(output_file_path, book, {})
            print("="*50)
            print(f" [成功] EPUB 已生成！")
            print(f" [位置] {abs_path}")
            if missing_count > 0:
                print(f" [注意] 有 {missing_count} 个章节因文件缺失未被打包，请运行下载步骤补充。")
            print("="*50)
        except Exception as e:
            print(f"[失败] 写入文件时出错: {e}")
            print("请检查文件是否被占用，或文件名包含特殊字符。")
