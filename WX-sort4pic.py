#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import shutil
import threading
import hashlib
from collections import defaultdict
from PIL import Image, UnidentifiedImageError
import imagehash
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("图片多条件筛选")
        self.geometry("720x540")
        self.resizable(False, False)

        # ------------ 主目录 ------------
        frm_path = ttk.Frame(self)
        frm_path.pack(pady=6, padx=10, fill='x')
        ttk.Label(frm_path, text="主目录：").pack(side='left')
        self.var_path = tk.StringVar()
        ttk.Entry(frm_path, textvariable=self.var_path, width=45).pack(side='left', padx=3)
        ttk.Button(frm_path, text="浏览...", command=self.choose_folder).pack(side='left')

        # ------------ Notebook ------------
        nb = ttk.Notebook(self)
        nb.pack(fill='both', expand=True, padx=10, pady=5)

        # ---- Tab1：固定分辨率（可滚动+全选） ----
        tab_fix = ttk.Frame(nb)
        nb.add(tab_fix, text="固定分辨率")
        self._build_fix_tab(tab_fix)

        # ---- Tab2：分类开关+阈值 ----
        tab_switch = ttk.Frame(nb)
        nb.add(tab_switch, text="分类开关")
        self._build_switch_tab(tab_switch)

        # ------------ 开始按钮 ------------
        self.btn_start = ttk.Button(self, text="开始处理", command=self.start_thread)
        self.btn_start.pack(pady=6)

        # ------------ 日志 ------------
        self.log = tk.Text(self, height=8, wrap='word')
        self.log.pack(padx=10, pady=3, fill='both', expand=True)

    # ------------------------------------------------------------------
    def _build_fix_tab(self, parent):
        # 顶部按钮
        frm_btn = ttk.Frame(parent)
        frm_btn.pack(fill='x', pady=2)
        ttk.Button(frm_btn, text="全选", width=8,
                   command=lambda: self._toggle_all_fix(True)).pack(side='left', padx=2)
        ttk.Button(frm_btn, text="取消全选", width=8,
                   command=lambda: self._toggle_all_fix(False)).pack(side='left', padx=2)

        # 画布+滚动条
        canvas = tk.Canvas(parent, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable = ttk.Frame(canvas)
        scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # 固定分辨率列表（宽度升序）
        fixed_list = [
            "400*320", "400*400", "420*336", "420*420", "486*388", "500*400",
            "540*432", "600*480", "600*599", "600*600", "620*1034", "630*504",
            "750*750", "750*800", "750*1000", "800*800", "884*1920", "919*1528",
            "1000*1000", "1024*1024", "1079*1719", "1080*1080", "1080*1483",
            "1080*2340", "1080*2396", "1080*2400", "1080*2408", "1170*2532",
            "1179*2556", "1200*1200", "1279*2774", "1280*1280", "1280*2774"
        ]
        self.fixed_items = {}
        for txt in fixed_list:
            var = tk.BooleanVar(value=True)
            self.fixed_items[txt] = var
            ttk.Checkbutton(scrollable, text=txt, variable=var).pack(anchor='w')

    def _toggle_all_fix(self, flag: bool):
        for var in self.fixed_items.values():
            var.set(flag)

    def _build_switch_tab(self, parent):
        # 开关
        self.chk_large = tk.BooleanVar(value=True)
        self.chk_small = tk.BooleanVar(value=True)
        self.chk_exact = tk.BooleanVar(value=True)
        self.chk_dup = tk.BooleanVar(value=True)      # 重复图
        self.chk_thumb = tk.BooleanVar(value=True)    # 缩略图

        frm_switch = ttk.LabelFrame(parent, text="分类开关")
        frm_switch.pack(fill='x', pady=5)
        ttk.Checkbutton(frm_switch, text="筛选超大图（最长边>多少像素）", variable=self.chk_large).pack(anchor='w')
        ttk.Checkbutton(frm_switch, text="筛选超小图（最短边>多少像素）", variable=self.chk_small).pack(anchor='w')
        ttk.Checkbutton(frm_switch, text="筛选固定分辨率图（按照前一页筛选，前一页不选也可在下面手填。）", variable=self.chk_exact).pack(anchor='w')
        ttk.Checkbutton(frm_switch, text="筛选重复图（HASH校验）", variable=self.chk_dup).pack(anchor='w')
        ttk.Checkbutton(frm_switch, text="筛选缩略图（imagehash库）", variable=self.chk_thumb).pack(anchor='w')

        # 阈值填写
        frm_thresh = ttk.LabelFrame(parent, text="阈值填写")
        frm_thresh.pack(fill='x', pady=5)

        frm_lt = ttk.Frame(frm_thresh)
        frm_lt.pack(fill='x', pady=2)
        ttk.Label(frm_lt, text="最短边 <").pack(side='left')
        self.var_lt = tk.StringVar(value='400')
        ttk.Entry(frm_lt, textvariable=self.var_lt, width=6).pack(side='left')
        ttk.Label(frm_lt, text="像素").pack(side='left')

        frm_gt = ttk.Frame(frm_thresh)
        frm_gt.pack(fill='x', pady=2)
        ttk.Label(frm_gt, text="最长边 >").pack(side='left')
        self.var_gt = tk.StringVar(value='2500')
        ttk.Entry(frm_gt, textvariable=self.var_gt, width=6).pack(side='left')
        ttk.Label(frm_gt, text="像素").pack(side='left')

        # 完全等于
        frm_ex = ttk.LabelFrame(parent, text="完全等于（宽*高，一行一条）")
        frm_ex.pack(fill='both', expand=True, pady=5)
        self.txt_exact = tk.Text(frm_ex, height=5)
        self.txt_exact.pack(fill='both', expand=True, padx=3, pady=3)
        self.txt_exact.insert('end', '1080*2400\n1080*2408')

    # ------------------------------------------------------------------
    def choose_folder(self):
        path = filedialog.askdirectory(title="请选择主文件夹")
        if path:
            self.var_path.set(path)

    def log_print(self, txt):
        self.log.insert('end', txt + '\n')
        self.log.see('end')

    def start_thread(self):
        if not self.var_path.get():
            messagebox.showwarning("提示", "请先选择主文件夹！")
            return
        self.btn_start.config(state='disabled')
        self.log.delete(1.0, 'end')
        threading.Thread(target=self.run_move, daemon=True).start()

    # ------------------------------------------------------------------
    def run_move(self):
        root = self.var_path.get()

        # 1. 解析完全等于
        exact = set()
        for line in self.txt_exact.get(1.0, 'end').splitlines():
            line = line.strip()
            if '*' in line:
                try:
                    exact.add(tuple(map(int, line.split('*', 1))))
                except ValueError:
                    pass
        for txt, var in self.fixed_items.items():
            if var.get():
                exact.add(tuple(map(int, txt.split('*'))))

        # 2. 阈值
        try:
            lt_th = int(self.var_lt.get()) if self.chk_small.get() else None
            gt_th = int(self.var_gt.get()) if self.chk_large.get() else None
        except ValueError:
            messagebox.showerror("错误", "阈值必须是整数！")
            self.btn_start.config(state='normal')
            return

        # 3. 目录
        base_other = os.path.join(root, '其他')
        dirs = {}
        for name, flag in [('超大图', self.chk_large), ('超小图', self.chk_small),
                           ('固定图', self.chk_exact), ('重复图', self.chk_dup),
                           ('缩略图', self.chk_thumb)]:
            if flag.get():
                dirs[name] = os.path.join(base_other, name)
        for d in dirs.values():
            os.makedirs(d, exist_ok=True)

        # 4. 收集图片
        self.log_print('开始扫描...')
        all_files = [os.path.join(dp, f)
                     for dp, _, files in os.walk(root)
                     if not dp.startswith(base_other)
                     for f in files
                     if f.lower().endswith(('.jpg', '.jpeg', '.png'))]

        # 5. 重复图（内容 MD5 相同）
        if self.chk_dup.get():
            md5_map = defaultdict(list)
            for fp in all_files:
                try:
                    with open(fp, 'rb') as bf:
                        digest = hashlib.md5(bf.read()).hexdigest()
                    md5_map[digest].append(fp)
                except Exception:
                    continue
            moved = 0
            for group in md5_map.values():
                if len(group) > 1:
                    keep = min(group, key=lambda x: os.path.basename(x))  # 文件名小的保留
                    for dup in set(group) - {keep}:
                        dst = os.path.join(dirs['重复图'], os.path.basename(dup))
                        base, ext = os.path.splitext(dst)
                        counter = 1
                        while os.path.exists(dst):
                            dst = f"{base}_{counter}{ext}"
                            counter += 1
                        shutil.move(dup, dst)
                        moved += 1
                        self.log_print(f'moved duplicate: {os.path.basename(dup)}')
            self.log_print(f'重复图处理完毕，移动 {moved} 张')

        # 6. 缩略图（内容相似，尺寸不同）
        if self.chk_thumb.get():
            hash_map = defaultdict(list)
            for fp in all_files:
                if not os.path.exists(fp):
                    continue
                try:
                    h = str(imagehash.average_hash(Image.open(fp)))
                    hash_map[h].append(fp)
                except Exception:
                    continue
            moved = 0
            for group in hash_map.values():
                if len(group) > 1:
                    group_sorted = sorted(group, key=lambda p: Image.open(p).size[0] * Image.open(p).size[1], reverse=True)
                    for dup in group_sorted[1:]:
                        dst = os.path.join(dirs['缩略图'], os.path.basename(dup))
                        base, ext = os.path.splitext(dst)
                        counter = 1
                        while os.path.exists(dst):
                            dst = f"{base}_{counter}{ext}"
                            counter += 1
                        shutil.move(dup, dst)
                        moved += 1
                        self.log_print(f'moved thumbnail: {os.path.basename(dup)}')
            self.log_print(f'缩略图处理完毕，移动 {moved} 张')

        # 7. 超大、超小、固定图
        counts = {k: 0 for k in dirs if k not in ('重复图', '缩略图')}
        for fp in all_files:
            if not os.path.exists(fp):
                continue
            try:
                with Image.open(fp) as im:
                    w, h = im.size
            except UnidentifiedImageError:
                continue
            max_side, min_side = max(w, h), min(w, h)
            target = None
            if self.chk_exact.get() and (w, h) in exact:
                target = '固定图'
            elif self.chk_large.get() and max_side > gt_th:
                target = '超大图'
            elif self.chk_small.get() and min_side < lt_th:
                target = '超小图'
            if target:
                dst = os.path.join(dirs[target], os.path.basename(fp))
                base, ext = os.path.splitext(dst)
                counter = 1
                while os.path.exists(dst):
                    dst = f"{base}_{counter}{ext}"
                    counter += 1
                shutil.move(fp, dst)
                counts[target] += 1
                self.log_print(f'moved: {os.path.basename(fp)}')

        self.log_print('全部处理完毕！')
        for k, v in counts.items():
            self.log_print(f'{k}: {v} 张')
        self.btn_start.config(state='normal')


if __name__ == '__main__':
    App().mainloop()