import streamlit as st
import pandas as pd
import io
import cloud_storage

def render_page(smart_read_uploaded_file):
# --- 选项 2 ：疾控月报表 界面 ---
    st.title("📊 选项 2：疾控月报表自动统计")
    st.write("可以直接把省平台下载的Excel表格上传，也可以只保留【用工单位名称】和【体检危害因素名称】这2列再上传：")
    
    # 🌟 1. 顶部提供选择方式：本地上传 OR 选择云端已存原始表格
    source_type = st.radio("请选择文件来源：", ["📁 上传本地 Excel 文件", "☁️ 选择云端历史原始表格"], horizontal=True)

    file_to_process = None

    if source_type == "📁 上传本地 Excel 文件":
        uploaded_file = st.file_uploader("点击或拖入上传 Excel 文件", type=["xlsx", "xls"], key="opt2_local")
        if uploaded_file is not None:
            file_to_process = uploaded_file

            # 🌟 新增：给网页装上“记忆”，防止只要一点击按钮就疯狂重复上传！
            if "last_uploaded_file_2" not in st.session_state or st.session_state.last_uploaded_file_2 != uploaded_file.name:
                # 自动备份原始文件到云端 option_2/raw
                cloud_storage.upload_bytes_to_supabase(uploaded_file.getvalue(), uploaded_file.name, folder="option_2/raw")
                # 记下这个文件名，下次刷新就不会再瞎传了
                st.session_state.last_uploaded_file_2 = uploaded_file.name
    else:
        # 🌟 只读取原始表格目录 option_2/raw
        raw_cloud_files = cloud_storage.list_supabase_files(folder="option_2/raw")
        if raw_cloud_files:
            options_map = {f["display_name"]: f for f in raw_cloud_files}
            chosen_display = st.selectbox("请选择要重新分析的云端原始表格：", list(options_map.keys()))
            selected_file_info = options_map[chosen_display]

            st.markdown(f"📥 **[下载选中的云端原始文件]({selected_file_info['download_url']})**")
            
            # 👇 新增：批量删除云端原始表格
            with st.expander("🗑️ 批量管理/删除历史原始表格", expanded=False):
                select_all_raw = st.checkbox("✅ 全选所有原始表格", key="sel_all_raw_2")
                del_raw_list = []
                for f_info in raw_cloud_files:
                    c1, c2 = st.columns([1, 9])
                    with c1:
                        if st.checkbox("勾选", value=select_all_raw, key=f"del_chk_raw2_{f_info['path']}", label_visibility="collapsed"):
                            del_raw_list.append(f_info["path"])
                    with c2:
                        st.write(f_info['display_name'])
                if del_raw_list:
                    if st.button(f"🚨 确认永久删除选中的 {len(del_raw_list)} 个表格", key="btn_del_raw_2"):
                        for p in del_raw_list:
                            cloud_storage.delete_supabase_file(p)
                        st.success("批量删除成功！")
                        st.rerun()

            # 从云端下载字节流供 Python 读取分析
            file_bytes = cloud_storage.download_bytes_from_supabase(selected_file_info["path"])
            if file_bytes:
                file_to_process = io.BytesIO(file_bytes)
                file_to_process.name = selected_file_info["file_name"]
        else:
            st.info("☁️ 云端暂无备份的原始表格，请先从本地上传~")

    if file_to_process is not None:
        # 🌟 新增：增加手动开始按钮，点一下才开始统计！
        if st.button("🚀 开始生成疾控月报表", use_container_width=True):
            try:
                df = smart_read_uploaded_file(file_to_process)
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
                # 🌟 新增：动态生成导出文件名（原文件名 + _月报表统计.xlsx）
                export_name = file_to_process.name.rsplit(".", 1)[0] + "_月报表统计.xlsx"

                # 自动保存结果文件（存入 option_2/result 目录）
                cloud_storage.upload_bytes_to_supabase(
                    excel_buffer.getvalue(), 
                    file_name=export_name, 
                    folder="option_2/result"
                )
                
                # 网页下载按钮
                st.download_button(
                    label="📥 点击下载统计结果 Excel",
                    data=excel_buffer.getvalue(),
                    file_name=export_name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
                
            except Exception as e:
                st.error(f"处理文件时出错，请检查是否包含所需列！错误信息: {e}")
    # 👇 新增：底部增加折叠框，用来查看和下载以前生成过的 Excel 分析结果历史
    result_cloud_files = cloud_storage.list_supabase_files(folder="option_2/result")
    if result_cloud_files:
        with st.expander("📜 批量查看/下载/删除云端 Excel 结果", expanded=False):
            select_all_res = st.checkbox("✅ 全选所有结果文件", key="sel_all_res_2")
            del_res_list = []
            
            for res_file in result_cloud_files:
                col_chk, col_name, col_btn = st.columns([1, 6, 2])
                with col_chk:
                    if st.checkbox("勾选", value=select_all_res, key=f"chk_res2_{res_file['path']}", label_visibility="collapsed"):
                        del_res_list.append(res_file["path"])
                with col_name:
                    st.write(f"📄 {res_file['display_name']}")
                with col_btn:
                    st.markdown(f"📥 **[点击下载]({res_file['download_url']})**")
            
            if del_res_list:
                if st.button(f"🗑️ 永久删除选中的 {len(del_res_list)} 个结果文件", key="btn_del_res_2"):
                    for p in del_res_list:
                        cloud_storage.delete_supabase_file(p)
                    st.success("批量删除成功！")
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