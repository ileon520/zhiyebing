import streamlit as st

def render_theme():
    """渲染侧边栏配色设置与多巴胺主题 CSS"""
    st.sidebar.title("⚙️ 设置与导航")

    with st.sidebar.expander(" 界面配色设置", expanded=False):
        theme_choice = st.selectbox(
            "选择预设多巴胺配色：",
            [" 柔粉奶油 (默认多巴胺)", " 清新薄荷", " 薰衣草紫", " 自定义配色"]
        )
        if theme_choice == " 柔粉奶油 (默认多巴胺)":
            bg_color, card_color, text_color, btn_bg, btn_text = "#FFFDF6", "#FFE5EC", "#2A085C", "#FFC2D1", "#4A0E17"
        elif theme_choice == " 清新薄荷":
            bg_color, card_color, text_color, btn_bg, btn_text = "#F4FBF7", "#E8F5E9", "#004D40", "#A5D6A7", "#1B5E20"
        elif theme_choice == " 薰衣草紫":
            bg_color, card_color, text_color, btn_bg, btn_text = "#FAF5FF", "#F3E5F5", "#3B0764", "#E1BEE7", "#4A148C"
        else:
            bg_color = st.color_picker("背景颜色 (浅色)", "#FFFDF6")
            card_color = st.color_picker("卡片背景 (浅色)", "#FFE5EC")
            text_color = st.color_picker("全局文字 (暗色)", "#2A085C")
            btn_bg = st.color_picker("按钮背景色", "#FFC2D1")
            btn_text = st.color_picker("按钮文字颜色", "#4A0E17")

    custom_css = f"""
    <style>
        .stApp {{ background-color: {bg_color}; color: {text_color}; }}
        h1, h2, h3, p, label, .stMarkdown, .stSelectbox {{ color: {text_color} !important; font-family: 'Microsoft YaHei', sans-serif; }}
        [data-testid="stVerticalBlockBorderWrapper"] {{ background-color: {card_color}; border-radius: 18px; border: none; box-shadow: 0 4px 15px rgba(0,0,0,0.04); }}
        div.stButton > button {{ background-color: {btn_bg} !important; color: {btn_text} !important; font-weight: bold !important; border-radius: 12px !important; border: none !important; padding: 10px 24px !important; transition: all 0.3s ease; }}
        div.stButton > button:hover {{ transform: translateY(-2px); box-shadow: 0 4px 10px rgba(0,0,0,0.12); }}
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)

def render_navigation(app_options):
    """渲染侧边栏搜索框、标签筛选库及菜单导航，返回用户选中的功能名称"""
    st.sidebar.divider()
    st.sidebar.subheader("🔎 功能筛选库")
    search_keyword = st.sidebar.text_input("🔍 搜索选项名称...")

    # 提取所有不重复的标签
    all_tags = sorted(list(set(tag for opt in app_options for tag in opt["tags"])))
    selected_tags = st.sidebar.multiselect("🏷️ 按业务标签筛选：", all_tags)

    filtered_options = []
    for opt in app_options:
        match_kw = search_keyword.lower() in opt["name"].lower() if search_keyword else True
        match_tag = any(tag in selected_tags for tag in opt["tags"]) if selected_tags else True
        if match_kw and match_tag:
            filtered_options.append(opt["name"])

    if not filtered_options:
        st.sidebar.warning("没有找到匹配的选项，请清空搜索或标签~")
        filtered_options = [app_options[0]["name"]]

    st.sidebar.divider()
    menu_choice = st.sidebar.radio("📌 请选择功能：", filtered_options, key="current_page")
    return menu_choice