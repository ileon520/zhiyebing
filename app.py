import streamlit as st
import pandas as pd
import io
from collections import defaultdict
from openai import OpenAI  # 👈 新增的库


# =============================================================================
# 🌟 昭昭专属：统一 API 接口与模型配置区 🌟
# =============================================================================
API_CONFIGS = {
    "智谱 AI (GLM-4-Flash - 完全免费)": {
        "api_key": "da3565b0d1a646268a9c8e4ab1560c48.W71ryJprJ5MepXSy",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "models": ["glm-4-flash"]
    },
    "硅基流动 (DeepSeek - 代金券范围)": {
        "api_key": "sk-dymnpvuauhjfqmgqmrrkobcnjtgteyaeehghouqajsjejfxi",
        "base_url": "https://api.siliconflow.cn/v1",
        "models": ["deepseek-ai/DeepSeek-R1", "deepseek-ai/DeepSeek-V3"]
    },
    # 💡 以后姐姐要加 Gemini，直接取消下面几行的注释，把 Key 填上即可：
    # "Google Gemini": {
    #     "api_key": "这里填Gemini的Key",
    #     "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
    #     "models": ["gemini-1.5-flash", "gemini-1.5-pro"]
    # }
}

def call_ai_api(provider_name, model_name, messages):
    """统一的通用 AI 调用函数，全自动适配所有厂商"""
    cfg = API_CONFIGS[provider_name]
    client = OpenAI(
        api_key=cfg["api_key"],
        base_url=cfg["base_url"]
    )
    response = client.chat.completions.create(
        model=model_name,
        messages=messages
    )
    return response.choices[0].message.content

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
        "name": " 选项 2：疾控月报表", 
        "tags": ["#月报表", "#疾控"], 
        "desc": "上传Excel表格，转化为表1-2和1-3的内容"
    },
    {
        "name": " 选项 1：报告书百分比转文字", 
        "tags": ["#报告书", "#百分比"], 
        "desc": "上传Excel表格，百分比表格转化为文字描述"
    },
    {
        "name": " 选项 3：待定", 
        "tags": ["#？", "#？"], 
        "desc": "？"
    },
    {
        "name": " 🤖 AI 智能测试助手", 
        "tags": ["#AI", "#测试", "#对话"], 
        "desc": "测试智谱、硅基流动等多 API 接口可用性与回答效果"
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
                st.subheader(opt["name"])
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
elif menu_choice == " 选项 2：疾控月报表":
    st.title("📊 选项 2：疾控月报表自动统计")
    st.write("请上传包含【用工单位名称】和【体检危害因素名称】的 Excel 文件：")
    
    uploaded_file = st.file_uploader("点击或拖入上传 Excel 文件", type=["xlsx", "xls"], key="cdc_upload")
    
    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file)
            df = df.dropna(subset=['用工单位名称', '体检危害因素名称'])
            
            # 显示读取成功提示
            unit_count = len(df['用工单位名称'].unique())
            st.success(f"✅ 文件读取成功！共检测到 {unit_count} 个单位，点击下方按钮下载统计报表。")
            
            # 核心函数：分析单人危害因素
            def analyze_person_hazards(hazard_str):
                if pd.isna(hazard_str) or not str(hazard_str).strip():
                    return {}
                raw_str = str(hazard_str).replace('，', ',').replace(' ', ',').replace('、', ',')
                factors = [f.strip() for f in raw_str.split(',') if f.strip()]
                
                categories = {k: 0 for k in [
                    "全因素", "矽尘", "煤尘", "石棉粉尘", "水泥粉尘", 
                    "电焊烟尘", "其他粉尘", "苯", "铅", "其他化学因素", 
                    "噪声", "其他物理因素", "布鲁氏菌", "其他生物因素"
                ]}
                categories["全因素"] = 1
                has_other_chem = False
                
                for factor in factors:
                    if "矽尘" in factor: categories["矽尘"] = 1
                    elif "煤尘" in factor: categories["煤尘"] = 1
                    elif "石棉" in factor and "尘" in factor: categories["石棉粉尘"] = 1
                    elif "水泥" in factor and "尘" in factor: categories["水泥粉尘"] = 1
                    elif "电焊烟尘" in factor: categories["电焊烟尘"] = 1
                    elif "尘" in factor: categories["其他粉尘"] = 1
                    elif any(p in factor for p in ["手传振动", "高温", "紫外", "高气压", "微波", "低温", "激光", "工频"]): categories["其他物理因素"] = 1
                    elif "噪声" in factor: categories["噪声"] = 1
                    elif "布鲁氏菌" in factor: categories["布鲁氏菌"] = 1
                    elif "生物" in factor: categories["其他生物因素"] = 1
                    elif any(s in factor for s in ["高处作业", "电工作业", "焊接", "空间", "驾驶", "特殊作业"]): pass
                    else:
                        if factor == "苯" or ("苯" in factor and "甲苯" not in factor and "二甲苯" not in factor): categories["苯"] = 1
                        elif "铅" in factor and "四乙基铅" not in factor: categories["铅"] = 1
                        elif not any(ex in factor for ex in ["甲苯", "二甲苯"]): has_other_chem = True
                
                if has_other_chem:
                    categories["其他化学因素"] = 1
                return categories

            # 用于存储所有行数据的列表
            output_data = []
            
            # 核心函数：向表格数据中追加单个单位的统计块
            def add_table_to_data(temp_df, title):
                # 写入单位名称（不再使用 ===）
                output_data.append({"危害因素": title, "接触职业病危害因素人数": ""})
                output_data.append({"危害因素": "危害因素", "接触职业病危害因素人数": "接触职业病危害因素人数"})
                
                totals = {k: 0 for k in [
                    "全因素", "矽尘", "煤尘", "石棉粉尘", "水泥粉尘", 
                    "电焊烟尘", "其他粉尘", "苯", "铅", "其他化学因素", 
                    "噪声", "其他物理因素", "布鲁氏菌", "其他生物因素"
                ]}
                
                for hazard_item in temp_df['体检危害因素名称']:
                    person_res = analyze_person_hazards(hazard_item)
                    for key, val in person_res.items():
                        totals[key] += val
                        
                for key, count in totals.items():
                    output_data.append({"危害因素": key, "接触职业病危害因素人数": count})
                
                # 追加一个空行隔开不同单位
                output_data.append({"危害因素": "", "接触职业病危害因素人数": ""})
            
            # 1. 统计总表
            add_table_to_data(df, "1-3 表格：全因素汇总表")
            
            # 2. 分别统计各单位
            units = df['用工单位名称'].unique()
            for unit in units:
                unit_df = df[df['用工单位名称'] == unit]
                add_table_to_data(unit_df, f"1-2 表格：{unit}")
            
            # 3. 将数据转为 DataFrame 并生成 Excel 文件流
            result_df = pd.DataFrame(output_data)
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                # header=False 防止输出 DataFrame 原本的英文列名
                result_df.to_excel(writer, index=False, header=False)
            
            # 网页下载按钮
            st.download_button(
                label="📥 点击下载统计结果 Excel",
                data=excel_buffer.getvalue(),
                file_name="月报表统计结果.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
            
        except Exception as e:
            st.error(f"处理文件时出错，请检查是否包含所需列！错误信息: {e}")
    # 增加的示例展示区
    st.divider()
    st.subheader("💡 填写示例与说明")
    st.write("上传的表格格式示例：")
    
    # 表格示例
    example_df = pd.DataFrame({
        "用工单位名称": [
            "中国铁路郑州局集团有限公司月山工务段",
            "华润电力焦作有限公司",
            "中国铁路郑州局集团有限公司郑州东高铁基础设施段",
            "河南平原光电有限公司"
        ],
        "体检危害因素名称": [
            "噪声",
            "煤尘（游离 SiO2 含量＜10%）,噪声",
            "矽尘,噪声",
            "其他粉尘,乙醚,丙酮"
        ]
    })
    st.dataframe(example_df, use_container_width=True)
    
    st.write("得到的成品示例：")

    # 1. 表格：全因素汇总表
    st.write("1-3 表格：全因素汇总表")
    summary_df = pd.DataFrame({
        "危害因素": [
            "全因素", "矽尘", "煤尘", "石棉粉尘", "水泥粉尘", 
            "电焊烟尘", "其他粉尘", "苯", "铅", "其他化学因素", 
            "噪声", "其他物理因素", "布鲁氏菌", "其他生物因素"
        ],
        "接触职业病危害因素人数": [
            "1515", "130", "223", "0", "0", 
            "36", "389", "129", "12", "507", 
            "970", "250", "0", "0"
        ]
    })
    st.dataframe(summary_df, use_container_width=True)

    # 2. 表格：分单位明细表
    st.write("1-2 表格：中国铁路郑州局集团有限公司新乡机务段")
    detail_df = pd.DataFrame({
        "危害因素": [
            "全因素", "矽尘", "煤尘", "石棉粉尘", "水泥粉尘", 
            "电焊烟尘", "其他粉尘", "苯", "铅", "其他化学因素", 
            "噪声", "其他物理因素", "布鲁氏菌", "其他生物因素"
        ],
        "接触职业病危害因素人数": [
            "158", "5", "0", "0", "0", 
            "3", "73", "2", "0", "5", 
            "73", "2", "0", "0"
        ]
    })
    st.dataframe(detail_df, use_container_width=True)
    

    # 图片示例（将示例图片命名为 example.jpg 放入同文件夹，去掉下一行的 # 即可显示）
    # st.image("example.jpg", caption="Excel截图示例", use_container_width=True)

# --- 选项 3 界面 ---
elif menu_choice == " 选项 3：快捷报告审核":
    st.title("📝 选项 3：快捷报告审核")
    st.info("这里放置快捷报告审核功能。")

# --- 🤖 AI 智能测试助手 界面 ---
elif menu_choice == " 🤖 AI 智能测试助手":
    # 顶部标题与“新开聊天”按钮（并排放置）
    col_title, col_reset = st.columns([3, 1])
    with col_title:
        st.title("🤖 AI 智能测试助手")
    with col_reset:
        # 点击清空聊天历史，开启新对话
        if st.button("🧹 新开聊天", use_container_width=True):
            st.session_state.chat_messages = [
                {"role": "assistant", "content": "姐姐好！我是 AI 测试助手，当前接口正常运行，你想测试什么？"}
            ]
            st.rerun()

    st.write("姐姐可以在这里随意测试各个 API 接口与模型的可用性：")

    # 1. 下拉菜单选择 API 厂商与模型
    col1, col2 = st.columns(2)
    with col1:
        selected_provider = st.selectbox(
            "📌 选择 API 厂商：",
            list(API_CONFIGS.keys()),
            index=0  # 默认选中第一个（智谱 AI）
        )
    with col2:
        available_models = API_CONFIGS[selected_provider]["models"]
        selected_model = st.selectbox(
            "🧠 选择具体模型：",
            available_models,
            index=0
        )

    st.caption(f"当前使用的接口：`{selected_provider}` | 模型名：`{selected_model}`")
    st.divider()

    # 2. 初始化对话历史
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = [
            {"role": "assistant", "content": "姐姐好！我是 AI 测试助手，当前接口正常运行，你想测试什么？"}
        ]

    # 显示过往聊天记录
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # 3. 聊天输入框与 API 发送
    user_input = st.chat_input("请输入你想对 AI 说的测试内容...")
    if user_input:
        # 显示用户发送的信息
        st.session_state.chat_messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.write(user_input)

        # 调用后台 API 接口获取回答
        with st.chat_message("assistant"):
            with st.spinner("AI 思考中，请稍候..."):
                try:
                    # 格式化历史消息发给 API
                    api_msgs = [{"role": m["role"], "content": m["content"]} for m in st.session_state.chat_messages]
                    reply = call_ai_api(selected_provider, selected_model, api_msgs)
                    
                    st.write(reply)
                    st.session_state.chat_messages.append({"role": "assistant", "content": reply})
                except Exception as e:
                    st.error(f"❌ 调用失败，请检查网络或 API 额度！具体错误：{e}")
