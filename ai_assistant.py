import streamlit as st

def render_page(API_CONFIGS, check_network_environment, call_ai_api):
    """渲染 AI 智能测试助手的交互界面"""
    col_title, col_reset = st.columns([3, 1])
    with col_title:
        st.title("🤖 AI 智能测试助手")
    with col_reset:
        if st.button("🧹 新开聊天", use_container_width=True):
            st.session_state.chat_messages = [
                {"role": "assistant", "content": "你好！我是 AI 测试助手，当前接口正常运行，你想测试什么？"}
            ]
            st.rerun()

    st.write("姐姐可以在这里随意测试各个 API 接口与模型的可用性：")

    provider_list = list(API_CONFIGS.keys())

    if check_network_environment():
        default_provider_idx = next(
            (i for i, name in enumerate(provider_list) if "智谱" in name), 0
        )
    else:
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
            index=default_provider_idx,
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

    is_silicon = "硅基" in selected_provider
    if is_silicon:
        st.info("💡 硅基流动模式：为节省代金券/流量，已自动关闭外部资料携带。")
        attach_gbz = False
    else:
        attach_gbz = st.checkbox(
            "📚 勾选此项：向 AI 附加《GBZ 188-2025》参考资料（适合向智谱/本地小模型提问时开启）",
            value=False,
        )

    st.divider()

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = [
            {"role": "assistant", "content": "姐姐好！我是 AI 测试助手，当前接口正常运行，你想测试什么？"}
        ]

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    user_input = st.chat_input("请输入你想对 AI 说的测试内容...")
    if user_input:
        st.session_state.chat_messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.write(user_input)

        with st.chat_message("assistant"):
            with st.spinner("AI 思考中，请稍候..."):
                try:
                    api_msgs = [{"role": m["role"], "content": m["content"]} for m in st.session_state.chat_messages]
                    reply = call_ai_api(
                        selected_provider, selected_model, api_msgs, use_gbz=attach_gbz
                    )
                    st.write(reply)
                    st.session_state.chat_messages.append({"role": "assistant", "content": reply})
                except Exception as e:
                    st.error(f"❌ 调用失败，请检查网络或 API 额度！具体错误：{e}")