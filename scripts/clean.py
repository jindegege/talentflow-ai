import sys
import os
import shutil

# --- 关键修复：添加项目根目录到系统路径 ---
# 获取当前脚本所在的目录 (scripts)
current_dir = os.path.dirname(os.path.abspath(__file__))
# 获取项目根目录 (scripts 的上一级)
parent_dir = os.path.dirname(current_dir)
# 将根目录插入到系统路径的最前面
sys.path.insert(0, parent_dir)
# -----------------------------------------

try:
    # 现在应该能正常导入了
    from app.core.config import settings
    
    # 获取向量库路径 (根据你的 settings 定义，通常是 CHROMA_DB_PATH 或类似)
    # 假设你在 settings.py 里定义的是 CHROMA_DIR
    db_path = settings.VECTOR_DB_PATH
    
    print(f"🔍 正在检查路径: {db_path}")

    if os.path.exists(db_path):
        # 确认删除
        confirm = input(f"⚠️ 警告: 即将删除 {db_path} 及其所有内容。确定吗? (y/N): ")
        if confirm.lower() == 'y':
            shutil.rmtree(db_path)
            print(f"✅ 成功删除 {db_path}。请重新运行 sync 脚本。")
        else:
            print("❌ 操作已取消。")
    else:
        print(f"ℹ️ 路径 {db_path} 不存在，可能已经删除过了。")

except Exception as e:
    print(f"❌ 发生错误: {e}")
    print("请检查 settings.py 中的路径配置是否正确。")