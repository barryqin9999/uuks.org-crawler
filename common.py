# -*- coding: utf-8 -*-
import re
import os
import json

def validate_filename(filename):
    """去除文件名中的非法字符"""
    if not filename:
        return "untitled"
    # 替换非法字符为下划线
    cleaned = re.sub(r'[\\/:*?"<>|]', '_', filename).strip()
    return cleaned if cleaned else "output_file"

def clean_title(text):
    """清洗章节标题"""
    if not text:
        return ""
    match = re.search(r'(第[0-9零一二三四五六七八九十百千万两]+章.+)', text)
    if match:
        return match.group(1).strip()
    return text.strip()

def load_json(path):
    """读取JSON文件"""
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[警告] 读取JSON失败 {path}: {e}")
            return None
    return None

def save_json(path, data):
    """保存JSON文件"""
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[错误] 保存JSON失败 {path}: {e}")

def get_download_config(default_base_path):
    """
    交互式获取下载配置
    """
    print("-" * 50)
    print("   全网小说通用下载配置导向")
    print("-" * 50)

    # 1. 获取 URL 或 书号
    while True:
        user_input = input("请输入小说【目录页链接】或【uuks书号】: ").strip()
        if not user_input:
            print("输入不能为空，请重新输入。")
            continue
        
        if user_input.isdigit():
            target_url = f"https://www.uuks.org/b/{user_input}/"
            print(f"[系统] 检测到书号，自动转换为链接: {target_url}")
        elif "http" in user_input:
            target_url = user_input
        else:
            print("输入格式不正确，请输入完整网址或纯数字书号。")
            continue
        break

    # 2. 获取自定义书名（可选）
    print("\n[可选] 默认会自动从网页抓取书名建立文件夹。")
    manual_name = input("如需自定义文件夹名，请直接输入(回车跳过): ").strip()
    if manual_name:
        manual_name = validate_filename(manual_name)
        print(f"[系统] 将使用自定义文件夹名: {manual_name}")

    # 3. 确认保存路径
    if not os.path.exists(default_base_path):
        try:
            os.makedirs(default_base_path)
        except:
            pass
    
    return target_url, manual_name, default_base_path
