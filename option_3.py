import streamlit as st
import pandas as pd
import io
import re
import cloud_storage

def render_page(smart_read_uploaded_file, get_pinyin_sort_key, API_CONFIGS, check_network_environment, call_ai_api):
    st.title("📝 选项 3：报告书生成与 AI 医学建议（支持云端挂机）")
    st.write("请上传包含体检信息的 Excel 表格：")

    if "opt3_fast_buffer" not in st.session_state: st.session_state.opt3_fast_buffer = None
    if "opt3_fast_sheets" not in st.session_state: st.session_state.opt3_fast_sheets = None
    if "opt3_full_buffer" not in st.session_state: st.session_state.opt3_full_buffer = None
    if "opt3_output_sheets" not in st.session_state: st.session_state.opt3_output_sheets = None
    if "opt3_t2_done" not in st.session_state: st.session_state.opt3_t2_done = False
    if "opt3_df" not in st.session_state: st.session_state.opt3_df = None

    st.subheader("⚙️ 第一步：选择需要生成的表格")
    check_all = st.checkbox("✅ 全选（勾选后自动选中下方所有表格）", value=True)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1: gen_t1 = st.checkbox("📊 表格 1：结果汇总表", value=check_all)
    with col2: gen_t2 = st.checkbox("🤖 表格 2：阳性结果(需AI)", value=check_all)
    with col3: gen_t3 = st.checkbox("📈 表格 3：个体结论统计", value=check_all)
    with col4: gen_t4 = st.checkbox("📋 表格 4：检查对象", value=check_all)

    if gen_t2:
        st.info("💡 提示：生成表格 2 需要使用 AI 进行医学建议改写。请选择下方接口：")
        provider_list = list(API_CONFIGS.keys())
        default_idx = next((i for i, name in enumerate(provider_list) if "智谱" in name), 0) if check_network_environment() else 0
            
        col_ai1, col_ai2 = st.columns(2)
        with col_ai1:
            opt3_provider = st.selectbox("📌 选择 API 厂商：", provider_list, index=default_idx, key="opt3_provider")
        with col_ai2:
            opt3_model = st.selectbox("🧠 选择具体模型：", API_CONFIGS[opt3_provider]["models"], index=0, key="opt3_model")

    st.subheader("📂 第二步：上传表格并生成")
    uploaded_file = st.file_uploader("点击或拖入上传 Excel 文件", type=["xlsx", "xls"], key="opt3_upload")

    if uploaded_file is not None:
        if st.button("🚀 开始处理并生成选中的表格", use_container_width=True):
            try:
                df = smart_read_uploaded_file(uploaded_file)
                df.columns = [str(c).strip() for c in df.columns]

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
                
                if '姓名' in df.columns:
                    df['pinyin_key'] = df['姓名'].apply(get_pinyin_sort_key)
                    sort_cols = ['pinyin_key']
                    if 'IdCardNo' in df.columns: sort_cols.append('IdCardNo')
                    df = df.sort_values(by=sort_cols, ascending=[True] * len(sort_cols)).drop(columns=['pinyin_key'])
                
                df = df.reset_index(drop=True)
                st.session_state.opt3_df = df

                fast_sheets = {}
                def get_exam_type(text):
                    text = str(text)
                    if "上岗" in text: return "上岗"
                    elif "离岗" in text: return "离岗"
                    else: return "在岗"

                df['检查类别'] = df.get('WorkAgeOccuTouched', '').apply(get_exam_type)
                workage_col_name = next((c for c in df.columns if any(k in str(c).lower() for k in ['工龄', 'workage', 'workno', '接害年限', '接害工龄'])), None)
                t1_workage = df[workage_col_name] if workage_col_name else df.get('workno', df.get('工龄', ''))

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

                if gen_t3:
                    t3_records = []
                    for _, row in df.iterrows():
                        for h in [h.strip() for h in re.split(r'[、,\s]+', str(row.get('岗位危害因素', ''))) if h.strip()]:
                            t3_records.append({'体检类别': row['检查类别'], '职业病危害因素名称': h})
                    if t3_records:
                        fast_sheets['表格3_个体结论统计表'] = pd.DataFrame(t3_records).groupby(['体检类别', '职业病危害因素名称']).size().reset_index(name='应检人数')

                if gen_t4:
                    t4_grouped = df.groupby(['检查类别', '团体部门', 'worktype', '岗位危害因素']).size().reset_index(name='委托人数')
                    t4_grouped.rename(columns={'检查类别': '体检类别', '团体部门': '车间', 'worktype': '工种', '岗位危害因素': '职业病危害因素名称'}, inplace=True)
                    fast_sheets['表格4_检查对象表'] = t4_grouped

                if fast_sheets:
                    fast_buffer = io.BytesIO()
                    with pd.ExcelWriter(fast_buffer, engine='openpyxl') as writer:
                        for sheet_name, sheet_df in fast_sheets.items():
                            sheet_df.to_excel(writer, sheet_name=sheet_name, index=False)
                    st.session_state.opt3_fast_buffer = fast_buffer.getvalue()
                    st.session_state.opt3_fast_sheets = fast_sheets
                    st.success("⚡ 基础表格（表1、3、4）已就绪！")

                st.session_state.opt3_t2_done = False
                st.session_state.opt3_full_buffer = None
                st.session_state.opt3_output_sheets = None
            except Exception as e:
                st.error(f"处理文件出错啦：{e}")

    if st.session_state.opt3_fast_buffer is not None:
        st.divider()
        st.subheader("⚡ 基础表格（表1、3、4）已就绪，可直接下载")
        c_dl1, c_dl2 = st.columns(2)
        with c_dl1:
            st.download_button(
                label="📥 优先下载：基础表格 Excel",
                data=st.session_state.opt3_fast_buffer,
                file_name="基础报告表格(表1_3_4).xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        with c_dl2:
            if st.button("☁️ 将基础表格存入云端 (Supabase)", use_container_width=True):
                url = cloud_storage.upload_bytes_to_supabase(st.session_state.opt3_fast_buffer, "基础报告表格(表1_3_4).xlsx")
                if url and url.startswith("http"):
                    st.success("🎉 已存入 Supabase 云端！")
                    st.markdown(f"📥 **[点击下载云端基础表格]({url})**")

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
{{序号}}. {{结论词}}：{{医学建议}}，就诊科室：{{科室名称}}。
【当前任务】
输入：{conclusion_text}
输出："""
                    try:
                        reply = call_ai_api(opt3_provider, opt3_model, [{"role": "user", "content": ai_prompt}], use_gbz=False)
                        final_advice = reply.strip().replace('\n', '')
                    except Exception as e:
                        final_advice = f"AI处理出错: {e}"

                t2_data.append({'编号': idx, '姓名': name, '主要阳性结果及医学建议': final_advice})
                progress_bar.progress((i + 1) / total_count)

            status_text.text("✅ AI 医学建议处理全部完成！")
            full_sheets = dict(st.session_state.opt3_fast_sheets) if st.session_state.opt3_fast_sheets else {}
            full_sheets['表格2_阳性结果及建议'] = pd.DataFrame(t2_data)

            full_buffer = io.BytesIO()
            with pd.ExcelWriter(full_buffer, engine='openpyxl') as writer:
                for sheet_name, sheet_df in full_sheets.items():
                    sheet_df.to_excel(writer, sheet_name=sheet_name, index=False)

            full_bytes = full_buffer.getvalue()
            st.session_state.opt3_full_buffer = full_bytes
            st.session_state.opt3_output_sheets = full_sheets
            st.session_state.opt3_t2_done = True
            
            # 自动同步上传云端
            cloud_storage.upload_bytes_to_supabase(full_bytes, "报告书最终表格全集(含AI建议).xlsx")
            st.rerun()

        if st.session_state.opt3_t2_done and st.session_state.opt3_full_buffer is not None:
            st.success("🎉 全套表格（含 AI 表格 2）已全部生成完毕，并已自动挂载至云端！")
            
            c_full1, c_full2 = st.columns(2)
            with c_full1:
                st.download_button(
                    label="📥 点击下载完整全套报告书 Excel",
                    data=st.session_state.opt3_full_buffer,
                    file_name="报告书最终表格全集(含AI建议).xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            with c_full2:
                if st.button("☁️ 获取云端下载直链 (Supabase)", use_container_width=True):
                    url = cloud_storage.upload_bytes_to_supabase(st.session_state.opt3_full_buffer, "报告书最终表格全集(含AI建议).xlsx")
                    if url and url.startswith("http"):
                        st.markdown(f"📥 **[点击下载云端全套表格]({url})**")

    # 完整保留姐姐的底部示例展示区
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
    st.dataframe(example_input_df, use_container_width=True)