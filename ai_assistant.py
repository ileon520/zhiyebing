import streamlit as st

def render_page(API_CONFIGS, check_network_environment, call_ai_api):
    col_title, col_reset = st.columns([3, 1])
    with col_title:
        st.title("🤖 AI 智能测试助手（云端版）")
    with col_reset:
        if st.button("🧹 新开聊天", use_container_width=True):
            st.session_state.chat_messages = [{"role": "assistant", "content": "你好！我是 AI 测试助手，随时待命！"}]
            st.rerun()

    provider_list = list(API_CONFIGS.keys())
    default_idx = next((i for i, name in enumerate(provider_list) if "智谱" in name), 0) if check_network_environment() else 0

    col1, col2 = st.columns(2)
    with col1:
        selected_provider = st.selectbox("📌 选择 API 厂商：", provider_list, index=default_idx)
    with col2:
        selected_model = st.selectbox("🧠 选择具体模型：", API_CONFIGS[selected_provider]["models"], index=0)

    attach_gbz = st.checkbox("📚 附带《GBZ 188-2025》参考资料", value=False)
    st.divider()

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = [{"role": "assistant", "content": "姐姐好！当前接口正常，你想测试什么？"}]

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    user_input = st.chat_input("请输入测试内容...")
    if user_input:
        st.session_state.chat_messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.write(user_input)

        with st.chat_message("assistant"):
            with st.spinner("AI 思考中..."):
                try:
                    reply = call_ai_api(selected_provider, selected_model, st.session_state.chat_messages, use_gbz=attach_gbz)
                    st.write(reply)
                    st.session_state.chat_messages.append({"role": "assistant", "content": reply})
                except Exception as e:
                    st.error(f"调用失败: {e}")