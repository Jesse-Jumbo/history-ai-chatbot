"""
初始化資料庫腳本
執行此腳本以建立資料庫表格和範例資料
"""
from database import init_db

if __name__ == "__main__":
    print("正在初始化資料庫...")
    init_db()
    print("資料庫初始化完成！")

