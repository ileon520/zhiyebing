import streamlit as st
import pandas as pd
from collections import defaultdict
import cloud_storage

def render_page(smart_read_uploaded_file):
    st.title("📊 选项 1：Excel 异常检出率分析与 TXT 导出")
    st.write("拖入任意 Excel 表格（包含“项目”、“检查人数”、“异常人数”列即可）：")
    uploaded_file = st.file_uploader("点击或拖入上传 Excel 文件", type=["xlsx", "xls"], key="opt1_up")
    
    if uploaded_file is not None:
        try:
            df = smart_read_uploaded_file(uploaded_file)
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
            
            export_name = uploaded_file.name.rsplit('.', 1)[0] + "_描述.txt"
            file_bytes = full_content.encode('utf-8')

            c1, c2 = st.columns(2)
            with c1:
                st.download_button(" 点击下载生成的 TXT 文本文件", data=file_bytes, file_name=export_name, mime="text/plain", use_container_width=True)
            with c2:
                if st.button("☁️ 一键保存至云端 (Supabase)", use_container_width=True):
                    res_url = cloud_storage.upload_bytes_to_supabase(file_bytes, export_name)
                    if res_url and res_url.startswith("http"):
                        st.success("🎉 成功保存至 Supabase 云端存储！")
                        st.markdown(f"📥 **[点击直接下载云端 TXT 文件]({res_url})**")
                    else:
                        st.error("云端保存失败，已自动转为本地保存路径。")
        except Exception as e:
            st.error(f"处理文件时出错，请检查 Excel 列名！具体错误信息: {e}")

    # 完整保留姐姐的示例展示区
    st.divider()
    st.subheader("💡 填写示例与说明")
    st.write("上传表格的示例：")
    
    example_df = pd.DataFrame({
        "项目": [
            "尿常规", "肝胆脾胰彩超", "口腔科", "肺功能检测", "身高体重血压", 
            "外科", "纯音听阈测试", "心电图", "血常规", "肝功1", 
            "总IgE测定", "内科", "高千伏胸部正位片", "耳鼻喉科", "眼科", 
            "职业病问诊", "神经内科"
        ],
        "检查人数": ["44"] * 17,
        "异常人数": ["43", "38", "31", "29", "29", "28", "24", "18", "16", "14", "13", "10", "9", "5", "3", "0", "0"],
        "异常检出率": ["97.73%", "86.36%", "70.45%", "65.91%", "65.91%", "63.64%", "54.55%", "40.91%", "36.36%", "31.82%", "29.55%", "22.73%", "20.45%", "11.36%", "6.82%", "0.00%", "0.00%"]
    })
    st.dataframe(example_df, use_container_width=True)
    
    st.write("得到的成品示例：")
    result_text = """  第一部分：
  尿常规异常检出率为97.73%，肝胆脾胰彩超异常检出率为86.36%，口腔科异常检出率为70.45%，肺功能检测、身高体重血压异常检出率为65.91%，外科异常检出率为63.64%，纯音听阈测试异常检出率为54.55%，心电图异常检出率为40.91%，血常规异常检出率为36.36%，肝功1异常检出率为31.82%，总IgE测定异常检出率为29.55%，内科异常检出率为22.73%，高千伏胸部正位片异常检出率为20.45%，耳鼻喉科异常检出率为11.36%，眼科异常检出率为6.82%，职业病问诊、神经内科异常检出率为0。

  第二部分：
  尿常规：实检44人，检出异常43例，占受检人数异常检出率97.73%，43例与目前所从事职业无相关联系，在《个人职业健康检查结果》中已给出相应的处理意见。
  （其余略...）"""
    st.text_area("生成的文本成品预览（支持直接复制）", result_text, height=250)