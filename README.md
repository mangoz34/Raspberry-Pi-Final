```aiignore
smart_dashboard/
├── main.py                 # 程式入口，負責實例化 DashboardWindow 與啟動事件迴圈
├── config.py               # 存放全域設定（如 1920x480 解析度、UI 更新頻率設定）
├── requirements.txt        # 記錄 Python 依賴套件（如 PyQt6, psutil 等）
│
├── ui/                     # 介面顯示層 (Frontend)
│   ├── __init__.py
│   ├── dashboard_window.py # 實作 DashboardWindow，精確處理左右佈局切割
│   ├── swipe_container.py  # 實作 SwipeContainer，封裝 QPropertyAnimation 翻頁特效
│   │
│   ├── panels/             # 常駐型顯示面板
│   │   ├── __init__.py
│   │   └── clock_panel.py  # 左側專用的 ClockPanel，獨立管理時間刷新
│   │
│   └── tabs/               # 右側可滑動的分頁元件
│       ├── __init__.py
│       ├── performance_tab.py # 實作 PerformanceTab，視覺化呈現硬體數據
│       └── spotify_tab.py     # 實作 SpotifyTab，處理專輯封面與播放控制 UI
│
├── backend/                # 數據採集與服務層 (Backend)
│   ├── __init__.py
│   ├── hardware_collector.py  # 實作 HardwareCollector，封裝 Linux 檔案系統讀取邏輯
│   └── spotify_client.py      # 實作 SpotifyClient，處理 API 認證與網路請求
│
├── assets/                 # 靜態資源目錄
│   ├── styles/             # 存放 QSS (類似 CSS) 檔案，定義現代化儀表板的外觀
│   ├── fonts/              # 自訂字型檔案
│   └── icons/              # 介面使用的圖示
│
└── docs/                   # 作業提交與報告準備
    ├── report_assets/      # 存放證明系統運作的影像、螢幕截圖和影片 
    └── time_log.txt        # 專門記錄各開發階段花費的時間
```