#!/usr/bin/env python
"""
測試 SAGE API 連接
用於診斷後端與 SAGE API 的連接問題
"""
import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv
import httpx

# 載入環境變數
load_dotenv()

SAGE_API_URL = os.getenv("SAGE_API_URL", "http://localhost:8001")

async def test_connection():
    """測試 SAGE API 連接"""
    print("=" * 60)
    print("  SAGE API 連接測試")
    print("=" * 60)
    print()
    print(f"配置的 SAGE API URL: {SAGE_API_URL}")
    print()
    
    # 解析 URL
    from urllib.parse import urlparse
    parsed = urlparse(SAGE_API_URL)
    host = parsed.hostname
    port = parsed.port or 8001
    
    print(f"📍 主機: {host}")
    print(f"🔌 端口: {port}")
    print()
    
    # 測試 1: 基本網路連接（socket 測試）
    print("1. 測試基本網路連接（端口 {port}）...")
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)  # 5 秒超時
        result = sock.connect_ex((host, port))
        sock.close()
        if result == 0:
            print(f"   ✅ 端口 {port} 可訪問")
        else:
            print(f"   ❌ 端口 {port} 無法訪問（錯誤碼: {result}）")
            print()
            print("可能的原因：")
            print("  1. 網路連接問題（本地電腦無法到達遠端機器）")
            print("  2. 中間路由器或防火牆阻擋")
            print("  3. 遠端機器防火牆設定問題")
            print()
            print("解決方法：")
            print(f"  1. 測試基本網路連接：")
            print(f"     ping {host}")
            print(f"  2. 測試端口連接：")
            print(f"     telnet {host} {port}")
            print(f"     或")
            print(f"     nc -zv {host} {port}")
            print(f"  3. 確認遠端機器防火牆允許來自你的 IP：")
            print(f"     在遠端機器上：sudo ufw allow from <你的IP> to any port {port}")
            print(f"  4. 檢查是否在同一網路：")
            print(f"     如果不在同一網路，可能需要 VPN 或端口轉發")
            return False
    except socket.gaierror:
        print(f"   ❌ 無法解析主機名 {host}")
        print("   請確認 IP 地址或主機名是否正確")
        return False
    except socket.timeout:
        print(f"   ❌ 連接超時（5 秒）")
        print("   網路連接可能很慢或不穩定")
        print(f"   嘗試：ping {host} 檢查基本連接")
        return False
    except Exception as e:
        print(f"   ⚠️  網路測試失敗: {type(e).__name__}: {str(e)}")
    print()
    
    # 測試 2: HTTP 連接
    print("2. 測試 HTTP 連接（超時 30 秒）...")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:  # 增加到 30 秒
            try:
                response = await client.get(f"{SAGE_API_URL}/status")
                print(f"   ✅ HTTP 連接成功！狀態碼: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print()
                    print("   📊 SAGE API 狀態：")
                    print(f"      狀態: {data.get('status', 'unknown')}")
                    print(f"      GPU 可用: {'是' if data.get('gpu_available') else '否'}")
                    if data.get('gpu_name'):
                        print(f"      GPU 名稱: {data.get('gpu_name')}")
                    print(f"      Mock 模式: {'是' if data.get('mock_mode') else '否'}")
                    print(f"      攝影機可用: {'是' if data.get('camera_available') else '否'}")
                    print()
                    print("✅ SAGE API 連接正常，可以正常使用！")
                    return True
                else:
                    print(f"   ⚠️  狀態碼異常: {response.status_code}")
                    print(f"   回應內容: {response.text[:200]}")
                    return False
                    
            except httpx.ConnectError as e:
                print(f"   ❌ HTTP 連接失敗: {str(e)}")
                print()
                print("可能的原因：")
                print("  1. SAGE API 服務未啟動")
                print("  2. SAGE API 未綁定到 0.0.0.0（只綁定到 127.0.0.1）")
                print("  3. 防火牆阻擋連接")
                print()
                print("解決方法：")
                print(f"  在遠端機器 ({host}) 上：")
                print(f"    1. 確認服務運行：")
                print(f"       sudo systemctl status sage-api")
                print(f"       或")
                print(f"       ps aux | grep run_server")
                print(f"    2. 確認綁定地址（應使用 0.0.0.0）：")
                print(f"       netstat -tlnp | grep {port}")
                print(f"       應該看到: 0.0.0.0:{port} 或 :::{port}")
                print(f"    3. 檢查防火牆：")
                print(f"       sudo ufw status")
                print(f"       如果未啟用，執行：sudo ufw enable")
                print(f"       然後：sudo ufw allow {port}/tcp")
                print(f"    4. 測試本地連接（在遠端機器上）：")
                print(f"       curl http://localhost:{port}/status")
                return False
                
            except httpx.TimeoutException:
                print("   ❌ 連接超時（超過 15 秒）")
                print()
                print("可能的原因：")
                print("  1. SAGE API 服務正在啟動中（首次啟動需要載入模型）")
                print("  2. 網路連接不穩定")
                print("  3. SAGE API 服務無響應")
                print()
                print("解決方法：")
                print(f"  1. 在遠端機器上檢查服務狀態：")
                print(f"     sudo systemctl status sage-api")
                print(f"     或查看日誌：")
                print(f"     sudo journalctl -u sage-api -f")
                print(f"  2. 嘗試在遠端機器本地測試：")
                print(f"     curl http://localhost:{port}/status")
                print(f"  3. 如果服務正在啟動，等待 1-2 分鐘後再試")
                print(f"  4. 檢查網路連接：")
                print(f"     ping {host}")
                return False
                
            except Exception as e:
                print(f"   ❌ 發生錯誤: {str(e)}")
                print(f"   錯誤類型: {type(e).__name__}")
                return False
                
    except Exception as e:
        print(f"❌ 測試失敗: {str(e)}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_connection())
    sys.exit(0 if success else 1)

