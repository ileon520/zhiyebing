import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import os
import io
import urllib.request

FONT_FILENAME = "wqy-microhei.ttc"

def get_font(font_size):
    """智能查找支持中文的字体，若云端缺乏中文字体则自动下载并缓存"""
    font_paths = [
        FONT_FILENAME,  # 本地缓存字体
        "simhei.ttf", "msyh.ttc", "simsun.ttc",  # 本地/Windows常见字体
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",  # Linux / Streamlit Cloud 常用中文字体
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/System/Library/Fonts/PingFang.ttc"  # Mac 字体
    ]
    
    # 1. 尝试从本地或系统已知路径读取
    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, font_size)
            except Exception:
                pass

    # 2. 如果云端完全找不到中文字体，自动从 Git 镜像下载标准开源中文字体文件
    font_url = "https://gitee.com/mirrors/wqy-microhei/raw/master/wqy-microhei.ttc"
    try:
        if not os.path.exists(FONT_FILENAME):
            with st.spinner("首次运行正在自动为您下载中文字体库，请稍候..."):
                urllib.request.urlretrieve(font_url, FONT_FILENAME)
        return ImageFont.truetype(FONT_FILENAME, font_size)
    except Exception:
        pass

    # 兜底默认字体
    return ImageFont.load_default()

def add_text_to_image(img, text, font_size, text_color, stroke_color, stroke_width, pos_y_percent):
    """在图片上绘制带发光/双色描边效果的中老年大字"""
    img = img.convert("RGB")
    draw = ImageDraw.Draw(img)
    width, height = img.size
    
    font = get_font(font_size)
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if not lines:
        return img

    # 计算多行文本的总高度
    line_heights = []
    line_widths = []
    for line in lines:
        try:
            bbox = font.getbbox(line)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1] + 20  # 行距加空隙
        except Exception:
            w, h = font_size * len(line), font_size + 20
        line_widths.append(w)
        line_heights.append(h)

    total_text_height = sum(line_heights)
    # 根据百分比计算文字起始垂直坐标
    start_y = int((height - total_text_height) * (pos_y_percent / 100.0))

    current_y = start_y
    for i, line in enumerate(lines):
        w = line_widths[i]
        x = (width - w) // 2  # 水平居中
        
        # 核心：使用 Pillow 的 stroke_width 与 stroke_fill 实现立体发光描边
        draw.text(
            (x, current_y), 
            line, 
            font=font, 
            fill=text_color, 
            stroke_width=stroke_width, 
            stroke_fill=stroke_color
        )
        current_y += line_heights[i]

    return img

def render_page():
    st.title("🌸 选项 4：中老年喜庆表情包制作")
    st.write("选择预设荷花/鲜花素材，一键为你添加喜庆立体大字表情包！")

    # 支持 images/ 目录下或根目录下的图片路径
    image_options = {
        "🪷 荷花素材 1 (flower01.jpg)": ["images/flower01.jpg", "flower01.jpg"],
        "🌺 鲜花素材 2 (flower02.jpg)": ["images/flower02.jpg", "flower02.jpg"],
        "🌸 鲜花素材 3 (flower03.jpg)": ["images/flower03.jpg", "flower03.jpg"],
        "🌹 鲜花素材 4 (flower04.jpg)": ["images/flower04.jpg", "flower04.jpg"],
    }

    col_control, col_preview = st.columns([1, 1])

    with col_control:
        st.subheader("⚙️ 制作参数设置")
        
        # 1. 素材选择
        selected_label = st.selectbox("1. 选择背景素材图片：", list(image_options.keys()))
        possible_paths = image_options[selected_label]
        
        # 寻找实际存在的图片路径
        actual_img_path = None
        for p in possible_paths:
            if os.path.exists(p):
                actual_img_path = p
                break

        # 2. 文字内容输入
        text_input = st.text_area(
            "2. 输入要添加的文字（支持换行）：", 
            value="之前的听力\n出报告啦", 
            height=100
        )

        # 3. 风格调色盘
        st.write("3. 文字与描边风格设置：")
        c1, c2 = st.columns(2)
        with c1:
            text_color = st.color_picker("文字主颜色", "#FFFF00")  # 默认靓丽金黄
        with c2:
            stroke_color = st.color_picker("描边发光颜色", "#0000FF")  # 默认鲜艳宝蓝

        # 🌟 调整：放大了字体上限与默认初始字号
        font_size = st.slider("字体大小", min_value=30, max_value=300, value=120, step=10)
        stroke_width = st.slider("描边粗细（越粗发光效果越明显）", min_value=0, max_value=30, value=10, step=1)
        pos_y_percent = st.slider("文字上下位置（0=最顶，50=居中，100=最底）", min_value=0, max_value=100, value=50, step=5)

    with col_preview:
        st.subheader("🖼️ 表情包效果实时预览")
        
        if actual_img_path:
            try:
                base_img = Image.open(actual_img_path)
                res_img = add_text_to_image(
                    base_img, 
                    text_input, 
                    font_size, 
                    text_color, 
                    stroke_color, 
                    stroke_width, 
                    pos_y_percent
                )
                
                # 展示合成好的图像
                st.image(res_img, caption="生成的表情包样式", use_container_width=True)
                
                # 导出图像流提供下载
                buf = io.BytesIO()
                res_img.save(buf, format="JPEG", quality=95)
                byte_im = buf.getvalue()

                st.download_button(
                    label="📥 点击一键保存/下载高清表情包",
                    data=byte_im,
                    file_name="中老年喜庆表情包.jpg",
                    mime="image/jpeg",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"处理图片时出错：{e}")
        else:
            st.warning("⚠️ 未找到对应的图片文件！请确保已经把 `flower01.jpg` ~ `flower04.jpg` 上传到了 GitHub 的 `images/` 文件夹中。")
