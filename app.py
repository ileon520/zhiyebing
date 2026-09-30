import streamlit as st
import pandas as pd
from collections import defaultdict

# =============================================================================
# 🌟 昭昭专属防遗漏：核心配置区 🌟
# 姐姐以后要加新选项，只需要在这里按照格式加一行！系统会自动生成侧边栏、标签和搜索！
# =============================================================================
APP_OPTIONS = [
    {
        "name": " 首页控制台", 
        "tags": ["#导航", "#首页"], 
        "desc": "返回主控制台首页"
    },
    {
        "name": " 选项 1：报告书百分比转文字", 
        "tags": ["#报告书", "#数据处理", "#Excel"], 
        "desc": "上传 Excel 表格数据并生成带有缩进的描述 TXT 文本"
    },
    {
        "name": " 选项 2：听力数据计算", 
        "tags": ["#听力", "#体检计算", "#规则"], 
        "desc": "听力阈值提取、年龄修正与禁忌判定"
    },
    {
        "name": " 选项 3：快捷报告审核", 
        "tags": ["#报告书", "#审核"], 
        "desc": "体检数据快捷审核与规则校验"
    },
    # 💡 以后需要增加 100 个选项，就一直往这里复制粘贴，改掉名字和标签即可：
    # {"name": " 选项 4：月报表生成", "tags": ["#月报表", "#统计"], "desc": "自动生成月度统计报表"},
]

# -----------------------------------------------------------------------------
# 1. 页面基本配置与状态初始化
# -----------------------------------------------------------------------------
st.set_page_config(page_title="职业病专属工作台", layout="wide")

# 初始化 session_state，用于打通首页按钮与侧边栏菜单的联动
if "current_page" not in st.session_state:
    st.session_state.current_page = APP_OPTIONS[0]["name"]

def go_to_page(page_name):
    """页面跳转回调函数"""
    st.session_state.current_page = page_name

# -----------------------------------------------------------------------------
# 2. 侧边栏设置：配色方案（暗色文字 + 浅色多巴胺背景）
# -----------------------------------------------------------------------------
st.sidebar.title("⚙️ 设置与导航")

with st.sidebar.expander(" 界面配色设置", expanded=False):
    theme_choice = st.selectbox(
        "选择预设多巴胺配色：",
        [" 柔粉奶油 (默认多巴胺)", " 清新薄荷", " 薰衣草紫", " 自定义配色"]
    )
    # 配色代码复用[cite: 1]
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
    /* 使用 Streamlit 原生容器替代纯 HTML div 以解决分离问题 */
    [data-testid="stVerticalBlockBorderWrapper"] {{ background-color: {card_color}; border-radius: 18px; border: none; box-shadow: 0 4px 15px rgba(0,0,0,0.04); }}
    div.stButton > button {{ background-color: {btn_bg} !important; color: {btn_text} !important; font-weight: bold !important; border-radius: 12px !important; border: none !important; padding: 10px 24px !important; transition: all 0.3s ease; }}
    div.stButton > button:hover {{ transform: translateY(-2px); box-shadow: 0 4px 10px rgba(0,0,0,0.12); }}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. 导航控制：带搜索和标签筛选的侧边栏
# -----------------------------------------------------------------------------
st.sidebar.divider()
st.sidebar.subheader("🔎 功能筛选库")
search_keyword = st.sidebar.text_input("🔍 搜索选项名称...")

# 提取所有不重复的标签，并提供多选框
all_tags = sorted(list(set(tag for opt in APP_OPTIONS for tag in opt["tags"])))
selected_tags = st.sidebar.multiselect("🏷️ 按业务标签筛选：", all_tags)

# 根据搜索词和标签过滤选项
filtered_options = []
for opt in APP_OPTIONS:
    match_kw = search_keyword.lower() in opt["name"].lower() if search_keyword else True
    match_tag = any(tag in selected_tags for tag in opt["tags"]) if selected_tags else True
    if match_kw and match_tag:
        filtered_options.append(opt["name"])

if not filtered_options:
    st.sidebar.warning("没有找到匹配的选项，请清空搜索或标签~")
    filtered_options = [APP_OPTIONS[0]["name"]]

st.sidebar.divider()
# 侧边栏菜单（绑定 session_state 的 current_page）
menu_choice = st.sidebar.radio("📌 请选择功能：", filtered_options, key="current_page")

