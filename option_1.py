import streamlit as st
import pandas as pd
import io
import os
import socket
from collections import defaultdict
from openai import OpenAI
import cloud_storage  # 引入云端工具

def render_page(smart_read_uploaded_file):
    # 🌟 把原来 app.py 里选项 1 的所有代码（包括文件上传、处理逻辑、底部示例表格）
    # 原封不动地粘贴到这里面来！
# --- 选项 1：报告书百分比转文字 界面 ---
    st.title("📊 选项 1：Excel 异常检出率分析与 TXT 导出")
    st.write("拖入任意 Excel 表格（包含“项目”、“检查人数”、“异常人数”列即可）：")
    # 🌟 1. 顶部提供选择方式：本地上传 OR 选择云端已存原始表格
    source_type = st.radio("请选择文件来源：", ["📁 上传本地 Excel 文件", "☁️ 选择云端历史原始表格"], horizontal=True)

    file_to_process = None

    if source_type == "📁 上传本地 Excel 文件":
        uploaded_file = st.file_uploader("点击或拖入上传 Excel 文件", type=["xlsx", "xls"], key="opt1_local")
        if uploaded_file is not None:
            file_to_process = uploaded_file
            # 自动备份原始文件到云端 option_1/raw
            cloud_storage.upload_bytes_to_supabase(uploaded_file.getvalue(), uploaded_file.name, folder="option_1/raw")
    else:
        # 🌟 只读取原始表格目录 option_1/raw，避免读取到 txt 结果文件导致预览错乱
        raw_cloud_files = cloud_storage.list_supabase_files(folder="option_1/raw")
        if raw_cloud_files:
            options_map = {f["display_name"]: f for f in raw_cloud_files}
            chosen_display = st.selectbox("请选择要重新分析的云端原始表格：", list(options_map.keys()))
            selected_file_info = options_map[chosen_display]

            # 补上下载按钮与删除按钮
            col_dl, col_del = st.columns([3, 2])
            with col_dl:
                st.markdown(f"📥 **[下载选中的云端原始文件]({selected_file_info['download_url']})**")
            with col_del:
                if st.checkbox("⚠️ 确认删除此表格？", key="chk_raw"):
                    if st.button("🗑️ 立即删除", key="del_raw"):
                        cloud_storage.delete_supabase_file(selected_file_info["path"])
                        st.rerun() # 删除后立刻刷新页面

            # 从云端下载字节流供 Python 读取分析
            file_bytes = cloud_storage.download_bytes_from_supabase(selected_file_info["path"])
            if file_bytes:
                file_to_process = io.BytesIO(file_bytes)
                file_to_process.name = selected_file_info["file_name"]
        else:
            st.info("☁️ 云端暂无备份的原始表格，请先从本地上传~")
    if file_to_process is not None:
        # 🌟 新增：增加手动开始按钮，点一下才开始处理！
        if st.button("🚀 开始分析 Excel 异常检出率", use_container_width=True):
            try:
                df = smart_read_uploaded_file(file_to_process)
                df.columns = df.columns.str.strip()
            with st.expander(" 点击展开预览 Excel 表格内容", expanded=True):
                st.dataframe(df.head(10), use_container_width=True)
            
            data_list = []
            for index, row in df.iterrows():
                proj = str(row['项目']).strip()
                total = int(row['检查人数'])
                abnormal = int(row['异常人数'])
                rate_val = (abnormal / total * 100) if total > 0 else 0.0
                data_list.append({'proj': proj, 'total': total, 'abnormal': abnormal, 'rate_val': rate_val})

            sorted_data = sorted(data_list, key=lambda x: x['rate_val'], reverse=True)
            groups = defaultdict(list)
            for item in sorted_data:
                rate_key = "0" if item['rate_val'] == 0 else f"{item['rate_val']:.2f}%"
                groups[rate_key].append(item['proj'])

            part1_segments = [f"{'、'.join(projs)}异常检出率为{rate_key}" for rate_key, projs in groups.items()]
            part1_text = "\u3000\u3000第一部分：\n\u3000\u3000" + "，".join(part1_segments) + "。"

            part2_lines = ["\u3000\u3000第二部分："]
            for item in data_list:
                if item['abnormal'] == 0:
                    part2_lines.append(f"\u3000\u3000{item['proj']}：实检{item['total']}人均未检出异常。")
                else:
                    rate_str = f"{item['rate_val']:.2f}%"
                    part2_lines.append(f"\u3000\u3000{item['proj']}：实检{item['total']}人，检出异常{item['abnormal']}例，占受检人数异常检出率{rate_str}，{item['abnormal']}例与目前所从事职业无相关联系，在《个人职业健康检查结果》中已给出相应的处理意见。")

            full_content = part1_text + "\n\n" + "\n".join(part2_lines)
            st.markdown("###  生成的描述文本预览：")
            st.text_area("生成文本内容（已自动首行缩进）", full_content, height=250)
            
            export_name = file_to_process.name.rsplit(".", 1)[0] + "_描述.txt"
            result_bytes = full_content.encode("utf-8")
            
            # 自动保存结果文件（存入 option_1/result 目录）
            result_cloud_url = cloud_storage.upload_bytes_to_supabase(
                result_bytes, 
                export_name, 
                folder="option_1/result"
            )

            st.success("🎉 分析完成！结果已自动保存至云端。")
            st.markdown(f"📥 **[点击直接下载分析结果 TXT 文件]({result_cloud_url})**")
            except Exception as e:
              st.error(f"处理文件时出错，请检查 Excel 列名！具体错误信息: {e}")
    # 🌟 2. 底部增加折叠框：专门用来查看和下载以前生成过的 TXT 分析结果历史
    result_cloud_files = cloud_storage.list_supabase_files(folder="option_1/result")
    if result_cloud_files:
        with st.expander("📜 查看/下载以前自动保存过的云端 TXT 描述结果", expanded=False):
            for res_file in result_cloud_files:
                col_name, col_btn, col_del = st.columns([5, 2, 3])
                with col_name:
                    st.write(f"📄 {res_file['display_name']}")
                with col_btn:
                    st.markdown(f"📥 **[点击下载]({res_file['download_url']})**")
                with col_del:
                    # 两步防误触安全删除
                    if st.checkbox("确认删除?", key=f"chk_{res_file['path']}"):
                        if st.button("🗑️ 永久删除", key=f"del_{res_file['path']}"):
                            cloud_storage.delete_supabase_file(res_file["path"])
                            st.rerun()
    
    # 增加的示例展示区
    st.divider()
    st.subheader("💡 填写示例与说明")
    st.write("上传表格的示例：")
    
    # 上传表格示例
    example_df = pd.DataFrame({
        "项目": [
            "尿常规", "肝胆脾胰彩超", "口腔科", "肺功能检测", "身高体重血压", 
            "外科", "纯音听阈测试", "心电图", "血常规", "肝功1", 
            "总IgE测定", "内科", "高千伏胸部正位片", "耳鼻喉科", "眼科", 
            "职业病问诊", "神经内科"
        ],
        "检查人数": [
            "44", "44", "44", "44", "44", 
            "44", "44", "44", "44", "44", 
            "44", "44", "44", "44", "44", 
            "44", "44"
        ],
        "异常人数": [
            "43", "38", "31", "29", "29", 
            "28", "24", "18", "16", "14", 
            "13", "10", "9", "5", "3", 
            "0", "0"
        ],
        "异常检出率": [
            "97.73%", "86.36%", "70.45%", "65.91%", "65.91%", 
            "63.64%", "54.55%", "40.91%", "36.36%", "31.82%", 
            "29.55%", "22.73%", "20.45%", "11.36%", "6.82%", 
            "0.00%", "0.00%"
        ]
    })
    st.dataframe(example_df, use_container_width=True)
    
    st.write("得到的成品示例：")

    # 成品展示：使用多行文本框 text_area 显示 txt 效果
    result_text = """  第一部分：
  尿常规异常检出率为97.73%，肝胆脾胰彩超异常检出率为86.36%，口腔科异常检出率为70.45%，肺功能检测、身高体重血压异常检出率为65.91%，外科异常检出率为63.64%，纯音听阈测试异常检出率为54.55%，心电图异常检出率为40.91%，血常规异常检出率为36.36%，肝功1异常检出率为31.82%，总IgE测定异常检出率为29.55%，内科异常检出率为22.73%，高千伏胸部正位片异常检出率为20.45%，耳鼻喉科异常检出率为11.36%，眼科异常检出率为6.82%，职业病问诊、神经内科异常检出率为0。

  第二部分：
  尿常规：实检44人，检出异常43例，占受检人数异常检出率97.73%，43例与目前所从事职业无相关联系，在《个人职业健康检查结果》中已给出相应的处理意见。
  肝胆脾胰彩超：实检44人，检出异常38例，占受检人数异常检出率86.36%，38例与目前所从事职业无相关联系，在《个人职业健康检查结果》中已给出相应的处理意见。
  口腔科：实检44人，检出异常31例，占受检人数异常检出率70.45%，31例与目前所从事职业无相关联系，在《个人职业健康检查结果》中已给出相应的处理意见。
  肺功能检测：实检44人，检出异常29例，占受检人数异常检出率65.91%，29例与目前所从事职业无相关联系，在《个人职业健康检查结果》中已给出相应的处理意见。
  身高体重血压：实检44人，检出异常29例，占受检人数异常检出率65.91%，29例与目前所从事职业无相关联系，在《个人职业健康检查结果》中已给出相应的处理意见。
  外科：实检44人，检出异常28例，占受检人数异常检出率63.64%，28例与目前所从事职业无相关联系，在《个人职业健康检查结果》中已给出相应的处理意见。
  纯音听阈测试：实检44人，检出异常24例，占受检人数异常检出率54.55%，24例与目前所从事职业无相关联系，在《个人职业健康检查结果》中已给出相应的处理意见。
  心电图：实检44人，检出异常18例，占受检人数异常检出率40.91%，18例与目前所从事职业无相关联系，在《个人职业健康检查结果》中已给出相应的处理意见。
  血常规：实检44人，检出异常16例，占受检人数异常检出率36.36%，16例与目前所从事职业无相关联系，在《个人职业健康检查结果》中已给出相应的处理意见。
  肝功1：实检44人，检出异常14例，占受检人数异常检出率31.82%，14例与目前所从事职业无相关联系，在《个人职业健康检查结果》中已给出相应的处理意见。
  总IgE测定：实检44人，检出异常13例，占受检人数异常检出率29.55%，13例与目前所从事职业无相关联系，在《个人职业健康检查结果》中已给出相应的处理意见。
  内科：实检44人，检出异常10例，占受检人数异常检出率22.73%，10例与目前所从事职业无相关联系，在《个人职业健康检查结果》中已给出相应的处理意见。
  高千伏胸部正位片：实检44人，检出异常9例，占受检人数异常检出率20.45%，9例与目前所从事职业无相关联系，在《个人职业健康检查结果》中已给出相应的处理意见。
  耳鼻喉科：实检44人，检出异常5例，占受检人数异常检出率11.36%，5例与目前所从事职业无相关联系，在《个人职业健康检查结果》中已给出相应的处理意见。
  眼科：实检44人，检出异常3例，占受检人数异常检出率6.82%，3例与目前所从事职业无相关联系，在《个人职业健康检查结果》中已给出相应的处理意见。
  职业病问诊：实检44人均未检出异常。
  神经内科：实检44人均未检出异常。"""

    st.text_area("生成的文本成品预览（支持直接复制）", result_text, height=350)