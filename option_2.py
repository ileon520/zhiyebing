import streamlit as st
import pandas as pd
import io
import cloud_storage

def render_page():
    st.title("📊 选项 2：疾控月报表自动统计（云端版）")
    st.write("上传省平台下载的Excel表格（包含【用工单位名称】和【体检危害因素名称】）：")
    
    uploaded_file = st.file_uploader("点击或拖入上传 Excel 文件", type=["xlsx", "xls"], key="cdc_upload")
    
    if uploaded_file is not None:
        try:
            uploaded_file.seek(0)
            df = pd.read_excel(uploaded_file, dtype=str)
            df = df.dropna(subset=['用工单位名称', '体检危害因素名称'])
            
            unit_count = len(df['用工单位名称'].unique())
            st.success(f"✅ 文件读取成功！共检测到 {unit_count} 个单位。")
            
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

            output_data = []
            def add_table_to_data(temp_df, title):
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
                output_data.append({"危害因素": "", "接触职业病危害因素人数": ""})
            
            add_table_to_data(df, "1-3 表格：全因素汇总表")
            for unit in df['用工单位名称'].unique():
                add_table_to_data(df[df['用工单位名称'] == unit], f"1-2 表格：{unit}")
            
            result_df = pd.DataFrame(output_data)
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                result_df.to_excel(writer, index=False, header=False)
            
            excel_bytes = excel_buffer.getvalue()
            if st.button("☁️ 生成并保存统计报表至云端", use_container_width=True):
                result_url = cloud_storage.upload_bytes_to_supabase(excel_bytes, "月报表统计结果.xlsx")
                if result_url and result_url.startswith("http"):
                    st.success("🎉 统计报表已成功安全存入 Supabase 云端！")
                    st.markdown(f"📥 **[点击直接下载统计结果 Excel]({result_url})**")
                else:
                    st.download_button("📥 点击下载统计结果 Excel", data=excel_bytes, file_name="月报表统计结果.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
        except Exception as e:
            st.error(f"处理文件出错: {e}")