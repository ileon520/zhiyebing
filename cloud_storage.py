import os
import streamlit as st
import io
import urllib.parse
from datetime import datetime, timedelta

try:
    from supabase import create_client
except ImportError:
    pass

def get_storage_client():
    """连接 Supabase 云端存储"""
    # 🌟 直接把姐姐的云端参数写在这里，开箱即用！
    url = "https://aylyfexlomakrcwwqqml.supabase.co"
    key = "sb_publishable_Sf-1bHP7Xw74fs39mwknKw_Z4ynFD7g"
    
    try:
        # 如果后台配置了 secrets 优先用 secrets，没配就自动用上面的默认值
        if "SUPABASE_URL" in st.secrets and "SUPABASE_KEY" in st.secrets:
            url = st.secrets["SUPABASE_URL"]
            key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception:
        pass
        
    try:
        return create_client(url, key)
    except Exception:
        return None

def upload_bytes_to_supabase(
    file_bytes, file_name, bucket_name="zhiyebing", folder="option_1"
):  # 👈 【改动1】：末尾加上了 , folder="option_1"
  """将字节流（如 Excel 或 TXT）上传到 Supabase 并返回公开下载链接"""
  client = get_storage_client()
  if client is not None:
    try:
      import re
      from datetime import datetime

      # 🌟 1. 尝试将中文文件名转为拼音
      name_part, ext_part = os.path.splitext(file_name)
      try:
          import pypinyin
          name_part = ''.join(pypinyin.lazy_pinyin(name_part))
      except Exception:
          pass

      # 🌟 2. 清理特殊字符，并加上“时分秒”时间戳，彻底防止云端同名覆盖！
      safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', name_part)
      time_str = datetime.now().strftime("%H%M%S") # 获取当前时分秒
      
      safe_file_name = (
          f"{safe_name}_{time_str}{ext_part}" if safe_name else f"file_{time_str}{ext_part}"
      )
      full_path = f"{folder}/{safe_file_name}"

      client.storage.from_(bucket_name).upload(
          path=full_path,  # 👈 【改动2】：原本的 path=file_name 改成了 path=full_path
          file=file_bytes,
          file_options={"upsert": "true"},
      )
      # 👇 注意这里必须用 full_path，才能获取到正确的云端文件
      public_url = client.storage.from_(bucket_name).get_public_url(full_path)
      # 👇 强制浏览器直接下载，并恢复姐姐原本好看的中文文件名
      download_url = f"{public_url}?download={urllib.parse.quote(file_name)}"
      return download_url
    except Exception as e:
      st.error(f"上传到 Supabase 失败: {e}")
      return None
  else:
    # 降级本地保存
    local_dir = os.path.join(
        "local_data", folder
    )  # 👈 【改动4】：本地路径也按文件夹隔离
    os.makedirs(local_dir, exist_ok=True)
    local_path = os.path.join(local_dir, file_name)
    with open(local_path, "wb") as f:
      f.write(file_bytes)
    return local_path

def list_supabase_files(bucket_name="zhiyebing", folder="option_1"):
    """获取指定选项文件夹下的所有云端历史文件列表"""
    client = get_storage_client()
    if client is None:
        return []
    try:
        res = client.storage.from_(bucket_name).list(folder)
        files_info = []
        for item in res:
            if item.get("name") and item.get("id") is not None:
                raw_name = item["name"]
                unquoted_name = urllib.parse.unquote(raw_name)
                
                # 🌟 处理北京时间 (+8小时)
                created_at_utc = item.get("created_at", "")[:19]
                try:
                    utc_dt = datetime.strptime(created_at_utc, "%Y-%m-%dT%H:%M:%S")
                    bj_dt = utc_dt + timedelta(hours=8)
                    created_at = bj_dt.strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    created_at = created_at_utc.replace("T", " ")
                
                # 🌟 补全缺失的 download_url，彻底解决 KeyError 报错！
                public_url = client.storage.from_(bucket_name).get_public_url(f"{folder}/{raw_name}")
                download_url = f"{public_url}?download={urllib.parse.quote(unquoted_name)}"
                
                files_info.append({
                    "display_name": f"{unquoted_name} (上传时间: {created_at})",
                    "file_name": unquoted_name,
                    "path": f"{folder}/{raw_name}",
                    "download_url": download_url  # 👈 关键修复位置
                })
        return files_info
    except Exception as e:
        st.error(f"读取云端文件列表失败: {e}")
        return []

def download_bytes_from_supabase(file_path, bucket_name="zhiyebing"):
    """从 Supabase 下载文件并返回 Bytes 字节流"""
    client = get_storage_client()
    if client is not None:
        try:
            data = client.storage.from_(bucket_name).download(file_path)
            return data
        except Exception as e:
            st.error(f"下载云端文件失败: {e}")
            return None
    return None
def delete_supabase_file(file_path, bucket_name="zhiyebing"):
    """删除云端指定文件"""
    client = get_storage_client()
    if client is not None:
        try:
            client.storage.from_(bucket_name).remove([file_path])
            return True
        except Exception as e:
            st.error(f"删除云端文件失败: {e}")
            return False
    return False