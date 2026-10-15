import streamlit as st
import pandas as pd
import io
import os
import socket
from collections import defaultdict
from openai import OpenAI

import option_1
import option_2
import option_3
import ai_assistant


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
elif menu_choice == " 选项 1：报告书百分比转文字":
    option_1.render_page(smart_read_uploaded_file)

elif menu_choice == " 选项 2：疾控月报表":
    option_2.render_page(smart_read_uploaded_file)

elif menu_choice == " 选项 3：报告书表格生成":
    option_3.render_page(smart_read_uploaded_file, get_pinyin_sort_key, API_CONFIGS, check_network_environment, call_ai_api)

# --- 🌸 选项 4 界面 ---
elif menu_choice == " 🌸 选项 4：中老年表情包制作":
    import option_image
    option_image.render_page()                    