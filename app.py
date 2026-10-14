import streamlit as st
import pandas as pd
import os
import socket
from openai import OpenAI

# 导入所有独立模块
import ui_components
import option_image
import option_1
import option_2
import option_3
import ai_assistant

def smart_read_uploaded_file(uploaded_file):
    try:
        uploaded_file.seek(0)
        return pd.read_excel(uploaded_file, dtype=str)
    except Exception:
        pass
    try:
        uploaded_file.seek(0)
        return pd.read_excel(uploaded_file, engine='xlrd', dtype=str)
    except Exception:
        pass
    try:
        uploaded_file.seek(0)
        dfs = pd.read_html(uploaded_file)
        if dfs:
            return dfs[0].astype(str)
    except Exception:
        pass
    for enc in ['utf-8', 'gbk', 'gb18030', 'utf-16', 'utf-16-le', 'ansi']:
        try:
            uploaded_file.seek(0)
            return pd.read_csv(uploaded_file, encoding=enc, dtype=str)
        except Exception:
            continue
    raise ValueError("无法识别的表格格式！")

try:
    import pypinyin
    def get_pinyin_sort_key(text):
        return ''.join(pypinyin.lazy_pinyin(str(text)))
except ImportError:
    import locale
    def get_pinyin_sort_key(text):
        try:
            locale.setlocale(locale.LC_COLLATE, 'zh_CN.UTF-8')
            return locale.strxfrm(str(text))
        except Exception:
            return str(text)

def check_network_environment():
    try:
        socket.create_connection(("open.bigmodel.cn", 443), timeout=0.5)
        return True
    except Exception:
        return False

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
    "本地小模型 (Ollama - Qwen2.5)": {
        "api_key": "ollama",
        "base_url": "http://127.0.0.1:11434/v1",
        "models": ["qwen2.5:1.5b"]
    }
}

def call_ai_api(provider_name, model_name, messages, use_gbz=False):
    cfg = API_CONFIGS[provider_name]
    client = OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"])
    final_messages = []
    
    if use_gbz and ("硅基" not in provider_name):
        if os.path.exists("GBZ188_2025.txt"):
            try:
                with open("GBZ188_2025.txt", "r", encoding="utf-8") as f:
                    gbz_content = f.read()
                sys_msg = {
                    "role": "system",
                    "content": (
                        "【极其严格的抽取指令】：你是一个只负责精准抽取资料内容的助手。\n"
                        f"【参考资料全文】：\n{gbz_content}"
                    ),
                }
                final_messages.append(sys_msg)
            except Exception:
                pass

    final_messages.extend(messages)
    kwargs = {"model": model_name, "messages": final_messages}
    
    if "本地" in provider_name or "Ollama" in provider_name:
        kwargs["extra_body"] = {"options": {"num_ctx": 16384, "temperature": 0.1}}

    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message.content

APP_OPTIONS = [
    {"name": " 首页控制台", "tags": ["#导航", "#首页"], "desc": "返回主控制台首页"},
    {"name": " 选项 1：报告书百分比转文字", "tags": ["#报告书", "#百分比"], "desc": "上传Excel表格，百分比表格转化为文字描述"},
    {"name": " 选项 2：疾控月报表", "tags": ["#月报表", "#疾控"], "desc": "上传Excel表格，转化为表1-2和1-3的内容"},
    {"name": " 选项 3：报告书表格生成", "tags": ["#报告书", "#表格", "#AI建议"], "desc": "上传包含体检信息的Excel，自动拆分并使用AI生成4种报告书最终表格"},
    {"name": " 🤖 AI 智能测试助手", "tags": ["#AI", "#测试", "#对话"], "desc": "多 API 接口可用性与回答效果测试"},
    {"name": " 🌸 选项 4：中老年表情包制作", "tags": ["#图片", "#表情包", "#花样加字"], "desc": "选择预设荷花/鲜花背景图，一键制作喜庆中老年发光大字表情包"}
]

st.set_page_config(page_title="职业病专属工作台", layout="wide")

if "current_page" not in st.session_state:
    st.session_state.current_page = APP_OPTIONS[0]["name"]

def go_to_page(page_name):
    st.session_state.current_page = page_name

# 调用独立组件：渲染侧边栏配色、搜索和导航
menu_choice = ui_components.render_sidebar_and_navigation(APP_OPTIONS)

# 页面内容路由分发
if menu_choice == " 首页控制台":
    st.title("✨ 职业病专属工作台（云端存储增强版）")
    st.write("点击下方对应按钮，即可一键进入工作区域：")
    st.write("")
    work_options = [opt for opt in APP_OPTIONS if opt["name"] != " 首页控制台"]
    cols = st.columns(3)
    for i, opt in enumerate(work_options):
        with cols[i % 3]:
            with st.container(border=True):
                st.subheader(opt["name"])
                st.write(opt["desc"])
                tags_str = " ".join(opt["tags"])
                st.caption(f"标签：{tags_str}")
                st.button("🚀 开启功能", key=f"btn_{i}", on_click=go_to_page, args=(opt["name"],), use_container_width=True)

elif menu_choice == " 选项 1：报告书百分比转文字":
    option_1.render_page(smart_read_uploaded_file)

elif menu_choice == " 选项 2：疾控月报表":
    option_2.render_page(smart_read_uploaded_file)

elif menu_choice == " 选项 3：报告书表格生成":
    option_3.render_page(smart_read_uploaded_file, get_pinyin_sort_key, API_CONFIGS, check_network_environment, call_ai_api)

elif menu_choice == " 🤖 AI 智能测试助手":
    ai_assistant.render_page(API_CONFIGS, check_network_environment, call_ai_api)

elif menu_choice == " 🌸 选项 4：中老年表情包制作":
    option_image.render_page()