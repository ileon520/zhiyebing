import streamlit as st
import pandas as pd
from collections import defaultdict
import cloud_storage

def smart_read_uploaded_file(uploaded_file):
    try:
        uploaded_file.seek(0)
        return pd.read_excel(uploaded_file, dtype=str)
    except Exception:
        pass
    try:
        uploaded_file.seek(0)
        return pd.read_excel(uploaded_file, engine='xlrd', dtype=str)
    except Exception:
        pass
    try:
        uploaded_file.seek(0)
        dfs = pd.read_html(uploaded_file)
        if dfs:
            return dfs[0].astype(str)
    except Exception:
        pass
    for enc in ['utf-8', 'gbk', 'gb18030', 'utf-16', 'utf-16-le', 'ansi']:
        try:
            uploaded_file.seek(0)
            return pd.read_csv(uploaded_file, encoding=enc, dtype=str)
        except Exception:
            continue
    raise ValueError("无法识别的表格格式！")

def render_page():
    st.title("📊 选项 1：Excel 异常检出率分析与 TXT 导出（云端版）")
    st.write("拖入任意 Excel 表格（包含“项目”、“检查人数”、“异常人数”列即可）：")
    uploaded_file = st.file_uploader("点击或拖入上传 Excel 文件", type=["xlsx", "xls"], key="opt1_up")
    
    if uploaded_file is not None:
        try:
            df = smart_read_uploaded_file(uploaded_file)
            df.columns = df.columns.str.strip()
            with st.expander("点击展开预览 Excel 表格内容", expanded=True):
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
            st.markdown("### 生成的描述文本预览：")
            st.text_area("生成文本内容（已自动首行缩进）", full_content, height=250)
            
            export_name = uploaded_file.name.rsplit('.', 1)[0] + "_描述.txt"
            file_bytes = full_content.encode('utf-8')
            
            if st.button("☁️ 生成并保存至云端存储", use_container_width=True):
                result_url = cloud_storage.upload_bytes_to_supabase(file_bytes, export_name)
                if result_url and result_url.startswith("http"):
                    st.success("🎉 成功保存至 Supabase 云端！")
                    st.markdown(f"📥 **[点击直接下载生成的 TXT 文件]({result_url})**")
                else:
                    st.download_button("📥 点击下载生成的 TXT 文本文件", data=file_bytes, file_name=export_name, mime="text/plain", use_container_width=True)
        except Exception as e:
            st.error(f"处理文件时出错: {e}")