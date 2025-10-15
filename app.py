#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
考研笔记复习网站主应用文件
"""

import os
import json
import numpy as np
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename

app = Flask(__name__)

# 配置
DATA_DIR = 'data'  # 数据目录
WEIGHTS_FILE = os.path.join(DATA_DIR, 'weights.json')  # 权重文件路径

# 确保数据目录存在
os.makedirs(DATA_DIR, exist_ok=True)

class ReviewSystem:
    """复习系统类，负责管理科目、图片和权重"""
    
    def __init__(self, data_dir=DATA_DIR, weights_file=WEIGHTS_FILE):
        """
        初始化复习系统
        
        Args:
            data_dir (str): 数据目录路径
            weights_file (str): 权重文件路径
        """
        self.data_dir = data_dir
        self.weights_file = weights_file
        self.weights = {}
        self.last_reviewed = {}  # 记录每个文件的最后复习时间
        self.review_intervals = {}  # 记录每个文件的复习间隔
        self.subject_mapping = {}  # 科目名称映射表
        self.load_weights()
        self.scan_subjects()
        self.create_subject_mapping()
    
    def scan_subjects(self):
        """
        扫描数据目录，检测科目文件夹及图片文件
        """
        # 获取所有科目目录
        subjects = [d for d in os.listdir(self.data_dir) 
                   if os.path.isdir(os.path.join(self.data_dir, d))]
        
        # 为新科目初始化权重和时间记录
        for subject in subjects:
            subject_path = os.path.join(self.data_dir, subject)
            if os.path.isdir(subject_path):
                # 获取该科目下的所有文件
                files = [f for f in os.listdir(subject_path)]
                
                # 为文件初始化权重和时间记录（不仅限于图片文件）
                for file in files:
                    image_key = f"{subject}/{file}"
                    if image_key not in self.weights:
                        self.weights[image_key] = 1.0  # 默认权重为1.0
                    if image_key not in self.last_reviewed:
                        self.last_reviewed[image_key] = None  # 默认未复习
                    if image_key not in self.review_intervals:
                        self.review_intervals[image_key] = 1.0  # 默认间隔为1天
        
        # 保存权重和时间记录
        self.save_weights()
    
    def create_subject_mapping(self):
        """
        创建科目名称映射表，使用编码替代中文科目名称以避免编码问题
        """
        # 获取所有科目
        subjects = self.get_subjects()
        
        # 为每个科目创建唯一编码
        for i, subject in enumerate(subjects):
            # 使用前缀+S+数字的方式创建编码
            encoded_name = f"S{i:03d}"
            self.subject_mapping[encoded_name] = subject
        
        # 更新权重数据中的科目名称
        self.update_weights_with_encoded_names()
    
    def update_weights_with_encoded_names(self):
        """
        将权重数据中的中文科目名称替换为编码
        """
        # 创建新的权重字典
        new_weights = {}
        new_last_reviewed = {}
        new_review_intervals = {}
        
        # 映射函数：将中文科目名替换为编码
        def encode_subject_name(key):
            if '/' in key:
                parts = key.split('/', 1)
                subject = parts[0]
                filename = parts[1]
                # 检查科目是否已经是编码格式(S+数字)
                if subject.startswith('S') and len(subject) == 4 and subject[1:].isdigit():
                    # 如果已经是编码格式，直接返回
                    return key
                # 查找科目对应的编码
                for encoded, original in self.subject_mapping.items():
                    if original == subject:
                        return f"{encoded}/{filename}"
                # 如果没有找到映射，创建新的编码
                encoded_name = f"S{len(self.subject_mapping):03d}"
                self.subject_mapping[encoded_name] = subject
                return f"{encoded_name}/{filename}"
            return key
        
        # 更新所有权重数据
        for key, value in self.weights.items():
            new_key = encode_subject_name(key)
            new_weights[new_key] = value
        
        for key, value in self.last_reviewed.items():
            new_key = encode_subject_name(key)
            new_last_reviewed[new_key] = value
        
        for key, value in self.review_intervals.items():
            new_key = encode_subject_name(key)
            new_review_intervals[new_key] = value
        
        # 替换原有的权重数据
        self.weights = new_weights
        self.last_reviewed = new_last_reviewed
        self.review_intervals = new_review_intervals
        
        # 保存更新后的权重数据
        self.save_weights()
    
    def decode_subject_name(self, encoded_name):
        """
        将编码的科目名称解码为中文名称
        
        Args:
            encoded_name (str): 编码的科目名称
            
        Returns:
            str: 解码后的中文科目名称
        """
        return self.subject_mapping.get(encoded_name, encoded_name)
    
    def get_decoded_subjects(self):
        """
        获取解码后的科目列表（用于显示）
        
        Returns:
            list: 解码后的科目名称列表
        """
        return list(self.subject_mapping.values())
    
    def load_weights(self):
        """
        从JSON文件加载权重、最后复习时间和复习间隔
        """
        try:
            if os.path.exists(self.weights_file):
                # 尝试不同的编码方式读取文件
                encodings = ['utf-8', 'gbk', 'gb2312']
                content = None
                
                for encoding in encodings:
                    try:
                        with open(self.weights_file, 'r', encoding=encoding) as f:
                            content = f.read().strip()
                            break  # 成功读取则跳出循环
                    except UnicodeDecodeError:
                        continue  # 尝试下一种编码
                
                # 如果所有编码都失败，则使用默认方式读取
                if content is None:
                    with open(self.weights_file, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read().strip()
                
                # 检查文件是否为空
                if not content:
                    print("权重文件为空")
                    self.weights = {}
                    self.last_reviewed = {}
                    self.review_intervals = {}
                    self.subject_mapping = {}
                    return
                
                # 解析JSON数据
                data = json.loads(content)
                
                # 确保data是一个字典
                if not isinstance(data, dict):
                    print("权重文件格式错误，不是字典类型")
                    self.weights = {}
                    self.last_reviewed = {}
                    self.review_intervals = {}
                    self.subject_mapping = {}
                    return
                
                # 加载科目映射表
                self.subject_mapping = data.get('subject_mapping', {})
                
                # 加载权重数据
                self.weights = data.get('weights', {}) if data.get('weights') is not None else {}
                self.last_reviewed = data.get('last_reviewed', {}) if data.get('last_reviewed') is not None else {}
                self.review_intervals = data.get('review_intervals', {}) if data.get('review_intervals') is not None else {}
                
                # 确保获取到的数据是字典类型
                if not isinstance(self.weights, dict):
                    self.weights = {}
                if not isinstance(self.last_reviewed, dict):
                    self.last_reviewed = {}
                if not isinstance(self.review_intervals, dict):
                    self.review_intervals = {}
                
                # 将字符串时间转换为datetime对象
                for key, value in self.last_reviewed.items():
                    if isinstance(value, str):
                        try:
                            self.last_reviewed[key] = datetime.fromisoformat(value)
                        except ValueError:
                            # 如果日期格式不正确，跳过该项
                            print(f"日期格式不正确，跳过: {key} = {value}")
                            pass
            else:
                print(f"权重文件 {self.weights_file} 不存在，将创建新的权重文件")
                self.weights = {}
                self.last_reviewed = {}
                self.review_intervals = {}
                self.subject_mapping = {}
        except FileNotFoundError:
            print(f"权重文件 {self.weights_file} 未找到，将创建新的权重文件")
            self.weights = {}
            self.last_reviewed = {}
            self.review_intervals = {}
            self.subject_mapping = {}
        except json.JSONDecodeError as e:
            print(f"权重文件 {self.weights_file} 格式错误: {e}，将创建新的权重文件")
            self.weights = {}
            self.last_reviewed = {}
            self.review_intervals = {}
            self.subject_mapping = {}
        except Exception as e:
            print(f"加载权重文件时出错: {e}，将创建新的权重文件")
            self.weights = {}
            self.last_reviewed = {}
            self.review_intervals = {}
            self.subject_mapping = {}
    
    def save_weights(self):
        """
        将权重数据和时间记录保存到文件
        """
        try:
            # 确保数据目录存在
            os.makedirs(os.path.dirname(self.weights_file), exist_ok=True)
            
            # 将datetime对象转换为字符串以便JSON序列化
            last_reviewed_serializable = {}
            for key, value in self.last_reviewed.items():
                if isinstance(value, datetime):
                    last_reviewed_serializable[key] = value.isoformat()
                else:
                    last_reviewed_serializable[key] = value
            
            # 确保所有数据都是可序列化的
            serializable_weights = {}
            for key, value in self.weights.items():
                # 确保键和值都是基本类型
                if isinstance(key, str) and isinstance(value, (int, float)):
                    serializable_weights[key] = value
            
            serializable_intervals = {}
            for key, value in self.review_intervals.items():
                # 确保键和值都是基本类型
                if isinstance(key, str) and isinstance(value, (int, float)):
                    serializable_intervals[key] = value
            
            # 准备要保存的数据
            data = {
                'subject_mapping': self.subject_mapping,  # 科目名称映射表
                'weights': serializable_weights,
                'last_reviewed': last_reviewed_serializable,
                'review_intervals': serializable_intervals
            }
            
            # 保存到JSON文件，确保使用UTF-8编码
            with open(self.weights_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存权重文件时出错: {e}")
    
    def get_subjects(self):
        """
        获取所有科目列表
        
        Returns:
            list: 科目名称列表
        """
        # 从数据目录中获取所有科目目录（只返回实际存在的目录）
        subjects_from_dir = set()
        try:
            for item in os.listdir(self.data_dir):
                item_path = os.path.join(self.data_dir, item)
                if os.path.isdir(item_path):
                    subjects_from_dir.add(item)
        except Exception as e:
            print(f"扫描科目目录时出错: {e}")
        
        return list(subjects_from_dir)
    
    def get_images_for_subject(self, subject):
        """
        获取指定科目的所有图片文件
        
        Args:
            subject (str): 科目名称
            
        Returns:
            list: 图片文件路径列表
        """
        images = []
        subject_path = os.path.join(self.data_dir, subject)
        
        if os.path.exists(subject_path):
            for file in os.listdir(subject_path):
                # 检查文件扩展名是否为图片格式
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                    images.append(f"{subject}/{file}")
        
        # 按照权重排序
        images.sort(key=lambda x: self.weights.get(x, 1.0), reverse=True)
        return images
    
    def get_all_files_for_subject(self, subject):
        """
        获取指定科目的所有文件
        
        Args:
            subject (str): 科目名称（可以是编码或中文名称）
            
        Returns:
            list: 文件名列表（不包含科目路径前缀）
        """
        # 如果传入的是编码，需要找到对应的中文名称来访问数据目录
        display_subject_name = subject
        encoded_subject_name = subject
        for encoded, original in self.subject_mapping.items():
            if original == subject:
                encoded_subject_name = encoded
                display_subject_name = subject  # 保持原样用于数据目录访问
                break
            elif encoded == subject:
                display_subject_name = original  # 使用中文名称访问数据目录
                break
        
        files = []
        # 使用中文名称查找数据目录
        subject_path = os.path.join(self.data_dir, display_subject_name)
        
        if os.path.exists(subject_path):
            for file in os.listdir(subject_path):
                files.append(file)
        
        # 按照权重排序，使用编码名称构造权重键
        files.sort(key=lambda x: self.weights.get(f"{encoded_subject_name}/{x}", 1.0), reverse=True)
        return files
    
    def update_weight(self, image_key, familiarity):
        """
        根据用户选择更新图片权重，基于间隔重复算法和遗忘曲线
        
        Args:
            image_key (str): 图片键名 (格式: "科目/图片名")
            familiarity (str): 熟悉程度 ("familiar", "blur", "strange")
        """
        if image_key not in self.weights:
            self.weights[image_key] = 1.0
        if image_key not in self.last_reviewed:
            self.last_reviewed[image_key] = None
        if image_key not in self.review_intervals:
            self.review_intervals[image_key] = 1.0
            
        # 记录当前复习时间
        current_time = datetime.now()
        self.last_reviewed[image_key] = current_time
        
        # 基于熟悉程度和间隔重复算法调整权重和复习间隔
        if familiarity == "familiar":
            # 熟悉：延长复习间隔，权重衰减
            self.review_intervals[image_key] = min(30.0, self.review_intervals[image_key] * 2.0)  # 最大间隔30天
            # 基于遗忘曲线的权重调整
            forgetting_rate = 0.1  # 掌握状态的遗忘率
            decay_factor = np.exp(-forgetting_rate)
            self.weights[image_key] *= decay_factor
        elif familiarity == "blur":
            # 模糊：稍微延长复习间隔，权重轻微衰减
            self.review_intervals[image_key] = max(1.0, self.review_intervals[image_key] * 1.2)
            # 权重轻微衰减
            self.weights[image_key] *= 0.95
        elif familiarity == "strange":
            # 陌生：缩短复习间隔，权重增加
            self.review_intervals[image_key] = max(0.1, self.review_intervals[image_key] * 0.5)
            # 权重增加
            self.weights[image_key] = min(10.0, self.weights[image_key] * 1.5)
        else:
            # 默认情况：轻微衰减
            self.weights[image_key] *= 0.9
            
        # 确保权重不会过低或过高
        self.weights[image_key] = max(0.1, min(10.0, self.weights[image_key]))
        
        # 保存权重和时间记录
        self.save_weights()
    
    def select_images_for_review(self, subject, count=30):
        """
        根据权重和时间间隔选择图片进行复习，实现智能间隔重复算法
        
        Args:
            subject (str): 科目名称
            count (int): 选择图片数量
            
        Returns:
            list: 选中的图片路径列表
        """
        # 获取该科目的所有图片
        images = self.get_images_for_subject(subject)
        
        if not images:
            return []
        
        current_time = datetime.now()
        # 计算每个图片的复习优先级
        priorities = []
        for img in images:
            # 获取权重值
            weight = self.weights.get(img, 1.0)
            
            # 获取上次复习时间和复习间隔
            last_reviewed = self.last_reviewed.get(img)
            review_interval = self.review_intervals.get(img, 1.0)
            
            # 如果从未复习过，优先级最高
            if last_reviewed is None:
                priority = 1000000  # 使用大数而不是无穷大
            else:
                # 计算距离下次复习的时间
                next_review_time = last_reviewed + timedelta(days=review_interval)
                time_until_review = (next_review_time - current_time).total_seconds()
                
                # 如果已经到了复习时间，优先级根据超时时间增加
                if time_until_review <= 0:
                    # 超时越久，优先级越高
                    priority = abs(time_until_review) + weight * 1000
                else:
                    # 未到复习时间，优先级根据权重和剩余时间计算
                    # 权重越高（越不熟悉），优先级越高
                    # 避免除零错误，确保分母不为0
                    time_in_hours = max(0.1, time_until_review / 3600)  # 转换为小时，最小值为0.1
                    priority = weight * 1000 / time_in_hours
            
            # 确保优先级为有效数值
            if not np.isfinite(priority):
                priority = 1.0
                
            priorities.append(priority)
        
        # 归一化优先级，确保不会出现NaN值
        total_priority = sum(priorities)
        if total_priority > 0 and np.isfinite(total_priority):
            probabilities = [p / total_priority for p in priorities]
        else:
            # 如果总优先级为0或无效，平均分配概率
            probabilities = [1.0 / len(priorities)] * len(priorities)
        
        # 确保概率数组中没有NaN或无穷大值
        probabilities = [p if np.isfinite(p) else 0 for p in probabilities]
        prob_sum = sum(probabilities)
        
        # 如果概率和为0，平均分配概率
        if prob_sum == 0:
            probabilities = [1.0 / len(probabilities)] * len(probabilities)
        else:
            # 归一化概率
            probabilities = [p / prob_sum for p in probabilities]
        
        # 根据优先级随机选择图片
        selected_indices = np.random.choice(
            len(images), 
            size=min(count, len(images)), 
            replace=False, 
            p=probabilities
        )
        
        return [images[i] for i in selected_indices]

# 创建全局复习系统实例
review_system = ReviewSystem()

# 添加静态文件路由，处理/data/路径下的文件访问
@app.route('/data/<path:filename>')
def data_files(filename):
    """
    处理/data/路径下的文件访问
    
    Args:
        filename (str): 文件路径
        
    Returns:
        Response: 文件响应
    """
    return send_from_directory(DATA_DIR, filename)

@app.route('/')
def index():
    """
    首页路由，显示所有科目按钮
    """
    subjects = review_system.get_subjects()
    return render_template('index.html', subjects=subjects)

@app.route('/subject/<subject_name>')
def subject_page(subject_name):
    """
    科目页面路由，显示复习数量选择界面
    
    Args:
        subject_name (str): 科目名称
    """
    return render_template('subject.html', subject_name=subject_name)

@app.route('/review/<subject_name>')
def review_page(subject_name):
    """
    复习页面路由，显示图片复习界面
    
    Args:
        subject_name (str): 科目名称
    """
    # 获取复习数量参数，默认30
    count = request.args.get('count', 30, type=int)
    
    # 选择图片进行复习
    images = review_system.select_images_for_review(subject_name, count)
    
    if not images:
        # 如果没有图片，重定向到科目页面
        return redirect(url_for('subject_page', subject_name=subject_name))
    
    return render_template('review.html', subject_name=subject_name, images=images, subject_mapping=review_system.subject_mapping)

@app.route('/api/update_weight', methods=['POST'])
def api_update_weight():
    """
    API接口，更新图片权重
    """
    data = request.get_json()
    image_key = data.get('image_key')
    familiarity = data.get('familiarity')
    weight = data.get('weight')
    
    if image_key and (familiarity or weight is not None):
        # 确保image_key使用编码后的科目名称
        if '/' in image_key:
            parts = image_key.split('/', 1)
            subject = parts[0]
            filename = parts[1]
            # 检查科目是否已经是编码格式
            if not subject.startswith('S') or len(subject) != 4:
                # 如果不是编码格式，查找对应的编码
                for encoded, original in review_system.subject_mapping.items():
                    if original == subject:
                        image_key = f"{encoded}/{filename}"
                        break
        
        if familiarity:
            # 根据熟悉程度调整权重
            review_system.update_weight(image_key, familiarity)
        elif weight is not None:
            # 直接设置权重值
            review_system.weights[image_key] = float(weight)
            review_system.save_weights()
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "error", "message": "参数不完整"}), 400

@app.route('/api/subjects')
def api_subjects():
    """
    API接口，获取所有科目列表
    """
    subjects = review_system.get_decoded_subjects()
    return jsonify({"subjects": subjects})

@app.route('/manage')
def manage_page():
    """
    管理页面路由，用于导入图片和创建新科目
    """
    subjects = review_system.get_decoded_subjects()
    return render_template('manage.html', subjects=subjects)

@app.route('/weight_management')
def weight_management():
    """
    权重管理界面路由
    """
    subjects = review_system.get_decoded_subjects()
    return render_template('weight_management.html', subjects=subjects)

@app.route('/statistics')
def statistics():
    """
    统计页面路由
    """
    return render_template('statistics.html')

@app.route('/api/create_subject', methods=['POST'])
def api_create_subject():
    """
    API接口，创建新科目
    """
    data = request.get_json()
    subject_name = data.get('subject_name')
    
    if subject_name:
        subject_path = os.path.join(DATA_DIR, subject_name)
        try:
            os.makedirs(subject_path, exist_ok=True)
            review_system.scan_subjects()  # 重新扫描科目
            return jsonify({"status": "success"})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
    else:
        return jsonify({"status": "error", "message": "科目名称不能为空"}), 400

@app.route('/api/import_image', methods=['POST'])
def api_import_image():
    """
    API接口，导入图片到指定科目
    """
    subject_name = request.form.get('subject_name')
    if 'image' not in request.files or not subject_name:
        return jsonify({"status": "error", "message": "参数不完整"}), 400
    
    image_file = request.files['image']
    if image_file.filename == '':
        return jsonify({"status": "error", "message": "未选择文件"}), 400
    
    if image_file:
        subject_path = os.path.join(DATA_DIR, subject_name)
        if not os.path.exists(subject_path):
            return jsonify({"status": "error", "message": "科目不存在"}), 400
        
        # 保存图片文件
        image_path = os.path.join(subject_path, image_file.filename)
        image_file.save(image_path)
        
        # 重新扫描科目以更新权重
        review_system.scan_subjects()
        
        return jsonify({"status": "success"})
    
    return jsonify({"status": "error", "message": "文件上传失败"}), 500

@app.route('/api/weights/<subject_name>', methods=['GET'])
def api_get_weights(subject_name):
    """
    获取指定科目的权重数据
    
    Args:
        subject_name (str): 科目名称
        
    Returns:
        JSON: 包含文件名和权重的字典
    """
    try:
        # 查找编码后的科目名称
        encoded_subject_name = subject_name
        # 如果传入的是中文名称，需要找到对应的编码
        for encoded, original in review_system.subject_mapping.items():
            if original == subject_name:
                encoded_subject_name = encoded
                break
        
        files = review_system.get_all_files_for_subject(encoded_subject_name)
        weights = {}
        for file in files:
            # 构造完整的文件路径键，使用编码后的科目名称
            full_key = f"{encoded_subject_name}/{file}"
            # 获取文件的权重，如果不存在则默认为1.0
            weights[file] = review_system.weights.get(full_key, 1.0)
        return jsonify(weights)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/statistics', methods=['GET'])
def api_statistics():
    """
    获取统计信息的API接口
    
    Returns:
        JSON: 包含统计信息的字典
    """
    try:
        subjects = review_system.get_subjects()
        decoded_subjects = review_system.get_decoded_subjects()
        subject_stats = {}
        total_files = 0
        total_weight = 0
        weight_count = 0
        total_reviews = 0
        pending_count = 0
        mastered_count = 0
        needs_review_count = 0
        strange_count = 0
        intervals = []
        
        # 定义状态阈值
        MASTERED_THRESHOLD = 0.5  # 权重低于此值认为已掌握
        NEEDS_REVIEW_THRESHOLD = 2.0  # 权重在此值之间认为需巩固
        STRANGE_THRESHOLD = 3.0  # 权重高于此值认为是陌生内容
        
        # 计算每个科目的统计数据
        for subject in subjects:
            files = review_system.get_all_files_for_subject(subject)
            file_count = len(files)
            total_files += file_count
            
            # 初始化各状态计数器
            subject_pending = 0
            subject_mastered = 0
            subject_needs_review = 0
            subject_strange = 0
            
            # 计算该科目的总权重和平均权重
            subject_total_weight = 0
            for file in files:
                # 使用编码后的科目名称构造文件键
                encoded_subject_name = subject
                for encoded, original in review_system.subject_mapping.items():
                    if original == subject:
                        encoded_subject_name = encoded
                        break
                
                file_key = f"{encoded_subject_name}/{file}"
                weight = review_system.weights.get(file_key, 1.0)
                subject_total_weight += weight
                total_weight += weight
                weight_count += 1
                
                # 根据权重值判断状态
                if weight < MASTERED_THRESHOLD:
                    subject_mastered += 1
                elif weight < NEEDS_REVIEW_THRESHOLD:
                    subject_needs_review += 1
                elif weight < STRANGE_THRESHOLD:
                    subject_strange += 1
                else:
                    subject_strange += 1  # 权重很高的内容也认为是陌生内容
                
                # 统计复习间隔
                if file_key in review_system.review_intervals:
                    interval = review_system.review_intervals[file_key]
                    intervals.append(interval)
            
            # 累计各状态文件数量
            pending_count += subject_pending
            mastered_count += subject_mastered
            needs_review_count += subject_needs_review
            strange_count += subject_strange
            
            # 更新总复习次数
            total_reviews += subject_mastered + subject_needs_review + subject_strange
            
            # 获取解码后的科目名称用于显示
            decoded_subject_name = review_system.decode_subject_name(subject)
            average_weight = subject_total_weight / file_count if file_count > 0 else 0
            subject_stats[decoded_subject_name] = {
                "file_count": file_count,
                "total_weight": subject_total_weight,
                "average_weight": average_weight,
                "pending_count": subject_pending,
                "mastered_count": subject_mastered,
                "needs_review_count": subject_needs_review,
                "strange_count": subject_strange
            }
        
        # 计算全局统计数据
        global_average_weight = total_weight / weight_count if weight_count > 0 else 0
        
        # 计算复习间隔统计数据
        average_interval = sum(intervals) / len(intervals) if intervals else 0
        max_interval = max(intervals) if intervals else 0
        min_interval = min(intervals) if intervals else 0
        
        stats = {
            "total_subjects": len(subjects),
            "total_files": total_files,
            "total_weight": total_weight,
            "average_weight": global_average_weight,
            "total_reviews": total_reviews,
            "pending_count": pending_count,
            "mastered_count": mastered_count,
            "needs_review_count": needs_review_count,
            "strange_count": strange_count,
            "average_interval": average_interval,
            "max_interval": max_interval,
            "min_interval": min_interval,
            "subject_stats": subject_stats
        }
        
        return jsonify({
            "subjects": decoded_subjects,
            "stats": stats
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)