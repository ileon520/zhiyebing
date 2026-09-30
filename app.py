import streamlit as st
import pandas as pd
from collections import defaultdict

# -----------------------------------------------------------------------------
# 1. 页面基本配置
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="职业病专属工作台",
    page_icon="",
    layout="wide"
)

# -----------------------------------------------------------------------------
# 2. 侧边栏设置：配色方案（暗色文字 + 浅色多巴胺背景）
# -----------------------------------------------------------------------------
st.sidebar.title("⚙️ 设置与导航")

with st.sidebar.expander(" 界面配色设置", expanded=False):
    theme_choice = st.selectbox(
        "选择预设多巴胺配色：",
        [" 柔粉奶油 (默认多巴胺)", " 清新薄荷", " 薰衣草紫", " 自定义配色"]
    )
    
    if theme_choice == " 柔粉奶油 (默认多巴胺)":
        bg_color = "#FFFDF6"
        card_color = "#FFE5EC"
        text_color = "#2A085C"
        btn_bg = "#FFC2D1"
        btn_text = "#4A0E17"
    elif theme_choice == " 清新薄荷":
        bg_color = "#F4FBF7"
        card_color = "#E8F5E9"
        text_color = "#004D40"
        btn_bg = "#A5D6A7"
        btn_text = "#1B5E20"
    elif theme_choice == " 薰衣草紫":
        bg_color = "#FAF5FF"
        card_color = "#F3E5F5"
        text_color = "#3B0764"
        btn_bg = "#E1BEE7"
        btn_text = "#4A148C"
    else:
        bg_color = st.color_picker("背景颜色 (浅色)", "#FFFDF6")
        card_color = st.color_picker("卡片背景 (浅色)", "#FFE5EC")
        text_color = st.color_picker("全局文字 (暗色)", "#2A085C")
        btn_bg = st.color_picker("按钮背景色", "#FFC2D1")
        btn_text = st.color_picker("按钮文字颜色", "#4A0E17")

