# SAGE - Self-Aging Generative Experience

基於 [FADING (Face Aging via Diffusion-based Editing)](https://github.com/gh-BumsooKim/FADING_stable) 的人臉變老系統

## 專案概述

SAGE 讓使用者可以：
1. 透過攝影機拍攝自己的照片
2. 使用 AI 擴散模型將照片處理成不同年齡的樣貌

## 技術架構

```
[攝影機] ──> [OpenCV 拍照] ──> [FADING 擴散模型] ──> [保存結果]
```

### FADING 模型架構

FADING 使用 **Stable Diffusion** 搭配專門的年齡編輯技術：

- **Null-text Inversion**: 將真實照片反演回擴散模型的 latent space
- **Prompt-to-Prompt Editing**: 透過文字提示詞控制年齡變化
- **Cross-Attention Replacement**: 精準控制年齡相關特徵的轉換

核心流程：
1. 輸入照片經過 null-text 反演得到 latent code
2. 使用原始年齡提示詞 (如 "photo of 25 year old man")
3. 替換為目標年齡提示詞 (如 "photo of 75 year old man")
4. 透過 prompt-to-prompt 技術生成目標年齡的照片

## 環境需求

- Python 3.10+
- CUDA 11.8+ (推薦 CUDA 12.x)
- NVIDIA GPU (建議 8GB+ VRAM)
- 攝影機

## 快速開始

### 方法一：使用 Conda（推薦）

```bash
# 創建環境
conda env create -f environment.yml

# 啟動環境
conda activate sage

# 下載模型
python scripts/download_models.py

# 運行
python src/main.py --gpu
```

或直接執行設置腳本：
```bash
setup_conda.bat
```

### 方法二：使用 pip

```bash
# 創建虛擬環境
python -m venv venv
venv\Scripts\activate

# 安裝依賴
pip install -r requirements.txt

# 安裝 PyTorch（選擇對應 CUDA 版本）

# CUDA 11.8:
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# CUDA 12.1:
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# CUDA 12.4 (RTX 40 系列):
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124

# 下載模型
python scripts/download_models.py
```

## 使用方法

### 命令列介面 (CLI)

```bash
# 基本使用：拍照並變老到 75 歲
python src/main.py --gpu

# 處理現有照片
python src/main.py -i photo.jpg --gpu

# 指定目標年齡
python src/main.py --gpu -a 40

# 指定原始年齡和性別（提高準確度）
python src/main.py -i photo.jpg --gpu -a 60 --initial-age 30 --gender female

# 處理多個年齡（10, 20, 40, 60, 80 歲）
python src/aging.py photo.jpg --multi-age --initial-age 25 --gender male

# 使用 Mock 模式（不需 GPU，開發測試用）
python src/main.py --mock
```

### 命令列參數

| 參數 | 說明 | 預設值 |
|------|------|--------|
| `-i, --input` | 輸入影像路徑 | 無（使用攝影機） |
| `-a, --age` | 目標年齡 | 75 |
| `--initial-age` | 估計的原始年齡 | 25 |
| `--gender` | 性別 (male/female) | male |
| `--gpu` | 使用 GPU 模式 | False |
| `--mock` | 使用 Mock 模式 | False |
| `--multi-age` | 處理多個年齡 | False |

### Python API

```python
from src.aging import age_photo, age_photo_fading, FADINGProcessor

# 方法一：快速變老
result = age_photo(
    "photo.jpg",
    target_age=60,
    initial_age=25,
    gender="male"
)
print(f"結果: {result}")

# 方法二：處理多個年齡
results = age_photo_fading(
    "photo.jpg",
    target_ages=[20, 40, 60, 80],
    initial_age=25,
    gender="female"
)
for r in results:
    print(f"結果: {r}")

# 方法三：使用處理器（更多控制）
processor = FADINGProcessor()
result = processor.process(
    "photo.jpg",
    target_age=50,
    initial_age=30,
    gender="male",
    output_filename="my_result.png"
)
```

## 專案結構

```
SAGE/
├── src/
│   ├── main.py              # 主程式入口
│   ├── camera.py            # 攝影機模組
│   ├── aging.py             # 人臉變老處理 (FADING)
│   ├── api.py               # FastAPI 伺服器
│   ├── utils.py             # 工具函數
│   └── fading/              # FADING 核心程式碼
│       ├── age_editing.py   # 年齡編輯推理
│       ├── null_inversion.py # Null-text 反演
│       ├── p2p.py           # Prompt-to-Prompt
│       └── FADING_util/     # 工具函數
├── models/                   # 模型目錄（.gitignore）
│   └── finetune_double_prompt_150_random/  # FADING 預訓練模型
├── assets/
│   ├── captured/            # 拍攝的照片
│   └── aged/                # 變老後的照片
├── config/
│   └── settings.py          # 設定檔
├── scripts/
│   └── download_models.py   # 模型下載工具
├── tests/                   # 測試
├── requirements.txt
├── environment.yml
└── README.md
```

## 模型檔案

| 模型 | 說明 | 大小 |
|------|------|------|
| `finetune_double_prompt_150_random/` | FADING 預訓練擴散模型 | ~4.57 GB |
| `face_landmarker.task` | MediaPipe 人臉特徵點 | ~5 MB |

### 手動下載模型

如果自動下載失敗，可以手動下載：

```bash
# 安裝 gdown
pip install gdown

# 下載 FADING 模型
cd models
gdown 1galwrcHq1HoZNfOI4jdJJqVs5ehB_dvO

# 解壓縮
unzip finetune_double_prompt_150_random.zip
```

## 環境變數

可在 `.env` 檔案中設定：

```env
# 引擎設定
SAGE_AGING_ENGINE=fading     # 老化引擎（fading/mock）

# 模式設定
SAGE_MOCK_MODE=false          # 強制 Mock 模式
SAGE_AUTO_MOCK=false          # 自動 Mock 模式

# 年齡設定
SAGE_TARGET_AGE=75            # 預設目標年齡

# 攝影機設定
SAGE_CAMERA_INDEX=0           # 攝影機索引
SAGE_CAMERA_WIDTH=1280        # 解析度寬度
SAGE_CAMERA_HEIGHT=720        # 解析度高度

# API 伺服器
SAGE_API_HOST=0.0.0.0         # API 主機
SAGE_API_PORT=8000            # API 埠號
```

## FADING 參數調整

在 `config/settings.py` 中可以調整 FADING 的行為：

```python
FADING_CONFIG = {
    # 擴散模型步數（越高品質越好，但更慢）
    "num_ddim_steps": 50,

    # CFG 引導強度（控制生成圖片與文字的相關性）
    "guidance_scale": 7.5,

    # 影像大小
    "image_size": 512,

    # 交叉注意力替換比例（控制年齡特徵轉換強度）
    "cross_replace_steps": 0.8,

    # 自注意力替換比例（控制身份保持程度）
    "self_replace_steps": 0.5,

    # 預設目標年齡列表
    "default_target_ages": [10, 20, 40, 60, 80],
}
```

## API 伺服器

啟動 API 伺服器：

```bash
python src/api.py
```

API 文件：http://localhost:8000/docs

### API 端點

- `POST /capture` - 拍照
- `POST /age` - 變老處理
- `POST /capture-and-age` - 拍照並變老
- `GET /status` - 系統狀態

## 技術參考

本專案基於以下研究：

- **FADING**: [FADING: Face Aging via Diffusion-based Editing](https://github.com/gh-BumsooKim/FADING_stable)
- **Null-text Inversion**: [Null-text Inversion for Editing Real Images using Guided Diffusion Models](https://arxiv.org/abs/2211.09794)
- **Prompt-to-Prompt**: [Prompt-to-Prompt Image Editing with Cross Attention Control](https://arxiv.org/abs/2208.01626)
- **Stable Diffusion**: [High-Resolution Image Synthesis with Latent Diffusion Models](https://arxiv.org/abs/2112.10752)

## 致謝

- [gh-BumsooKim/FADING_stable](https://github.com/gh-BumsooKim/FADING_stable) - FADING 原始實現
- [google-research/prompt-to-prompt](https://github.com/google-research/prompt-to-prompt) - P2P 技術
- [Stability AI](https://stability.ai/) - Stable Diffusion 基礎模型

## License

MIT License
