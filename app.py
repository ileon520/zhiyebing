import streamlit as st
import pandas as pd
import io
import os
import socket
from collections import defaultdict
from openai import OpenAI  # 👈 新增的库


def smart_read_uploaded_file(uploaded_file):
    file_name = uploaded_file.name.lower()
    
    # 1. 尝试 openpyxl 读取 (加 dtype=str)
    try:
        uploaded_file.seek(0)
        return pd.read_excel(uploaded_file, dtype=str)
    except Exception:
        pass
        
    # 2. 针对旧版 .xls 尝试 xlrd 引擎 (加 dtype=str)
    try:
        uploaded_file.seek(0)
        return pd.read_excel(uploaded_file, engine='xlrd', dtype=str)
    except Exception:
        pass
        
    # 3. 针对 HTML 表格伪装的 .xls
    try:
        uploaded_file.seek(0)
        dfs = pd.read_html(uploaded_file)
        if dfs:
            return dfs[0].astype(str)
    except Exception:
        pass
        
    # 4. 兜底 CSV 格式 (加 dtype=str)
    for enc in ['utf-8', 'gbk', 'gb18030', 'utf-16', 'utf-16-le', 'ansi']:
        try:
            uploaded_file.seek(0)
            return pd.read_csv(uploaded_file, encoding=enc, dtype=str)
        except Exception:
            continue
            
    raise ValueError("无法识别的表格格式，请确保文件没有损坏！")

# 尝试引入 pypinyin 实现精准拼音排序，如果没有安装则自动平滑兼容
try:
    import pypinyin
    def get_pinyin_sort_key(text):
        # 将汉字转换为无音调拼音字符串，如 "张三" -> "zhangsan"
        return ''.join(pypinyin.lazy_pinyin(str(text)))
except ImportError:
    import locale
    def get_pinyin_sort_key(text):
        try:
            locale.setlocale(locale.LC_COLLATE, 'zh_CN.UTF-8')
            return locale.strxfrm(str(text))
        except Exception:
            return str(text)

# 👈 2. 实时网络检测函数（移除了 @st.cache_data 缓存，实现断网实时切换）
def check_network_environment():
  """实时检测是否能连通外网（0.5秒毫秒级检测）"""
  try:
    # 尝试连接外网智谱 API 端口 (443)，超时设为 0.5 秒
    socket.create_connection(("open.bigmodel.cn", 443), timeout=0.5)
    return True  # 连通外网
  except Exception:
    return False  # 纯内网/断网环境


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
    # 👇 这里是新增的本地 Ollama 专属通道
    "本地小模型 (Ollama - Qwen2.5)": {
        "api_key": "ollama",  # 本地调用不需要真实的秘钥，随便填即可
        "base_url": "http://127.0.0.1:11434/v1",  # 这是 Ollama 默认的本地服务通信地址
        "models": ["qwen2.5:1.5b"]  # 填入你下载的具体模型名称
    }
    # 💡 以后姐姐要加 Gemini，直接取消下面几行的注释，把 Key 填上即可：
    # "Google Gemini": {
    #     "api_key": "这里填Gemini的Key",
    #     "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
    #     "models": ["gemini-1.5-flash", "gemini-1.5-pro"]
    # }
}

