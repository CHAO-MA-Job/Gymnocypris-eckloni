# -*- coding: utf-8 -*-
"""export_900dpi.py —— 把手稿成品图无损导出为 900 DPI PNG。

做三件事（不改像素、不重采样）：
  1. 将 DPI 元数据设为 900（原 563/600 是导出时随手设的，与像素量无关）；
  2. RGBA 图在**白底**上合成，避免透明背景在 Word/PDF 中渲染成黑块；
  3. 报告导出后的物理尺寸与"在期刊常见栏宽下的等效 DPI"，用于判断是否真的够。

为什么不做放大（重采样）：
  DPI = 像素 ÷ 英寸。放大只会插值出像素，不产生新细节，属伪造分辨率。
  若某图在目标栏宽下确实不足 900 DPI，正确做法是**从原始出图脚本按 dpi=900 重绘**。

用法
    python export_900dpi.py                 # 处理 05_figues/fig1..7.png
    python export_900dpi.py --suffix _900dpi
"""
import argparse
import os
import sys

from PIL import Image

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
Image.MAX_IMAGE_PIXELS = None

HERE = os.path.dirname(os.path.abspath(__file__))
FIGDIR = os.path.abspath(os.path.join(HERE, '..', '..', '05_figues'))
TARGET_DPI = 900
# 期刊常见栏宽（英寸）：单栏 8.5 cm、1.5 栏 14 cm、整栏 17.6 cm（MDPI 常用上限）
WIDTHS_IN = {'single 8.5cm': 3.35, 'onehalf 14cm': 5.51, 'full 17.6cm': 6.93}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--suffix', default='_900dpi')
    ap.add_argument('--names', nargs='*', default=['fig%d' % i for i in range(1, 8)])
    args = ap.parse_args()

    print('%-10s %-14s %-14s %-12s %s' % ('file', 'pixels(before)', 'pixels(after)',
                                          'size@900dpi', 'effective DPI at 8.5/14/17.6 cm'))
    for stem in args.names:
        src = os.path.join(FIGDIR, stem + '.png')
        if not os.path.exists(src):
            print('%-10s 缺失' % stem)
            continue
        im = Image.open(src)
        before = im.size
        if im.mode in ('RGBA', 'LA', 'P'):
            im = im.convert('RGBA')
            bg = Image.new('RGB', im.size, (255, 255, 255))
            bg.paste(im, mask=im.split()[-1])
            im = bg
        elif im.mode != 'RGB':
            im = im.convert('RGB')
        dst = os.path.join(FIGDIR, stem + args.suffix + '.png')
        im.save(dst, format='PNG', dpi=(TARGET_DPI, TARGET_DPI))
        eff = ' / '.join('%.0f' % (before[0] / w) for w in WIDTHS_IN.values())
        print('%-10s %-14s %-14s %-12s %s' % (
            stem, '%dx%d' % before, '%dx%d' % im.size,
            '%.2f x %.2f in' % (im.size[0] / TARGET_DPI, im.size[1] / TARGET_DPI), eff))
        im.close()
    print('\n输出目录:', FIGDIR)


if __name__ == '__main__':
    main()
