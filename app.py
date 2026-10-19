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
import ui_components


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
    },
    
    # 👇 下面这几行是这次给姐姐加的选项 5：
    {
        "name": " 🏥 选项 5：专家名单自动更新", 
        "tags": ["#专家名片", "#通讯录更新", "#AI处理"], 
        "desc": "自动核对并更新指定列的专家姓名与电话，生成修改备注"
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
# 2. 渲染配色主题与自定义 CSS
ui_components.render_theme()

# 3. 渲染侧边栏导航、搜索框与标签筛选
menu_choice = ui_components.render_navigation(APP_OPTIONS)

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
    ai_assistant.render_page(API_CONFIGS, check_network_environment, call_ai_api)


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
# --- 🏥 选项 5 界面 ---
elif menu_choice == " 🏥 选项 5：专家名单自动更新":
    import option_5
    option_5.render_page(smart_read_uploaded_file, API_CONFIGS, check_network_environment, call_ai_api)
