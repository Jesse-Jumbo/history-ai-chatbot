@echo off
REM SAGE Conda 環境設置腳本
REM 使用方式: setup_conda.bat

echo ========================================
echo SAGE Conda 環境設置
echo ========================================

REM 檢查 conda 是否安裝
where conda >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [錯誤] 未找到 Conda，請先安裝 Anaconda 或 Miniconda
    echo 下載地址: https://docs.conda.io/en/latest/miniconda.html
    pause
    exit /b 1
)

echo.
echo [1/3] 創建 Conda 環境...
call conda env create -f environment.yml

if %ERRORLEVEL% NEQ 0 (
    echo [警告] 環境可能已存在，嘗試更新...
    call conda env update -f environment.yml --prune
)

echo.
echo [2/3] 啟動環境...
call conda activate sage

echo.
echo [3/3] 下載模型...
python scripts/download_models.py

echo.
echo ========================================
echo 設置完成！
echo.
echo 使用方式:
echo   conda activate sage
echo   python src/main.py --gpu
echo ========================================
pause
