import time
import json
import io
import pandas as pd
import cloud_storage
# 引入基础解析与 AI 通用调用函数
from app_4 import smart_read_uploaded_file, get_pinyin_sort_key, call_ai_api

def process_single_task(task_info, t_file_path):
    """处理单个挂机任务的完整 AI 逻辑"""
    task_id = task_info.get("task_id")
    raw_path = task_info.get("raw_path")
    file_name = task_info.get("file_name")
    
    print(f"⚙️ 正在处理挂机任务【{task_id}】 - 文件: {file_name}")

    # 1. 从 Supabase 下载对应的原始 Excel 文件
    raw_bytes = cloud_storage.download_bytes_from_supabase(raw_path)
    if not raw_bytes:
        print(f"❌ 无法从云端下载原始表格: {raw_path}")
        return

    excel_file = io.BytesIO(raw_bytes)
    excel_file.name = file_name
    df = smart_read_uploaded_file(excel_file)
    df.columns = [str(c).strip() for c in df.columns]

    # 2. 清理身份证号与排序
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
        if id_col_name: sort_cols.append(id_col_name)
        df = df.sort_values(by=sort_cols, ascending=[True] * len(sort_cols))
        df = df.drop(columns=['pinyin_key'])
    df = df.reset_index(drop=True)

    import re
    def get_exam_type(text):
        text = str(text)
        if "上岗" in text: return "上岗"
        elif "离岗" in text: return "离岗"
        else: return "在岗"

    df['检查类别'] = df.get('WorkAgeOccuTouched', '').apply(get_exam_type)

    workage_col_name = next((c for c in df.columns if any(k in str(c).lower() for k in ['工龄', 'workage', 'workno', '接害年限', '接害工龄'])), None)
    t1_workage = df[workage_col_name] if workage_col_name else df.get('workno', df.get('工龄', ''))

    output_sheets = {}

    # 生成表 1、3、4
    if task_info.get("gen_t1"):
        output_sheets['表格1_结果汇总表'] = pd.DataFrame({
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

    if task_info.get("gen_t3"):
        t3_records = []
        for _, row in df.iterrows():
            exam_type = row['检查类别']
            hazards_str = str(row.get('岗位危害因素', ''))
            hazards = [h.strip() for h in re.split(r'[、,\s]+', hazards_str) if h.strip()]
            for h in hazards:
                t3_records.append({'体检类别': exam_type, '职业病危害因素名称': h})
        t3_df = pd.DataFrame(t3_records)
        output_sheets['表格3_个体结论统计表'] = t3_df.groupby(['体检类别', '职业病危害因素名称']).size().reset_index(name='应检人数')

    if task_info.get("gen_t4"):
        t4_grouped = df.groupby(['检查类别', '团体部门', 'worktype', '岗位危害因素']).size().reset_index(name='委托人数')
        t4_grouped.rename(columns={'检查类别': '体检类别', '团体部门': '车间', 'worktype': '工种', '岗位危害因素': '职业病危害因素名称'}, inplace=True)
        output_sheets['表格4_检查对象表'] = t4_grouped

    # 生成 AI 表格 2
    if task_info.get("gen_t2"):
        provider = task_info.get("provider", "智谱 AI (GLM-4-Flash - 完全免费)")
        model = task_info.get("model", "glm-4-flash")
        t2_data = []

        for i, row in df.iterrows():
            idx = i + 1
            name = row.get('姓名', '')
            conclusion_text = str(row.get('结论词', '')).strip()

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
                    ai_reply = call_ai_api(provider, model, messages, use_gbz=False)
                    final_advice = ai_reply.strip().replace('\n', '')
                except Exception as e:
                    final_advice = f"AI处理出错: {e}"

            t2_data.append({'编号': idx, '姓名': name, '主要阳性结果及医学建议': final_advice})

        output_sheets['表格2_阳性结果及建议'] = pd.DataFrame(t2_data)

    # 3. 把拼好的全套 Excel 上传保存到 Supabase 的 option_3/result 目录
    full_buffer = io.BytesIO()
    with pd.ExcelWriter(full_buffer, engine='openpyxl') as writer:
        for sheet_name, sheet_df in output_sheets.items():
            sheet_df.to_excel(writer, sheet_name=sheet_name, index=False)

    export_name = file_name.rsplit(".", 1)[0] + "_报告书全集.xlsx"
    cloud_storage.upload_bytes_to_supabase(full_buffer.getvalue(), export_name, folder="option_3/result")
    print(f"🎉 结果文件已成功生成并保存至云端目录: option_3/result/{export_name}")

    # 4. 更新任务状态为 completed（已完成）
    task_info["status"] = "completed"
    updated_bytes = json.dumps(task_info, ensure_ascii=False, indent=2).encode('utf-8')
    cloud_storage.upload_bytes_to_supabase(updated_bytes, file_name=f"task_{task_id}.json", folder="option_3/tasks")
    print(f"✅ 挂机任务【{task_id}】状态已更新为 completed！")

def main():
    print("🔍 [GitHub Actions 云端打工人] 开始巡逻扫描任务...")
    task_files = cloud_storage.list_supabase_files(folder="option_3/tasks")
    if not task_files:
        print("☕ 当前没有找到任何挂机任务文件。")
        return

    pending_count = 0
    for t_file in task_files:
        if not t_file["file_name"].endswith(".json"):
            continue

        task_bytes = cloud_storage.download_bytes_from_supabase(t_file["path"])
        if not task_bytes:
            continue

        try:
            task_info = json.loads(task_bytes.decode('utf-8'))
        except Exception:
            continue

        # 发现排队中的任务，立即在云端进行 AI 处理
        if task_info.get("status") == "pending":
            pending_count += 1
            process_single_task(task_info, t_file["path"])

    if pending_count == 0:
        print("✨ 所有任务均为已完成状态，无需处理。")

if __name__ == "__main__":
    main()
