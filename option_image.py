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
    
    for path in font_paths:
        if os.path.exists(path):
            try:
                if os.path.getsize(path) > 100000:
                    return ImageFont.truetype(path, font_size)
                else:
                    os.remove(path)
            except Exception:
                pass

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

def get_dark_color(hex_color, factor=0.35):
    """根据主字体颜色，自动生成同色系的暗系阴影（如鲜红->暗红，宝蓝->暗蓝）"""
    hex_color = hex_color.lstrip('#')
    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return f"#{int(r * factor):02x}{int(g * factor):02x}{int(b * factor):02x}"
    except Exception:
        return "#222222"

def add_multi_text_to_image(img, text_items):
    """在图片上绘制多组独立风格的文字，并实现整体绝对垂直与水平居中"""
    img = img.convert("RGB")
    draw = ImageDraw.Draw(img)
    img_w, img_h = img.size

    # 1. 预先计算所有文字组的总高度（含宽行间距）
    block_gap = 40  # 不同文字组之间的空隙
    total_content_height = 0
    calculated_blocks = []

    for item in text_items:
        text = item["text"]
        font_size = item["font_size"]
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        if not lines:
            continue

        font = get_font(font_size)
        line_gap = int(font_size * 0.35)  # 宽行间距：取字号的 35% 作为行与行空隙

        line_info = []
        block_height = 0

        for i, line in enumerate(lines):
            try:
                bbox = font.getbbox(line)
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
            except Exception:
                w, h = font_size * len(line), font_size

            line_info.append({"line": line, "w": w, "h": h})
            block_height += h + (line_gap if i < len(lines) - 1 else 0)

        calculated_blocks.append({
            "lines": line_info,
            "font": font,
            "item": item,
            "block_height": block_height,
            "line_gap": line_gap
        })

        total_content_height += block_height

    if not calculated_blocks:
        return img

    total_content_height += block_gap * (len(calculated_blocks) - 1)

    # 2. 计算整体起始 Y 坐标，确保 1 行、2 行或 3 行时总体始终居中
    current_y = (img_h - total_content_height) // 2

    # 3. 逐组渲染文字（暗影 + 亮黄描边 + 主字）
    for block in calculated_blocks:
        font = block["font"]
        item = block["item"]
        line_gap = block["line_gap"]
        
        # 自动获取同色系暗色阴影
        dark_shadow_color = get_dark_color(item["text_color"])
        shadow_offset = max(6, int(item["font_size"] * 0.05))  # 立体立体阴影偏移量

        for line_data in block["lines"]:
            line = line_data["line"]
            w = line_data["w"]
            h = line_data["h"]
            x = (img_w - w) // 2  # 水平居中

            # A. 绘制底层同色暗系立体阴影
            draw.text(
                (x + shadow_offset, current_y + shadow_offset),
                line,
                font=font,
                fill=dark_shadow_color,
                stroke_width=item["stroke_width"],
                stroke_fill=dark_shadow_color
            )

            # B. 绘制上层主文字与靓黄描边
            draw.text(
                (x, current_y),
                line,
                font=font,
                fill=item["text_color"],
                stroke_width=item["stroke_width"],
                stroke_fill=item["stroke_color"]
            )

            current_y += h + line_gap

        current_y += block_gap  # 加上组间距

    return img

