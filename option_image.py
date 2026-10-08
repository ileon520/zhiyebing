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

def add_multi_text_to_image(img, text_items, global_line_gap=20):
    """在图片上绘制多组独立风格的文字，并统一绝对均匀的行间距与垂直居中"""
    img = img.convert("RGB")
    draw = ImageDraw.Draw(img)
    img_w, img_h = img.size

    # 1. 提取并平铺所有行，统一计算行高与宽度
    all_lines = []
    for item in text_items:
        text = item["text"]
        font_size = item["font_size"]
        lines = [line.strip() for line in text.strip().split("\n") if line.strip()]
        if not lines:
            continue

        font = get_font(font_size)
        
        # 使用字体标准的 ascent + descent 作为统一高度，消除字符笔画差异导致的排版误差
        try:
            ascent, descent = font.getmetrics()
            font_h = ascent + descent
        except Exception:
            font_h = int(font_size * 0.85)

        for line in lines:
            try:
                bbox = font.getbbox(line)
                w = bbox[2] - bbox[0]
            except Exception:
                w = font_size * len(line)

            all_lines.append({
                "line": line,
                "w": w,
                "h": font_h,
                "font": font,
                "item": item
            })

    if not all_lines:
        return img

    # 2. 精确计算所有行占用的总高度（包含统一的 global_line_gap）
    total_content_height = sum(line_data["h"] for line_data in all_lines) + global_line_gap * (len(all_lines) - 1)

    # 3. 整体绝对垂直居中起始点
    current_y = (img_h - total_content_height) // 2

    # 4. 逐行绘制
    for idx, line_data in enumerate(all_lines):
        line = line_data["line"]
        w = line_data["w"]
        h = line_data["h"]
        font = line_data["font"]
        item = line_data["item"]

        x = (img_w - w) // 2  # 水平居中

        dark_shadow_color = get_dark_color(item["text_color"])
        shadow_offset = max(6, int(item["font_size"] * 0.05))

        # A. 底层同色暗影
        draw.text(
            (x + shadow_offset, current_y + shadow_offset),
            line,
            font=font,
            fill=dark_shadow_color,
            stroke_width=item["stroke_width"],
            stroke_fill=dark_shadow_color
        )

        # B. 主文字与描边
        draw.text(
            (x, current_y),
            line,
            font=font,
            fill=item["text_color"],
            stroke_width=item["stroke_width"],
            stroke_fill=item["stroke_color"]
        )

        # 推进到下一行起点（只有不是最后一行时才加间距）
        current_y += h
        if idx < len(all_lines) - 1:
            current_y += global_line_gap

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
                "text_color": "#FF0000",   # 默认鲜红色
                "stroke_color": "#FFFF00", # 默认靓黄色描边
                "stroke_width": 16
            }
        ]

    col_control, col_preview = st.columns([1, 1])

    with col_control:
        st.subheader("⚙️ 素材与排版参数")
        
        selected_label = st.selectbox("选择背景素材图片：", list(image_options.keys()))
        possible_paths = image_options[selected_label]
        
        actual_img_path = None
        for p in possible_paths:
            if os.path.exists(p):
                actual_img_path = p
                break

        # 🌟 整体行间距控制滑块
        global_line_gap = st.slider(
            "📏 整体行间距（往左拉紧凑，往右拉稀疏）", 
            min_value=-50, 
            max_value=150, 
            value=20, 
            step=5
        )

        st.divider()
        st.write("✍️ **文字内容与风格定制（支持新增多组独立风格）**")

        # 动态渲染每一组文字控制项
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
                        "字体主颜色", 
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

        # 按钮配置
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("➕ 新增一组新文字", use_container_width=True):
                st.session_state.text_items.append({
                    "text": "祝您健康快乐",
                    "font_size": 200,
                    "text_color": "#0000FF",   # 新增默认宝蓝色
                    "stroke_color": "#FFFF00", # 靓黄色描边
                    "stroke_width": 16
                })
                st.rerun()

        with col_btn2:
            if st.button("🔄 重置所有设置", use_container_width=True):
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
                res_img = add_multi_text_to_image(
                    base_img, 
                    st.session_state.text_items, 
                    global_line_gap=global_line_gap
                )
                
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
