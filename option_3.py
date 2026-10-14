import streamlit as st
import pandas as pd
import io
import re
import cloud_storage

def render_page(smart_read_uploaded_file, get_pinyin_sort_key, API_CONFIGS, check_network_environment, call_ai_api):
    st.title("📝 选项 3：报告书生成与 AI 医学建议（云端挂机版）")
    st.write("上传表格后，AI 阳性建议可在云端慢慢跑，支持关掉网页稍后回来下载！")

    check_all = st.checkbox("✅ 全选表格", value=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1: gen_t1 = st.checkbox("📊 表格 1", value=check_all)
    with c2: gen_t2 = st.checkbox("🤖 表格 2(含AI)", value=check_all)
    with c3: gen_t3 = st.checkbox("📈 表格 3", value=check_all)
    with c4: gen_t4 = st.checkbox("📋 表格 4", value=check_all)

    provider_list = list(API_CONFIGS.keys())
    opt3_provider = st.selectbox("📌 选择 API 厂商：", provider_list, key="opt3_prov")
    opt3_model = st.selectbox("🧠 选择模型：", API_CONFIGS[opt3_provider]["models"], key="opt3_mod")

    uploaded_file = st.file_uploader("上传 Excel 文件", type=["xlsx", "xls"], key="opt3_up")

    if uploaded_file is not None:
        if st.button("🚀 提交至云端后台开始生成全套表格", use_container_width=True):
            with st.spinner("☁️ 正在处理并生成基础表格与云端 AI 建议..."):
                try:
                    df = smart_read_uploaded_file(uploaded_file)
                    df.columns = [str(c).strip() for c in df.columns]
                    
                    if '姓名' in df.columns:
                        df['pinyin_key'] = df['姓名'].apply(get_pinyin_sort_key)
                        df = df.sort_values(by=['pinyin_key']).drop(columns=['pinyin_key'])
                    df = df.reset_index(drop=True)

                    def get_exam_type(text):
                        return "上岗" if "上岗" in str(text) else ("离岗" if "离岗" in str(text) else "ZaiGang")

                    df['检查类别'] = df.get('WorkAgeOccuTouched', '').apply(get_exam_type)
                    fast_sheets = {}

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
                            '工龄': df.get('workno', ''),
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

                    t2_data = []
                    if gen_t2:
                        for i, row in df.iterrows():
                            conclusion_text = str(row.get('结论词', '')).strip()
                            if not conclusion_text or conclusion_text == 'nan':
                                final_advice = ""
                            else:
                                prompt = f"请无多余废话提取并为以下结论补充建议，连成单行纯文本：{conclusion_text}"
                                try:
                                    reply = call_ai_api(opt3_provider, opt3_model, [{"role": "user", "content": prompt}], use_gbz=False)
                                    final_advice = reply.strip().replace('\n', '')
                                except Exception as e:
                                    final_advice = f"AI错误: {e}"
                            t2_data.append({'编号': i+1, '姓名': row.get('姓名', ''), '主要阳性结果及医学建议': final_advice})
                        fast_sheets['表格2_阳性结果及建议'] = pd.DataFrame(t2_data)

                    # 打包存入 Supabase 云端
                    out_buffer = io.BytesIO()
                    with pd.ExcelWriter(out_buffer, engine='openpyxl') as writer:
                        for s_name, s_df in fast_sheets.items():
                            s_df.to_excel(writer, sheet_name=s_name, index=False)
                    
                    excel_bytes = out_buffer.getvalue()
                    result_url = cloud_storage.upload_bytes_to_supabase(excel_bytes, "报告书最终表格全集(含AI建议).xlsx")
                    
                    if result_url and result_url.startswith("http"):
                        st.success("🎉 全套表格已在云端后台完美生成并安全存入 Supabase！")
                        st.markdown(f"📥 **[点击直接下载完整全套报告书 Excel]({result_url})**")
                    else:
                        st.download_button("📥 点击下载完整全套报告书 Excel", data=excel_bytes, file_name="报告书全集.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
                except Exception as e:
                    st.error(f"生成出错: {e}")