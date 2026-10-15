import streamlit as st
import pandas as pd
import io
import re
import cloud_storage

def render_page(smart_read_uploaded_file, get_pinyin_sort_key, API_CONFIGS, check_network_environment, call_ai_api):
# --- 选项 3 ：报告书表格生成 界面 ---
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
    # 🌟 1. 顶部提供选择方式：本地上传 OR 选择云端已存原始表格
    source_type = st.radio("请选择文件来源：", ["📁 上传本地 Excel 文件", "☁️ 选择云端历史原始表格"], horizontal=True)

    uploaded_file = None

    if source_type == "📁 上传本地 Excel 文件":
        local_file = st.file_uploader("点击或拖入上传 Excel 文件", type=["xlsx", "xls"], key="opt3_local")
        if local_file is not None:
            uploaded_file = local_file
            # 🌟 给网页装上“记忆”，防止只要一点击按钮就疯狂重复上传！
            if "last_uploaded_file_3" not in st.session_state or st.session_state.last_uploaded_file_3 != local_file.name:
                cloud_storage.upload_bytes_to_supabase(local_file.getvalue(), local_file.name, folder="option_3/raw")
                st.session_state.last_uploaded_file_3 = local_file.name
    else:
        # 🌟 读取云端原始表格目录 option_3/raw
        raw_cloud_files = cloud_storage.list_supabase_files(folder="option_3/raw")
        if raw_cloud_files:
            options_map = {f["display_name"]: f for f in raw_cloud_files}
            chosen_display = st.selectbox("请选择要重新分析的云端原始表格：", list(options_map.keys()))
            selected_file_info = options_map[chosen_display]

            st.markdown(f"📥 **[下载选中的云端原始文件]({selected_file_info['download_url']})**")
            
            # 批量管理/删除历史原始表格
            with st.expander("🗑️ 批量管理/删除历史原始表格", expanded=False):
                def toggle_all_raw_3():
                    for f in raw_cloud_files:
                        st.session_state[f"del_chk_raw3_{f['path']}"] = st.session_state.sel_all_raw_3

                st.checkbox("✅ 全选所有原始表格", key="sel_all_raw_3", on_change=toggle_all_raw_3)
                del_raw_list = []
                for f_info in raw_cloud_files:
                    c1, c2 = st.columns([1, 9])
                    with c1:
                        if st.checkbox("勾选", key=f"del_chk_raw3_{f_info['path']}", label_visibility="collapsed"):
                            del_raw_list.append(f_info["path"])
                    with c2:
                        st.write(f_info['display_name'])
                if del_raw_list:
                    if st.button(f"🚨 确认永久删除选中的 {len(del_raw_list)} 个表格", key="btn_del_raw_3"):
                        for p in del_raw_list:
                            cloud_storage.delete_supabase_file(p)
                        st.success("批量删除成功！")
                        st.rerun()

            # 从云端下载字节流供 Python 读取分析
            file_bytes = cloud_storage.download_bytes_from_supabase(selected_file_info["path"])
            if file_bytes:
                uploaded_file = io.BytesIO(file_bytes)
                uploaded_file.name = selected_file_info["file_name"]
        else:
            st.info("☁️ 云端暂无备份的原始表格，请先从本地上传~")

    if uploaded_file is not None:
        # 🌟 新增：增加两种模式的按钮（并排放置）
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            btn_fast = st.button("🚀 网页在线处理（适合几个人，需开着网页等）", use_container_width=True)
        with col_btn2:
            btn_cloud = st.button("☁️ 云端挂机处理（适合几百人，点完可关网页）", type="primary", use_container_width=True)

        # 只要点了任意一个按钮，就触发处理逻辑
        if btn_fast or btn_cloud:
            # 记录当前选择的模式，后续备用
            st.session_state.opt3_run_mode = "cloud" if btn_cloud else "fast"
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
                
                # 🌟 新增：如果点击的是“网页在线处理”，且需要生成表2，才触发刷新让下方代码接续执行
                if st.session_state.opt3_run_mode == "fast" and gen_t2:
                    st.rerun()
                elif st.session_state.opt3_run_mode == "cloud":
                    st.info("☁️ 云端挂机任务已提交！姐姐现在可以关掉网页了，稍后请去底部的【历史记录】中下载结果。")

            except Exception as e:
                st.error(f"处理文件出错啦！详细错误信息：{e}")

    # =========================================================================
    # 🌟 核心架构：【基础表格下载区】与【AI 运行区】独立悬挂在外，刷新不丢失
    # =========================================================================

    # 第一块：基础表格（表 1、3、4）优先下载区 (仅限网页模式或无需表2时显示)
    if st.session_state.opt3_fast_buffer is not None and (not gen_t2 or getattr(st.session_state, "opt3_run_mode", "fast") == "fast"):
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
    # 🌟 修改：只有在“网页模式”下，才在页面上实时展示 AI 进度条
    if gen_t2 and st.session_state.opt3_df is not None and getattr(st.session_state, "opt3_run_mode", "fast") == "fast":
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
            # 🌟 自动保存生成的全套 Excel 结果文件到云端 option_3/result 目录
            export_name = uploaded_file.name.rsplit(".", 1)[0] + "_报告书全集.xlsx"
            cloud_storage.upload_bytes_to_supabase(
                full_buffer.getvalue(),
                file_name=export_name,
                folder="option_3/result"
            )
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

    # 🌟 2. 底部增加折叠框：专门用来查看/下载/批量删除以前自动保存过的云端 Excel 结果
    result_cloud_files = cloud_storage.list_supabase_files(folder="option_3/result")
    if result_cloud_files:
        with st.expander("📜 批量查看/下载/删除云端历史 Excel 成果", expanded=False):
            def toggle_all_res_3():
                for f in result_cloud_files:
                    st.session_state[f"chk_res3_{f['path']}"] = st.session_state.sel_all_res_3
                    
            st.checkbox("✅ 全选所有结果文件", key="sel_all_res_3", on_change=toggle_all_res_3)
            del_res_list = []
            
            for res_file in result_cloud_files:
                col_chk, col_name, col_btn = st.columns([1, 6, 2])
                with col_chk:
                    if st.checkbox("勾选", key=f"chk_res3_{res_file['path']}", label_visibility="collapsed"):
                        del_res_list.append(res_file["path"])
                with col_name:
                    st.write(f"📄 {res_file['display_name']}")
                with col_btn:
                    st.markdown(f"📥 **[点击下载]({res_file['download_url']})**")
            
            if del_res_list:
                if st.button(f"🗑️ 永久删除选中的 {len(del_res_list)} 个结果文件", key="btn_del_res_3"):
                    for p in del_res_list:
                        cloud_storage.delete_supabase_file(p)
                    st.success("批量删除成功！")
                    st.rerun()
    
    
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
