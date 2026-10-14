import os
import streamlit as st
import io
import urllib.parse

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

      # 安全清理文件名：只保留字母、数字、下划线、横杠和点，避免出现 % 导致 Supabase 报 InvalidKey
      name_part, ext_part = os.path.splitext(file_name)
      safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', name_part)
      safe_file_name = (
          f"{safe_name}{ext_part}" if safe_name else f"file{ext_part}"
      )
      full_path = f"{folder}/{safe_file_name}"

      client.storage.from_(bucket_name).upload(
          path=full_path,  # 👈 【改动2】：原本的 path=file_name 改成了 path=full_path
          file=file_bytes,
          file_options={"upsert": "true"},
      )
      public_url = client.storage.from_(bucket_name).get_public_url(
          full_path
      )  # 👈 【改动3】：原本的 file_name 改成了 full_path
      return public_url
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
                created_at = item.get("created_at", "")[:19].replace("T", " ")
                files_info.append({
                    "display_name": f"{unquoted_name} (上传时间: {created_at})",
                    "file_name": unquoted_name,
                    "path": f"{folder}/{raw_name}"
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