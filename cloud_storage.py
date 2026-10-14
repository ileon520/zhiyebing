import os
import streamlit as st
import io

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

def upload_bytes_to_supabase(file_bytes, file_name, bucket_name="zhiyebing"):
    """将字节流（如 Excel 或 TXT）上传到 Supabase 并返回公开下载链接"""
    client = get_storage_client()
    if client is not None:
        try:
            client.storage.from_(bucket_name).upload(
                path=file_name,
                file=file_bytes,
                file_options={"upsert": "true"}
            )
            public_url = client.storage.from_(bucket_name).get_public_url(file_name)
            return public_url
        except Exception as e:
            st.error(f"上传到 Supabase 失败: {e}")
            return None
    else:
        # 降级本地保存
        local_dir = "local_data"
        os.makedirs(local_dir, exist_ok=True)
        local_path = os.path.join(local_dir, file_name)
        with open(local_path, "wb") as f:
            f.write(file_bytes)
        return local_path