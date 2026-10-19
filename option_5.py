import streamlit as st
import pandas as pd
import io
import json

def render_page(smart_read_uploaded_file, API_CONFIGS, check_network_environment, call_ai_api):
    st.title("🏥 选项 5：专家名单自动更新 (AI版)")
    st.write("上传包含医生信息的 Excel 表格，AI 将自动比对最新通讯录，进行专家名单的增、删、改，并自动生成备注。")

    # 1. 提供默认的最新的医生通讯录（姐姐可以随时在网页上手动修改补充）
    default_doctors = """序号	科室	主任	电话	副主任	电话	副主任	电话	
1	EICU/ CICU	乔雯雯	15239010171					
2	肾内	王杰	13403913163	赵建	13253870685			
3	全科医学科	徐爱华	13353913275					
4	神经重症（NCU）	孔侦宇	15239110006					
5	妇科一区（妇瘤一区）	孙丽莎	13403916578					
6	妇科二区（妇瘤科二区）	翟艳红	15939153827					 妇科：孙丽莎 13403916578 翟艳红15939153827
7	妇产科	谢淑红	15939144807					
8	盆底康复科	孙悦	13513816859					
9	胸外一	郭金成	13839170368					
10	胸外科二区（胸心外科）	宁玉林	13782851128					
11	胸外科三区（心脏大血管外科）	高新芳	13523918007					
12	心血管内科一区	苏毅	13203912236					心内科：苏毅13203912236 薛鸿群13598520088 顾冰15838900099
13	心血管内科二区	薛鸿群	13598520088					
14	老年医学（心内三区）	顾冰	15838900099					
15	神内一区	王林	13803912906					
16	神经内科二区	李波	13569133739					神经内科：王林13803912906 李波13569133739 姬松波13603915115
17	神经内科三区	姬松波	13603915115					
18	消化内科一区	王国庆	18739155223					消化内科：王国庆18739155223  王魁彬18639186518 赵宇亮13608635205
19	消化内科二区	王魁彬	18639186518					
20	消化内科三区（感染性疾病科）	赵宇亮	13608635205					
21	肿瘤内科一区	李丽	18603912883					
22	肿内二区	李春艳	13839175467					
23	呼吸与危重症医学科	许新举	13569183612	侯小花	15938103560	屈肖杰	15838982388	
24	风湿免疫科	刘泽有	13083848500	杨金玲	15938178880			
25	中医科	蔡焦生	18739140960					
26	儿  科	杨菊萍	13949656828	陈静	15938103192			
27	内分泌科一区	周雪红	13569108876					
28	内分泌二区	张一平	15639155513					
29	血液淋巴瘤科	刘晓娟	13939176877					
30	普通外科一区	王银中	13782653224					普外科 王银中 13782653224 乔超锋 15138019982  苏威强15138090762
31	普外二区	乔超锋	15138019982					
32	普通外科三区（血管外科）	苏威强	15138090762					
33	骨科一区	谢长伟	13839133425					骨科：谢长伟13839133425 李顺国13069429489 王斌13782638555
34	骨科二区	李顺国	13069429489					
35	骨科三区	王斌	13782638555					
36	创伤显微骨科	倪国华	13598538160					
37	神外一区	王东晓	13343912880					
38	神经外科二区	崔彦魁	13849597922					
39	烧伤整形科	葛玉珍	13839117540					
40	泌尿外科	冀强	13938131623	闫河峰	13782771676			
41	甲状腺乳腺外科一区	马驰骋	13839196606					
42	甲状腺乳腺外科二区	许菊萍	15036522999					
43	耳鼻咽喉头颈外科	薛新中	13803913723	张明	13639629899			
44	口腔科	韩蔚蔚	15603914665	马素霞	15939144035			
45	眼科	樊怡	15139161251					
46	康复医学科	王占峰	13782766578					
47	皮肤科	王坤	15824852112					
48	肛肠科	孙留生	13183138383					
49	疼痛科	刘峰	18697758303					
50	放疗病房	陈剑	13782833139					
51	微创介入科	秦春堂	18639186069					
52	急诊医学科主任	张彦杰	13839115231					
53	麻醉手术一部	荆凤娥	15138081258					
54	男科	杨振辉	13723150276"""
    
    st.subheader("📋 步骤一：确认或修改最新通讯录")
    doctor_list = st.text_area("最新医生名单基准（昭昭已为你默认填入）：", value=default_doctors, height=200)

    # 2. AI 配置区
    st.subheader("⚙️ 步骤二：AI 模型配置")
    provider_list = list(API_CONFIGS.keys())
    if check_network_environment():
        default_idx = next((i for i, name in enumerate(provider_list) if "智谱" in name), 0)
    else:
        default_idx = next((i for i, name in enumerate(provider_list) if "本地" in name or "Ollama" in name), 0)

    col_ai1, col_ai2 = st.columns(2)
    with col_ai1:
        opt5_provider = st.selectbox("📌 选择 API 厂商：", provider_list, index=default_idx, key="opt5_provider")
    with col_ai2:
        opt5_model = st.selectbox("🧠 选择具体模型：", API_CONFIGS[opt5_provider]["models"], index=0, key="opt5_model")

    # 3. 文件上传与列选择
    st.subheader("📂 步骤三：上传表格并处理")
    uploaded_file = st.file_uploader("点击或拖入上传要处理的 Excel 文件", type=["xlsx", "xls"], key="opt5_upload")

    if uploaded_file is not None:
        df = smart_read_uploaded_file(uploaded_file)
        st.write("👀 表格数据预览：")
        st.dataframe(df.head(3), use_container_width=True)

        cols = df.columns.tolist()
        st.info("💡 昭昭提示：请在下方选择你需要处理的列（比如 W列 或 U列 对应的实际表头名字）。")
        target_cols = st.multiselect("🎯 选择需要批量处理的列名：", cols)

        if target_cols:
            if st.button("🚀 开始智能处理", use_container_width=True):
                progress_bar = st.progress(0)
                status_text = st.empty()
                total_rows = len(df)
                
                # 针对选择的每一列，新增一个对应的“修改备注”列
                for col in target_cols:
                    df[f"{col}_备注(X列)"] = ""

                for i, row in df.iterrows():
                    status_text.text(f"正在使用 AI 处理第 {i+1}/{total_rows} 行数据...")
                    
                    for col in target_cols:
                        original_val = str(row[col])
                        if pd.isna(row[col]) or original_val.strip() == "" or original_val.strip() == "nan":
                            continue
                        
                        # 构建专属 AI 提示词
                        ai_prompt = f"""你是一个专业的医疗文本数据处理助手。请严格以 JSON 格式返回。
【最新全院通讯录】：
{doctor_list}

【需要处理的原文本】：
{original_val}

【处理规则】：
1. 原来文本里的医生人名，如果没有在最新通讯录里，请删掉。
2. 原来的人名，如果在通讯录里且电话变了，更新为新电话。
3. 如果原文本提到了某个科室的专家（例如“神经内科：xxx”），请根据通讯录，把该科室最新的所有专家和电话都补充上去。
4. 文本其余的医学建议和格式（如标点符号）保持完全不变！

【输出格式要求】：
必须严格输出 JSON 格式，且只包含两个字段：
{{
    "updated_text": "修改后的完整文本",
    "remarks": "用一句话备注修改了什么。例如：删除了徐建银、李志平；更新了李波的电话；新增了王林、姬松波。如果没有修改，请填 '无变化'。"
}}
"""
                        messages = [{"role": "user", "content": ai_prompt}]
                        try:
                            reply = call_ai_api(opt5_provider, opt5_model, messages, use_gbz=False)
                            # 清理AI可能返回的 markdown 代码块
                            clean_reply = reply.strip()
                            if clean_reply.startswith("```json"): clean_reply = clean_reply[7:]
                            elif clean_reply.startswith("```"): clean_reply = clean_reply[3:]
                            if clean_reply.endswith("```"): clean_reply = clean_reply[:-3]
                            
                            res_dict = json.loads(clean_reply.strip())
                            
                            # 更新 DataFrame 数据
                            df.at[i, col] = res_dict.get("updated_text", original_val)
                            df.at[i, f"{col}_备注(X列)"] = res_dict.get("remarks", "无修改")
                            
                        except Exception as e:
                            df.at[i, f"{col}_备注(X列)"] = f"AI处理出错或格式异常"

                    progress_bar.progress((i + 1) / total_rows)

                status_text.text("✅ 所有数据处理完毕！")
                
                # 将处理后的数据转换为 Excel 供下载
                output_buffer = io.BytesIO()
                with pd.ExcelWriter(output_buffer, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False)
                
                st.divider()
                st.success("🎉 数据已全部更新，并已在表格后方附加了备注列！")
                st.dataframe(df.head(10), use_container_width=True)
                
                st.download_button(
                    label="📥 点击下载处理后的 Excel",
                    data=output_buffer.getvalue(),
                    file_name="专家名单更新结果.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