def render_page():
    st.title("🌸 选项 4：中老年喜庆表情包制作")
    st.write("支持自定义多行不同颜色的霸气大字，带亮黄描边与同色系暗影！")

    image_options = {
        "🪷 荷花素材 1 (flower01.jpg)": ["images/flower01.jpg", "flower01.jpg"],
        "🌺 鲜花素材 2 (flower02.jpg)": ["images/flower02.jpg", "flower02.jpg"],
        "🌸 鲜花素材 3 (flower03.jpg)": ["images/flower03.jpg", "flower03.jpg"],
        "🌹 鲜花素材 4 (flower04.jpg)": ["images/flower04.jpg", "flower04.jpg"],
    }

    # 初始化动态多行数据列表（默认包含第 1 组）
    if "text_items" not in st.session_state:
        st.session_state.text_items = [
            {
                "text": "之前的听力\n出报告啦",
                "font_size": 270,
                "text_color": "#FF0000",   # 默认红色
                "stroke_color": "#FFFF00", # 默认黄色描边
                "stroke_width": 16
            }
        ]

    col_control, col_preview = st.columns([1, 1])

    with col_control:
        st.subheader("⚙️ 素材与多行文字设置")
        
        selected_label = st.selectbox("选择背景素材图片：", list(image_options.keys()))
        possible_paths = image_options[selected_label]
        
        actual_img_path = None
        for p in possible_paths:
            if os.path.exists(p):
                actual_img_path = p
                break

        st.divider()
        st.write("✍️ **文字行与风格定制（支持新增多组独立风格）**")

        # 循环渲染每一组文字的控制面板
        items_to_remove = []
        for idx, item in enumerate(st.session_state.text_items):
            with st.expander(f"📝 第 {idx + 1} 组文字配置", expanded=True):
                item["text"] = st.text_area(
                    f"输入文字（第 {idx + 1} 组）：",
                    value=item["text"],
                    key=f"text_{idx}",
                    height=80
                )
                
                c1, c2 = st.columns(2)
                with c1:
                    item["text_color"] = st.color_picker(
                        "字体颜色", 
                        value=item["text_color"], 
                        key=f"tcolor_{idx}"
                    )
                with c2:
                    item["stroke_color"] = st.color_picker(
                        "描边颜色", 
                        value=item["stroke_color"], 
                        key=f"scolor_{idx}"
                    )

                item["font_size"] = st.slider(
                    "字体大小", 
                    min_value=50, 
                    max_value=400, 
                    value=item["font_size"], 
                    step=10,
                    key=f"fsize_{idx}"
                )
                item["stroke_width"] = st.slider(
                    "描边粗细", 
                    min_value=0, 
                    max_value=30, 
                    value=item["stroke_width"], 
                    step=1,
                    key=f"swidth_{idx}"
                )

                if len(st.session_state.text_items) > 1:
                    if st.button(f"🗑️ 删除第 {idx + 1} 组文字", key=f"del_{idx}"):
                        items_to_remove.append(idx)

        # 处理删除逻辑
        if items_to_remove:
            for idx in sorted(items_to_remove, reverse=True):
                st.session_state.text_items.pop(idx)
            st.rerun()

        # 按钮：新增一组文字
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("➕ 新增一组新文字", use_container_width=True):
                st.session_state.text_items.append({
                    "text": "祝您健康快乐",
                    "font_size": 200,
                    "text_color": "#0000FF",   # 新增时默认蓝色
                    "stroke_color": "#FFFF00", # 靓黄描边
                    "stroke_width": 16
                })
                st.rerun()

        with col_btn2:
            if st.button("🔄 重置文字设置", use_container_width=True):
                st.session_state.text_items = [
                    {
                        "text": "之前的听力\n出报告啦",
                        "font_size": 270,
                        "text_color": "#FF0000",
                        "stroke_color": "#FFFF00",
                        "stroke_width": 16
                    }
                ]
                st.rerun()

    with col_preview:
        st.subheader("🖼️ 表情包效果实时预览")
        
        if actual_img_path:
            try:
                base_img = Image.open(actual_img_path)
                res_img = add_multi_text_to_image(base_img, st.session_state.text_items)
                
                st.image(res_img, caption="生成的表情包样式", use_container_width=True)
                
                buf = io.BytesIO()
                res_img.save(buf, format="JPEG", quality=95)
                byte_im = buf.getvalue()

                st.download_button(
                    label="📥 点击一键保存/下载高清表情包",
                    data=byte_im,
                    file_name="喜庆大字表情包.jpg",
                    mime="image/jpeg",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"处理图片时出错：{e}")
        else:
            st.warning("⚠️ 未找到对应的图片文件！请确保已经把 `flower01.jpg` ~ `flower04.jpg` 上传到了 GitHub 的 `images/` 文件夹中。")
