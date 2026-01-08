# -*- coding: utf-8 -*-
import os
from common import load_json, save_json, validate_filename

class TextCleaner:
    def __init__(self, base_path):
        self.base_path = base_path

    def run(self, specific_book=None):
        """
        修复文件名的主逻辑：
        将下载下来的文件（可能是乱序或旧名）按照 catalog.json 的顺序重命名。
        """
        if not specific_book:
            print("[错误] 未指定书籍。")
            return

        book_dir = os.path.join(self.base_path, specific_book)
        json_path = os.path.join(book_dir, 'catalog.json')

        if not os.path.exists(json_path):
            print(f"[错误] 找不到目录文件: {json_path}")
            return

        data = load_json(json_path)
        chapters = data['chapters']
        
        # === 1. 建立本地文件索引 ===
        # 目的：无论文件名怎么变，只要包含"标题"，就能找到它
        local_files = os.listdir(book_dir)
        existing_map = {}
        for f in local_files:
            if not f.endswith('.txt'): continue
            if f == 'error_log.txt': continue
            
            # 尝试提取标题部分
            clean_name = f.replace('.txt', '')
            
            # 策略A: 如果文件名是 "001_第一章"，提取 "第一章"
            if '_' in clean_name:
                parts = clean_name.split('_', 1)
                # 只有当前面是数字时，才认为是序号
                if parts[0].isdigit():
                    key = parts[1] 
                else:
                    key = clean_name
            else:
                key = clean_name
            
            existing_map[key] = f
            existing_map[clean_name] = f # 同时存完整名作为备份

        # === 2. 计算序号宽度 ===
        width = len(str(len(chapters)))
        if width < 4: width = 4 # 默认最少4位，如 0001

        renamed_count = 0
        linked_count = 0
        
        print(f"正在整理书籍: {specific_book}")

        for idx, ch in enumerate(chapters):
            raw_title = ch['title']
            safe_title = validate_filename(raw_title)
            
            # 期望的目标文件名
            num_str = str(idx + 1).zfill(width)
            target_name = f"{num_str}_{safe_title}.txt"
            target_path = os.path.join(book_dir, target_name)
            
            # 更新 JSON 记录
            ch['file_name'] = target_name
            
            # 情况A: 目标文件已经存在
            if os.path.exists(target_path):
                linked_count += 1
                continue
                
            # 情况B: 目标不存在，去现有的文件里找
            # 优先匹配 safe_title，其次匹配 raw_title
            candidate = existing_map.get(safe_title) or existing_map.get(raw_title)
            
            if candidate:
                old_path = os.path.join(book_dir, candidate)
                # 防止大小写造成的重名冲突 (Windows下是不区分大小写的)
                if old_path.lower() == target_path.lower() and old_path != target_path:
                    os.rename(old_path, old_path + ".tmp")
                    old_path = old_path + ".tmp"

                try:
                    os.rename(old_path, target_path)
                    renamed_count += 1
                except OSError as e:
                    print(f"  [重命名失败] {candidate} -> {target_name}: {e}")
        
        # 保存修正后的目录结构
        save_json(json_path, data)
        
        if renamed_count > 0:
            print(f"[整理完成] 修正了 {renamed_count} 个文件的命名。")
        else:
            print("[整理完成] 文件结构正常，无需变动。")

if __name__ == "__main__":
    # 测试代码
    cleaner = TextCleaner("novels")
    # cleaner.run("测试书籍名")
    pass