# 注入动态 CSS 样式
custom_css = f"""
<style>
    .stApp {{
        background-color: {bg_color};
        color: {text_color};
    }}
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown, .stSelectbox {{
        color: {text_color} !important;
        font-family: 'Microsoft YaHei', sans-serif;
    }}
    .dopamine-card {{
        background-color: {card_color};
        padding: 24px;
        border-radius: 18px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.04);
        margin-bottom: 20px;
        border: 1px solid rgba(0,0,0,0.05);
    }}
    div.stButton > button {{
        background-color: {btn_bg} !important;
        color: {btn_text} !important;
        font-weight: bold !important;
        border-radius: 12px !important;
        border: none !important;
        padding: 10px 24px !important;
        font-size: 16px !important;
        transition: all 0.3s ease;
    }}
    div.stButton > button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 4px 10px rgba(0,0,0,0.12);
    }}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. 导航控制 (侧边栏菜单)
# -----------------------------------------------------------------------------
menu_choice = st.sidebar.radio(
    " 请选择功能：",
    [" 首页控制台", " 选项 1：报告书百分比转文字", " 选项 2：听力数据计算", " 选项 3：快捷报告审核"]
)

# -----------------------------------------------------------------------------
# 4. 页面内容
# -----------------------------------------------------------------------------
if menu_choice == " 首页控制台":
    st.title("✨ 职业病专属工作台")
    st.write("点击下方任意功能按钮或侧边栏，即可进入对应工作区域：")
    st.write("")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown('<div class="dopamine-card">', unsafe_allow_html=True)
        st.subheader(" 选项 1")
        st.write("上传 Excel 表格数据并生成带有缩进的描述 TXT 文本")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col2:
        st.markdown('<div class="dopamine-card">', unsafe_allow_html=True)
        st.subheader(" 选项 2")
        st.write("听力阈值提取、年龄修正与禁忌判定")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col3:
        st.markdown('<div class="dopamine-card">', unsafe_allow_html=True)
        st.subheader(" 选项 3")
        st.write("体检数据快捷审核与规则校验")
        st.markdown('</div>', unsafe_allow_html=True)

# --- 选项 1 界面（集成姐姐原本的分析逻辑）---
elif menu_choice == " 选项 1：报告书百分比转文字":
    st.title(" 选项 1：Excel 异常检出率分析与 TXT 导出")
    st.write("拖入任意 Excel 表格（包含“项目”、“检查人数”、“异常人数”列即可）：")
    
    # 1. 动态上传文件（不限制文件名）
    uploaded_file = st.file_uploader("点击或拖入上传 Excel 文件", type=["xlsx", "xls"])
    
    if uploaded_file is not None:
        try:
            # 读取上传的文件
            df = pd.read_excel(uploaded_file)
            st.success(f"✅ 文件【{uploaded_file.name}】读取成功！")
            
            # 预处理列名
            df.columns = df.columns.str.strip()
            
            # 在网页预览前 5 行表格
            with st.expander(" 点击展开预览 Excel 表格内容", expanded=True):
                st.dataframe(df.head(10), use_container_width=True)
            
            # 2. 核心分析计算逻辑
            data_list = []
            for index, row in df.iterrows():
                proj = str(row['项目']).strip()
                total = int(row['检查人数'])
                abnormal = int(row['异常人数'])
                rate_val = (abnormal / total * 100) if total > 0 else 0.0
                
                data_list.append({
                    'proj': proj,
                    'total': total,
                    'abnormal': abnormal,
                    'rate_val': rate_val
                })

            # 第一部分：排序与分组
            sorted_data = sorted(data_list, key=lambda x: x['rate_val'], reverse=True)
            groups = defaultdict(list)
            for item in sorted_data:
                if item['rate_val'] == 0:
                    rate_key = "0"
                else:
                    rate_key = f"{item['rate_val']:.2f}%"
                groups[rate_key].append(item['proj'])

            part1_segments = []
            for rate_key, projs in groups.items():
                proj_names = "、".join(projs)
                part1_segments.append(f"{proj_names}异常检出率为{rate_key}")

            # 首行缩进 2 个字 (\u3000\u3000 为中文全角双空格)
            part1_text = "\u3000\u3000第一部分：\n\u3000\u3000" + "，".join(part1_segments) + "。"

            # 第二部分：详细描述
            part2_lines = ["\u3000\u3000第二部分："]
            for item in data_list:
                proj = item['proj']
                total = item['total']
                abnormal = item['abnormal']
                rate_val = item['rate_val']

                if abnormal == 0:
                    line = f"\u3000\u3000{proj}：实检{total}人均未检出异常。"
                else:
                    rate_str = f"{rate_val:.2f}%"
                    line = f"\u3000\u3000{proj}：实检{total}人，检出异常{abnormal}例，占受检人数异常检出率{rate_str}，{abnormal}例与目前所从事职业无相关联系，在《个人职业健康检查结果》中已给出相应的处理意见。"
                
                part2_lines.append(line)

            part2_text = "\n".join(part2_lines)
            full_content = part1_text + "\n\n" + part2_text

            # 3. 网页展示生成结果与下载按钮
            st.markdown("###  生成的描述文本预览：")
            st.text_area("生成文本内容（已自动首行缩进）", full_content, height=250)
            
            # 生成默认的导出文件名（基于原上传文件名）
            export_name = uploaded_file.name.rsplit('.', 1)[0] + "_描述.txt"
            
            # 导出 TXT 按钮
            st.download_button(
                label=" 点击下载生成的 TXT 文本文件",
                data=full_content.encode('utf-8'),
                file_name=export_name,
                mime="text/plain"
            )

        except Exception as e:
            st.error(f"处理文件时出错，请检查 Excel 列名是否包含“项目”、“检查人数”、“异常人数”！具体错误信息: {e}")

# --- 选项 2 界面 ---
elif menu_choice == " 选项 2：听力数据计算":
    st.title(" 选项 2：听力阈值计算与判定")
    st.info("这里后续会放置听力年龄修正与禁忌自动判定计算逻辑。")

# --- 选项 3 界面 ---
elif menu_choice == " 选项 3：快捷报告审核":
    st.title(" 选项 3：快捷报告审核")
    st.info("这里后续会放置快捷报告审核功能。")