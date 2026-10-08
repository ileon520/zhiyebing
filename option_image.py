import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import os
import io
import urllib.request

FONT_FILENAME = "zcool_font.ttf"

def get_font(font_size):
    """智能获取中文字体：优先系统字体，次选自动下载并校验文件有效性"""
    font_paths = [
        FONT_FILENAME,
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "simhei.ttf", "msyh.ttc", "simsun.ttc",
        "/System/Library/Fonts/PingFang.ttc"
    ]
    
    # 1. 尝试使用本地或系统已有字体
    for path in font_paths:
        if os.path.exists(path):
            try:
                # 确保文件有效（大于 100KB），防止读取到下载失败的坏文件
                if os.path.getsize(path) > 100000:
                    return ImageFont.truetype(path, font_size)
                else:
                    os.remove(path)
            except Exception:
                pass

    # 2. 从可靠源下载适用于表情包的中文字体（站酷快乐体）
    font_url = "https://raw.githubusercontent.com/google/fonts/main/ofl/zcoolkuaile/ZCOOLKuaiLe-Regular.ttf"
    try:
        if not os.path.exists(FONT_FILENAME):
            req = urllib.request.Request(font_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=15) as response, open(FONT_FILENAME, 'wb') as out_file:
                out_file.write(response.read())
        
        if os.path.exists(FONT_FILENAME) and os.path.getsize(FONT_FILENAME) > 100000:
            return ImageFont.truetype(FONT_FILENAME, font_size)
    except Exception:
        pass

    return ImageFont.load_default()

def add_text_to_image(img, text, font_size, text_color, stroke_color, stroke_width, pos_y_percent):
    """在图片上绘制带发光/双色描边效果的大字"""
    img = img.convert("RGB")
    draw = ImageDraw.Draw(img)
    width, height = img.size
    
    font = get_font(font_size)
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if not lines:
        return img

    line_heights = []
    line_widths = []
    for line in lines:
        try:
            bbox = font.getbbox(line)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1] + 20
        except Exception:
            w, h = font_size * len(line), font_size + 20
        line_widths.append(w)
        line_heights.append(h)

    total_text_height = sum(line_heights)
    start_y = int((height - total_text_height) * (pos_y_percent / 100.0))

    current_y = start_y
    for i, line in enumerate(lines):
        w = line_widths[i]
        x = (width - w) // 2
        
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

    image_options = {
        "🪷 荷花素材 1 (flower01.jpg)": ["images/flower01.jpg", "flower01.jpg"],
        "🌺 鲜花素材 2 (flower02.jpg)": ["images/flower02.jpg", "flower02.jpg"],
        "🌸 鲜花素材 3 (flower03.jpg)": ["images/flower03.jpg", "flower03.jpg"],
        "🌹 鲜花素材 4 (flower04.jpg)": ["images/flower04.jpg", "flower04.jpg"],
    }

    col_control, col_preview = st.columns([1, 1])

    with col_control:
        st.subheader("⚙️ 制作参数设置")
        
        selected_label = st.selectbox("1. 选择背景素材图片：", list(image_options.keys()))
        possible_paths = image_options[selected_label]
        
        actual_img_path = None
        for p in possible_paths:
            if os.path.exists(p):
                actual_img_path = p
                break

        text_input = st.text_area(
            "2. 输入要添加的文字（支持换行）：", 
            value="之前的听力\n出报告啦", 
            height=100
        )

        st.write("3. 文字与描边风格设置：")
        c1, c2 = st.columns(2)
        with c1:
            text_color = st.color_picker("文字主颜色", "#FFFF00")
        with c2:
            stroke_color = st.color_picker("描边发光颜色", "#0000FF")

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
                
                st.image(res_img, caption="生成的表情包样式", use_container_width=True)
                
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