def call_ai_api(provider_name, model_name, messages, use_gbz=False):
  """统一的通用 AI 调用函数，带防幻觉强约束"""
  cfg = API_CONFIGS[provider_name]
  client = OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"])

  final_messages = []

  # 🌟 1. 强约束提示词：给本地 AI 戴上紧箍咒，严禁自由发挥和跨章节串联
  if use_gbz and ("硅基" not in provider_name):
    if os.path.exists("GBZ188_2025.txt"):
      try:
        with open("GBZ188_2025.txt", "r", encoding="utf-8") as f:
          gbz_content = f.read()

        sys_msg = {
            "role": "system",
            "content": (
                "【极其严格的抽取指令】：你是一个只负责精准抽取资料内容的助手。\n"
                "1. 你的回答必须完全来自于下面给出的《GBZ 188-2025》参考资料，绝对禁止凭借自身知识捏造、补充或联想任何资料中未提及的疾病和检查项目！\n"
                "2. 只能精准提取用户询问的特定危害因素（如：铅）对应的条款！绝对禁止把其他危害因素混入当前回答中！\n"
                "3. 保持回答100%忠实于原文，找不到的内容直接说明未提及。\n"
                "4. 【重点】：如果参考资料中写有‘同 X.X.X’或‘参见X.X.X’（例如‘同 5.1.2.2’），绝对禁止直接回复‘同 X.X.X’！你必须根据资料全文，找到该章节的具体项目并展开详细回答！\n\n"
                f"【参考资料全文】：\n{gbz_content}"
            ),
        }
        final_messages.append(sys_msg)
      except Exception:
        pass

  final_messages.extend(messages)

  kwargs = {"model": model_name, "messages": final_messages}

  # 🌟 2. 针对本地 Ollama：扩容上下文的同时，将 temperature 锁定为 0.1，彻底封杀发散与胡思乱想
  if "本地" in provider_name or "Ollama" in provider_name:
    kwargs["extra_body"] = {
        "options": {
            "num_ctx": 16384,
            "temperature": 0.1,  # 强制严谨做完形填空，禁止创作
        }
    }

  response = client.chat.completions.create(**kwargs)
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
        "name": " 选项 3：报告书表格生成", 
        "tags": ["#报告书", "#表格", "#AI建议"], 
        "desc": "上传包含体检信息的Excel，自动拆分并使用AI生成4种报告书最终表格"
    },
    {
        "name": " 🤖 AI 智能测试助手", 
        "tags": ["#AI", "#测试", "#对话"], 
        "desc": "内网用不了AI，只能外网用。测试智谱、硅基流动等多 API 接口可用性与回答效果"
    },
    # 👇 下面是姐姐新加的选项 4 名片：
    {
        "name": " 🌸 选项 4：中老年表情包制作", 
        "tags": ["#图片", "#表情包", "#花样加字"], 
        "desc": "选择预设荷花/鲜花背景图，一键制作喜庆中老年发光大字表情包"
    }
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
            df = smart_read_uploaded_file(uploaded_file)
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
    # 增加的示例展示区
    st.divider()
    st.subheader("💡 填写示例与说明")
    st.write("上传表格的示例：")
    
    # 上传表格示例
    example_df = pd.DataFrame({
        "项目": [
            "尿常规", "肝胆脾胰彩超", "口腔科", "肺功能检测", "身高体重血压", 
            "外科", "纯音听阈测试", "心电图", "血常规", "肝功1", 
            "总IgE测定", "内科", "高千伏胸部正位片", "耳鼻喉科", "眼科", 
            "职业病问诊", "神经内科"
        ],
        "检查人数": [
            "44", "44", "44", "44", "44", 
            "44", "44", "44", "44", "44", 
            "44", "44", "44", "44", "44", 
            "44", "44"
        ],
        "异常人数": [
            "43", "38", "31", "29", "29", 
            "28", "24", "18", "16", "14", 
            "13", "10", "9", "5", "3", 
            "0", "0"
        ],
        "异常检出率": [
            "97.73%", "86.36%", "70.45%", "65.91%", "65.91%", 
            "63.64%", "54.55%", "40.91%", "36.36%", "31.82%", 
            "29.55%", "22.73%", "20.45%", "11.36%", "6.82%", 
            "0.00%", "0.00%"
        ]
    })
    st.dataframe(example_df, use_container_width=True)
    
    st.write("得到的成品示例：")

    # 成品展示：使用多行文本框 text_area 显示 txt 效果
    result_text = """  第一部分：
  尿常规异常检出率为97.73%，肝胆脾胰彩超异常检出率为86.36%，口腔科异常检出率为70.45%，肺功能检测、身高体重血压异常检出率为65.91%，外科异常检出率为63.64%，纯音听阈测试异常检出率为54.55%，心电图异常检出率为40.91%，血常规异常检出率为36.36%，肝功1异常检出率为31.82%，总IgE测定异常检出率为29.55%，内科异常检出率为22.73%，高千伏胸部正位片异常检出率为20.45%，耳鼻喉科异常检出率为11.36%，眼科异常检出率为6.82%，职业病问诊、神经内科异常检出率为0。

  第二部分：
  尿常规：实检44人，检出异常43例，占受检人数异常检出率97.73%，43例与目前所从事职业无相关联系，在《个人职业健康检查结果》中已给出相应的处理意见。
  肝胆脾胰彩超：实检44人，检出异常38例，占受检人数异常检出率86.36%，38例与目前所从事职业无相关联系，在《个人职业健康检查结果》中已给出相应的处理意见。
  口腔科：实检44人，检出异常31例，占受检人数异常检出率70.45%，31例与目前所从事职业无相关联系，在《个人职业健康检查结果》中已给出相应的处理意见。
  肺功能检测：实检44人，检出异常29例，占受检人数异常检出率65.91%，29例与目前所从事职业无相关联系，在《个人职业健康检查结果》中已给出相应的处理意见。
  身高体重血压：实检44人，检出异常29例，占受检人数异常检出率65.91%，29例与目前所从事职业无相关联系，在《个人职业健康检查结果》中已给出相应的处理意见。
  外科：实检44人，检出异常28例，占受检人数异常检出率63.64%，28例与目前所从事职业无相关联系，在《个人职业健康检查结果》中已给出相应的处理意见。
  纯音听阈测试：实检44人，检出异常24例，占受检人数异常检出率54.55%，24例与目前所从事职业无相关联系，在《个人职业健康检查结果》中已给出相应的处理意见。
  心电图：实检44人，检出异常18例，占受检人数异常检出率40.91%，18例与目前所从事职业无相关联系，在《个人职业健康检查结果》中已给出相应的处理意见。
  血常规：实检44人，检出异常16例，占受检人数异常检出率36.36%，16例与目前所从事职业无相关联系，在《个人职业健康检查结果》中已给出相应的处理意见。
  肝功1：实检44人，检出异常14例，占受检人数异常检出率31.82%，14例与目前所从事职业无相关联系，在《个人职业健康检查结果》中已给出相应的处理意见。
  总IgE测定：实检44人，检出异常13例，占受检人数异常检出率29.55%，13例与目前所从事职业无相关联系，在《个人职业健康检查结果》中已给出相应的处理意见。
  内科：实检44人，检出异常10例，占受检人数异常检出率22.73%，10例与目前所从事职业无相关联系，在《个人职业健康检查结果》中已给出相应的处理意见。
  高千伏胸部正位片：实检44人，检出异常9例，占受检人数异常检出率20.45%，9例与目前所从事职业无相关联系，在《个人职业健康检查结果》中已给出相应的处理意见。
  耳鼻喉科：实检44人，检出异常5例，占受检人数异常检出率11.36%，5例与目前所从事职业无相关联系，在《个人职业健康检查结果》中已给出相应的处理意见。
  眼科：实检44人，检出异常3例，占受检人数异常检出率6.82%，3例与目前所从事职业无相关联系，在《个人职业健康检查结果》中已给出相应的处理意见。
  职业病问诊：实检44人均未检出异常。
  神经内科：实检44人均未检出异常。"""

    st.text_area("生成的文本成品预览（支持直接复制）", result_text, height=350)

