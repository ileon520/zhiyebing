import streamlit as st
import pandas as pd
import io
import cloud_storage

def render_page(smart_read_uploaded_file):
# --- 选项 2 ：疾控月报表 界面 ---
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
            # 👇 新增：自动保存结果文件（存入 option_2/result 目录）
            cloud_storage.upload_bytes_to_supabase(
                excel_buffer.getvalue(), 
                file_name="月报表统计结果.xlsx", 
                folder="option_2/result"
            )
            
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
    # 👇 新增：底部增加折叠框，用来查看和下载以前生成过的 Excel 分析结果历史
    result_cloud_files = cloud_storage.list_supabase_files(folder="option_2/result")
    if result_cloud_files:
        with st.expander("📜 查看/下载以前自动保存过的云端 Excel 结果", expanded=False):
            for res_file in result_cloud_files:
                col_name, col_btn, col_del = st.columns([5, 2, 3])
                with col_name:
                    st.write(f"📄 {res_file['display_name']}")
                with col_btn:
                    st.markdown(f"📥 **[点击下载]({res_file['download_url']})**")
                with col_del:
                    if st.checkbox("确认删除?", key=f"chk_{res_file['path']}"):
                        if st.button("🗑️ 永久删除", key=f"del_{res_file['path']}"):
                            cloud_storage.delete_supabase_file(res_file["path"])
                            st.rerun()
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