# -----------------------------------------------------------------------------
# 4. 页面内容及各选项具体逻辑
# -----------------------------------------------------------------------------
if menu_choice == " 首页控制台":
    st.title("✨ 职业病专属工作台")
    st.write("点击下方对应按钮，即可一键进入工作区域：")
    st.write("")
    
    # 获取除首页外的所有选项，动态生成卡片和按钮
    work_options = [opt for opt in APP_OPTIONS if opt["name"] != " 首页控制台"]
    cols = st.columns(3)
    
    for i, opt in enumerate(work_options):
        with cols[i % 3]:
            # 使用 Streamlit 原生的 Container（自带边框和背景，不会与按钮分离）
            with st.container(border=True):
                st.subheader(opt["name"].split("：")[0])
                st.write(opt["desc"])
                tags_str = " ".join(opt["tags"])
                st.caption(f"标签：{tags_str}")
                # 绑定跳转回调函数
                st.button("🚀 开启功能", key=f"btn_{i}", on_click=go_to_page, args=(opt["name"],), use_container_width=True)

# --- 选项 1 界面 ---
elif menu_choice == " 选项 1：报告书百分比转文字":
    st.title("📊 选项 1：Excel 异常检出率分析与 TXT 导出")
    st.write("拖入任意 Excel 表格（包含“项目”、“检查人数”、“异常人数”列即可）：")
    uploaded_file = st.file_uploader("点击或拖入上传 Excel 文件", type=["xlsx", "xls"])
    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file)
            df.columns = df.columns.str.strip()
            with st.expander(" 点击展开预览 Excel 表格内容", expanded=True):
                st.dataframe(df.head(10), use_container_width=True)
            
            data_list = []
            for index, row in df.iterrows():
                proj = str(row['项目']).strip()
                total = int(row['检查人数'])
                abnormal = int(row['异常人数'])
                rate_val = (abnormal / total * 100) if total > 0 else 0.0
                data_list.append({'proj': proj, 'total': total, 'abnormal': abnormal, 'rate_val': rate_val})

            sorted_data = sorted(data_list, key=lambda x: x['rate_val'], reverse=True)
            groups = defaultdict(list)
            for item in sorted_data:
                rate_key = "0" if item['rate_val'] == 0 else f"{item['rate_val']:.2f}%"
                groups[rate_key].append(item['proj'])

            part1_segments = [f"{'、'.join(projs)}异常检出率为{rate_key}" for rate_key, projs in groups.items()]
            part1_text = "\u3000\u3000第一部分：\n\u3000\u3000" + "，".join(part1_segments) + "。"

            part2_lines = ["\u3000\u3000第二部分："]
            for item in data_list:
                if item['abnormal'] == 0:
                    part2_lines.append(f"\u3000\u3000{item['proj']}：实检{item['total']}人均未检出异常。")
                else:
                    rate_str = f"{item['rate_val']:.2f}%"
                    part2_lines.append(f"\u3000\u3000{item['proj']}：实检{item['total']}人，检出异常{item['abnormal']}例，占受检人数异常检出率{rate_str}，{item['abnormal']}例与目前所从事职业无相关联系，在《个人职业健康检查结果》中已给出相应的处理意见。")

            full_content = part1_text + "\n\n" + "\n".join(part2_lines)
            st.markdown("###  生成的描述文本预览：")
            st.text_area("生成文本内容（已自动首行缩进）", full_content, height=250)
            
            export_name = uploaded_file.name.rsplit('.', 1)[0] + "_描述.txt"
            st.download_button(" 点击下载生成的 TXT 文本文件", data=full_content.encode('utf-8'), file_name=export_name, mime="text/plain")
        except Exception as e:
            st.error(f"处理文件时出错，请检查 Excel 列名！具体错误信息: {e}")

# --- 选项 2 界面 ---
elif menu_choice == " 选项 2：听力数据计算":
    st.title("🎧 选项 2：听力阈值计算与判定")
    st.info("这里放置听力年龄修正与禁忌自动判定计算逻辑。")

# --- 选项 3 界面 ---
elif menu_choice == " 选项 3：快捷报告审核":
    st.title("📝 选项 3：快捷报告审核")
    st.info("这里放置快捷报告审核功能。")

# --- 模板：未来新增的选项 ---
# elif menu_choice == " 这里替换为新选项的名字":
#     st.title("新选项标题")
#     st.write("新选项功能逻辑")