# --- 选项 2 界面 ---
elif menu_choice == " 选项 2：疾控月报表":
    st.title("📊 选项 2：疾控月报表自动统计")
    st.write("可以直接把省平台下载的Excel表格上传，也可以只保留【用工单位名称】和【体检危害因素名称】这2列再上传：")
    
    uploaded_file = st.file_uploader("点击或拖入上传 Excel 文件", type=["xlsx", "xls"], key="cdc_upload")
    
    if uploaded_file is not None:
        try:
            df = smart_read_uploaded_file(uploaded_file)
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
elif menu_choice == " 选项 3：报告书表格生成":
    st.title("📝 选项 3：报告书生成与 AI 医学建议")
    st.write("请上传包含体检信息的 Excel 表格：")

    # 1. 初始化 Session State 存储区（记忆硬盘）
    if "opt3_fast_buffer" not in st.session_state:
        st.session_state.opt3_fast_buffer = None
    if "opt3_fast_sheets" not in st.session_state:
        st.session_state.opt3_fast_sheets = None
    if "opt3_full_buffer" not in st.session_state:
        st.session_state.opt3_full_buffer = None
    if "opt3_output_sheets" not in st.session_state:
        st.session_state.opt3_output_sheets = None
    if "opt3_t2_done" not in st.session_state:
        st.session_state.opt3_t2_done = False
    if "opt3_df" not in st.session_state:
        st.session_state.opt3_df = None

    # 2. 动态生成勾选框
    st.subheader("⚙️ 第一步：选择需要生成的表格")
    check_all = st.checkbox("✅ 全选（勾选后自动选中下方所有表格）", value=True)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1: gen_t1 = st.checkbox("📊 表格 1：结果汇总表", value=check_all)
    with col2: gen_t2 = st.checkbox("🤖 表格 2：阳性结果(需AI)", value=check_all)
    with col3: gen_t3 = st.checkbox("📈 表格 3：个体结论统计", value=check_all)
    with col4: gen_t4 = st.checkbox("📋 表格 4：检查对象", value=check_all)

    # 3. AI 接口选择器
    if gen_t2:
        st.info("💡 提示：生成表格 2 需要使用 AI 进行医学建议改写。请选择下方接口：")
        provider_list = list(API_CONFIGS.keys())
        if check_network_environment():
            default_idx = next((i for i, name in enumerate(provider_list) if "智谱" in name), 0)
        else:
            default_idx = next((i for i, name in enumerate(provider_list) if "本地" in name or "Ollama" in name), 0)
            
        col_ai1, col_ai2 = st.columns(2)
        with col_ai1:
            opt3_provider = st.selectbox("📌 选择 API 厂商：", provider_list, index=default_idx, key="opt3_provider")
        with col_ai2:
            opt3_model = st.selectbox("🧠 选择具体模型：", API_CONFIGS[opt3_provider]["models"], index=0, key="opt3_model")

    st.subheader("📂 第二步：上传表格并生成")
    uploaded_file = st.file_uploader("点击或拖入上传 Excel 文件", type=["xlsx", "xls"], key="opt3_upload")

    if uploaded_file is not None:
        # 点击生成按钮：优先处理毫秒级的表1、3、4
        if st.button("🚀 开始处理并生成选中的表格", use_container_width=True):
            try:
                df = smart_read_uploaded_file(uploaded_file)
                # 🌟 修复点1：清理列名首尾的所有隐形空格
                df.columns = [str(c).strip() for c in df.columns]

                # 身份证号修复
                id_col_name = next((col for col in ['IdCardNo', '身份证号', '身份证', 'idcard'] if col in df.columns), None)
                def clean_id_card(val):
                    if pd.isna(val) or val is None: return ""
                    s = str(val).strip()
                    if not s or s.lower() == 'nan': return ""
                    if 'e+' in s.lower():
                        try: s = f"{float(s):.0f}"
                        except: pass
                    if s.endswith('.0'): s = s[:-2]
                    return s

                if id_col_name:
                    df[id_col_name] = df[id_col_name].apply(clean_id_card)
                
                # 拼音升序排序 + 重置索引
                if '姓名' in df.columns:
                    df['pinyin_key'] = df['姓名'].apply(get_pinyin_sort_key)
                    sort_cols = ['pinyin_key']
                    if 'IdCardNo' in df.columns: sort_cols.append('IdCardNo')
                    df = df.sort_values(by=sort_cols, ascending=[True] * len(sort_cols))
                    df = df.drop(columns=['pinyin_key'])
                
                df = df.reset_index(drop=True)
                st.session_state.opt3_df = df  # 保持内存引用

                fast_sheets = {}
                import re

                def get_exam_type(text):
                    text = str(text)
                    if "上岗" in text: return "上岗"
                    elif "离岗" in text: return "离岗"
                    else: return "在岗"

                df['检查类别'] = df.get('WorkAgeOccuTouched', '').apply(get_exam_type)

                # 🌟 修复点2：智能精准匹配【工龄】列（解决工龄空白问题）
                workage_col_name = next((c for c in df.columns if any(k in str(c).lower() for k in ['工龄', 'workage', 'workno', '接害年限', '接害工龄'])), None)
                if workage_col_name:
                    t1_workage = df[workage_col_name]
                else:
                    t1_workage = df.get('workno', df.get('工龄', ''))

                # 1. 生成表格 1
                if gen_t1:
                    fast_sheets['表格1_结果汇总表'] = pd.DataFrame({
                        '编号': range(1, len(df) + 1),
                        '姓名': df.get('姓名', ''),
                        '性别': df.get('性别', ''),
                        '身份证号': df.get('IdCardNo', ''),
                        '检查': df['检查类别'],
                        '车间': df.get('团体部门', ''),
                        '工种': df.get('worktype', ''),
                        '职业病危害因素': df.get('岗位危害因素', ''),
                        '工龄': t1_workage,
                        '个体体检结论': '其他疾病或异常', 
                        '职业健康处理意见': df.get('Occuadvice', '')
                    })

                # 2. 生成表格 3
                if gen_t3:
                    t3_records = []
                    for _, row in df.iterrows():
                        exam_type = row['检查类别']
                        hazards_str = str(row.get('岗位危害因素', ''))
                        hazards = [h.strip() for h in re.split(r'[、,\s]+', hazards_str) if h.strip()]
                        for h in hazards:
                            t3_records.append({'体检类别': exam_type, '职业病危害因素名称': h})
                    t3_df = pd.DataFrame(t3_records)
                    fast_sheets['表格3_个体结论统计表'] = t3_df.groupby(['体检类别', '职业病危害因素名称']).size().reset_index(name='应检人数')

                # 3. 生成表格 4
                if gen_t4:
                    t4_grouped = df.groupby(['检查类别', '团体部门', 'worktype', '岗位危害因素']).size().reset_index(name='委托人数')
                    t4_grouped.rename(columns={'检查类别': '体检类别', '团体部门': '车间', 'worktype': '工种', '岗位危害因素': '职业病危害因素名称'}, inplace=True)
                    fast_sheets['表格4_检查对象表'] = t4_grouped

                # 存入基础表格 Byte 缓存，供点击立刻下载
                if fast_sheets:
                    fast_buffer = io.BytesIO()
                    with pd.ExcelWriter(fast_buffer, engine='openpyxl') as writer:
                        for sheet_name, sheet_df in fast_sheets.items():
                            sheet_df.to_excel(writer, sheet_name=sheet_name, index=False)
                    st.session_state.opt3_fast_buffer = fast_buffer.getvalue()
                    st.session_state.opt3_fast_sheets = fast_sheets
                    st.success("⚡ 基础表格（表1、3、4）已就绪！下弹下载按钮！")
                else:
                    # 如果姐姐没勾选基础表格，必须清空缓存，并给出准确的提示
                    st.session_state.opt3_fast_buffer = None
                    st.session_state.opt3_fast_sheets = None
                    st.success("⚡ 数据读取成功！准备开始 AI 处理表格 2...")

                # 重置 AI 表格 2 的状态
                st.session_state.opt3_t2_done = False
                st.session_state.opt3_full_buffer = None
                st.session_state.opt3_output_sheets = None

            except Exception as e:
                st.error(f"处理文件出错啦！详细错误信息：{e}")

    # =========================================================================
    # 🌟 核心架构：【基础表格下载区】与【AI 运行区】独立悬挂在外，刷新不丢失
    # =========================================================================

    # 第一块：基础表格（表 1、3、4）优先下载区
    if st.session_state.opt3_fast_buffer is not None:
        st.divider()
        st.subheader("⚡ 基础表格（表1、3、4）已就绪，可直接下载")
        st.download_button(
            label="📥 优先下载：基础表格 Excel (包含表1、3、4)",
            data=st.session_state.opt3_fast_buffer,
            file_name="基础报告表格(表1_3_4).xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        
        with st.expander("👀 展开预览基础表格内容", expanded=False):
            if st.session_state.opt3_fast_sheets:
                for s_name, s_df in st.session_state.opt3_fast_sheets.items():
                    st.write(f"**{s_name}**")
                    st.dataframe(s_df, use_container_width=True)

    # 第二块：AI 表格 2 处理区（自动接续运行，不干扰上方下载）
    if gen_t2 and st.session_state.opt3_df is not None:
        st.divider()
        st.subheader("🤖 表格 2：AI 阳性医学建议生成中")

        if not st.session_state.opt3_t2_done:
            df = st.session_state.opt3_df
            t2_data = []
            progress_bar = st.progress(0)
            status_text = st.empty()
            total_count = len(df)

            for i, row in df.iterrows():
                idx = i + 1
                name = row.get('姓名', '')
                conclusion_text = str(row.get('结论词', '')).strip()

                status_text.text(f"正在使用 AI 处理 {name} 的医学建议 ({idx}/{total_count})...")

                if not conclusion_text or conclusion_text == 'nan':
                    final_advice = ""
                else:
                    ai_prompt = f"""【角色与任务】
你是一个无情的医疗数据格式化提取工具，不需要任何礼貌用语和总结废话。你的唯一任务是为体检结论补充建议，并严格按公式拼接。

【格式公式】
必须严格按照以下公式拼接当前客户所有的结论，合并成纯文本的一整段话：
{{序号}}. {{结论词}}：{{医学建议}}，就诊科室：{{科室名称}}。

【绝对禁止（负面清单）】
1. 绝对禁止输出“医学建议：”、“推荐就诊科室：”等多余的过渡标签词，直接按公式无缝拼接！
2. 绝对禁止使用Markdown格式（如 **加粗** 或 # 标题）。
3. 绝对禁止换行，所有编号必须连在同一行！

【标准示范（Few-Shot）】
输入：1. 超重 2. 肝囊肿 3. 左耳高频轻度听力损失
输出：1. 超重：建议控制饮食，增加运动，调整生活方式，必要时就诊内分泌科评估。2. 肝囊肿：建议定期复查，观察囊肿变化，必要时就诊肝胆外科咨询。3. 左耳高频轻度听力损失：建议进行听力康复训练，就诊耳鼻喉科评估听力情况及治疗方案。

【当前任务】
输入：{conclusion_text}
输出："""
                    try:
                        messages = [{"role": "user", "content": ai_prompt}]
                        ai_reply = call_ai_api(opt3_provider, opt3_model, messages, use_gbz=False)
                        final_advice = ai_reply.strip().replace('\n', '')
                    except Exception as e:
                        final_advice = f"AI处理出错: {e}"

                t2_data.append({'编号': idx, '姓名': name, '主要阳性结果及医学建议': final_advice})
                progress_bar.progress((i + 1) / total_count)

            status_text.text("✅ AI 医学建议处理全部完成！")

            # 合并表1、3、4 与 表2 生成完整全套 Excel
            full_sheets = dict(st.session_state.opt3_fast_sheets) if st.session_state.opt3_fast_sheets else {}
            full_sheets['表格2_阳性结果及建议'] = pd.DataFrame(t2_data)

            full_buffer = io.BytesIO()
            with pd.ExcelWriter(full_buffer, engine='openpyxl') as writer:
                for sheet_name, sheet_df in full_sheets.items():
                    sheet_df.to_excel(writer, sheet_name=sheet_name, index=False)

            st.session_state.opt3_full_buffer = full_buffer.getvalue()
            st.session_state.opt3_output_sheets = full_sheets
            st.session_state.opt3_t2_done = True
            st.rerun()

        # AI 完成后的全套下载按钮
        if st.session_state.opt3_t2_done and st.session_state.opt3_full_buffer is not None:
            st.success("🎉 全套表格（含 AI 表格 2）已全部生成完毕！")
            st.download_button(
                label="📥 点击下载完整全套报告书 Excel (包含表1、2、3、4)",
                data=st.session_state.opt3_full_buffer,
                file_name="报告书最终表格全集(含AI建议).xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
            with st.expander("👀 预览表格 2（阳性结果及建议）", expanded=False):
                if st.session_state.opt3_output_sheets and '表格2_阳性结果及建议' in st.session_state.opt3_output_sheets:
                    st.dataframe(st.session_state.opt3_output_sheets['表格2_阳性结果及建议'], use_container_width=True)

    # ==========================
    # 💡 底部固定展示的示例区
    # ==========================
    st.divider()
    st.subheader("💡 上传表格与生成成果示例")
    
    st.write("**1. 上传的源表格样式（只需包含对应列名）：**")
    example_input_df = pd.DataFrame({
        "姓名": ["布洪波", "蔡磊"],
        "性别": ["男", "男"],
        "IdCardNo": ["110105199001011234", "110105198505055678"],
        "workno": ["5", "8"],
        "团体部门": ["物资供应部", "制造五部"],
        "worktype": ["下料工", "氧化工"],
        "岗位危害因素": ["噪声", "硫酸盐酸、氢氧化钠"],
        "WorkAgeOccuTouched": ["本次在岗期间...", "本次在岗期间..."],
        "结论词": ["1. 超重\n2. 肝囊肿", "1. 肥胖\n2. 高血压2级"],
        "Occuadvice": [
            "本次在岗期间职业健康检查未发现噪声作业目标疾病，可以继续从事原岗位作业。", 
            "本次在岗期间职业健康检查未发现酸雾或酸酐作业目标疾病，可以从事原岗位作业。"
        ]
    })
    st.dataframe(example_input_df, use_container_width=True)

    st.write("**2. 生成的【表格 1：职业健康检查结果汇总表】示例：**")
    example_t1_df = pd.DataFrame({
        "编号": [1, 2],
        "姓名": ["布洪波", "蔡磊"],
        "性别": ["男", "男"],
        "身份证号": ["110105199001011234", "110105198505055678"],
        "检查": ["在岗", "在岗"],
        "车间": ["物资供应部", "制造五部"],
        "工种": ["下料工", "氧化工"],
        "职业病危害因素": ["噪声", "硫酸盐酸、氢氧化钠"],
        "工龄": ["5", "8"],
        "个体体检结论": ["其他疾病或异常", "其他疾病或异常"],
        "职业健康处理意见": [
            "本次在岗期间职业健康检查未发现噪声作业目标疾病，可以继续从事原岗位作业。", 
            "本次在岗期间职业健康检查未发现酸雾或酸酐作业目标疾病，可以从事原岗位作业。"
        ]
    })
    st.dataframe(example_t1_df, use_container_width=True)

    st.write("**3. 生成的【表格 2：主要阳性结果及医学建议】示例（经 AI 处理后不换行）：**")
    example_t2_df = pd.DataFrame({
        "编号": [1, 2],
        "姓名": ["布洪波", "蔡磊"],
        "主要阳性结果及医学建议": [
            "1. 超重：控制饮食和总摄入热量，适当增加运动量，建议内分泌科就诊。2. 肝囊肿：建议到肝胆外科定期复查彩超，必要时进一步诊治。",
            "1. 肥胖：控制饮食和总摄入热量，适当增加运动量，建议营养门诊就诊。2. 高血压2级：规律作息，低盐低脂饮食，建议心血管内科就诊。"
        ]
    })
    st.dataframe(example_t2_df, use_container_width=True)

    st.write("**4. 生成的【表格 3】与【表格 4】示例：**")
    col_ex1, col_ex2 = st.columns(2)
    with col_ex1:
        st.caption("表格 3：个体结论统计表")
        example_t3_df = pd.DataFrame({
            "体检类别": ["上岗", "在岗", "在岗"],
            "职业病危害因素名称": ["丙酮", "噪声", "苯、甲苯、二甲苯"],
            "应检人数": [2, 32, 22]
        })
        st.dataframe(example_t3_df, use_container_width=True)
    with col_ex2:
        st.caption("表格 4：职业健康检查对象")
        example_t4_df = pd.DataFrame({
            "体检类别": ["上岗前", "在岗期间"],
            "车间": ["计量检试中心", "物资供应部"],
            "工种": ["环境试验工", "下料工"],
            "职业病危害因素名称": ["噪声", "噪声"],
            "委托人数": [2, 2]
        })
        st.dataframe(example_t4_df, use_container_width=True)

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
                {"role": "assistant", "content": "你好！我是 AI 测试助手，当前接口正常运行，你想测试什么？"}
            ]
            st.rerun()

    st.write("姐姐可以在这里随意测试各个 API 接口与模型的可用性：")

    # 1. 下拉菜单选择 API 厂商与模型
    provider_list = list(API_CONFIGS.keys())

    # 🌟 智能判断默认选中项：能连外网默认选择【智谱 AI】，纯内网自动切换为【本地小模型】
    if check_network_environment():
      # 外网：自动匹配名称中包含“智谱”的选项索引，若未找到则默认第一个
      default_provider_idx = next(
          (i for i, name in enumerate(provider_list) if "智谱" in name), 0
      )
    else:
      # 内网：自动匹配名称中包含“本地”或“Ollama”的选项索引
      default_provider_idx = next(
          (
              i
              for i, name in enumerate(provider_list)
              if "本地" in name or "Ollama" in name
          ),
          0,
      )

    col1, col2 = st.columns(2)
    with col1:
      selected_provider = st.selectbox(
          "📌 选择 API 厂商：",
          provider_list,
          index=default_provider_idx,  # 👈 替换为智能判断出的默认索引！
      )
    with col2:
        available_models = API_CONFIGS[selected_provider]["models"]
        selected_model = st.selectbox(
            "🧠 选择具体模型：",
            available_models,
            index=0
        )

    st.caption(
        f"当前使用的接口：`{selected_provider}` | 模型名：`{selected_model}`"
    )

    # 🌟 1. 动态勾选框：控制是否附带 GBZ 188 资料
    is_silicon = "硅基" in selected_provider
    if is_silicon:
      st.info("💡 硅基流动模式：为节省代金券/流量，已自动关闭外部资料携带。")
      attach_gbz = False
    else:
      attach_gbz = st.checkbox(
          "📚 勾选此项：向 AI 附加《GBZ 188-2025》参考资料（适合向智谱/本地小模型提问时开启）",
          value=False,  # 默认不勾选，不浪费任何无谓的 tokens！
      )

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
                    # 传入 attach_gbz 参数：只有勾选了才会带上 txt 内容
                    reply = call_ai_api(
                        selected_provider, selected_model, api_msgs, use_gbz=attach_gbz
                    )
                    
                    st.write(reply)
                    st.session_state.chat_messages.append({"role": "assistant", "content": reply})
                except Exception as e:
                    st.error(f"❌ 调用失败，请检查网络或 API 额度！具体错误：{e}")
# --- 🌸 选项 4 界面 ---
elif menu_choice == " 🌸 选项 4：中老年表情包制作":
    import option_image
    option_image.render_page()                    
                    
