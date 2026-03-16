```aiignore
smart_dashboard/
├── main.py            
├── config.py          
├── requirements.txt   
│
├── ui/                
│   ├── __init__.py
│   ├── dashboard_window.py
│   ├── swipe_container.py  
│   │
│   ├── panels/     
│   │   ├── __init__.py
│   │   └── clock_panel.py 
│   │
│   └── tabs/         
│       ├── __init__.py
│       ├── performance_tab.py 
│       └── spotify_tab.py   
│
├── backend/            
│   ├── __init__.py
│   ├── hardware_collector.py 
│   └── spotify_client.py     
│
├── assets/           
│   ├── styles/       
│   ├── fonts/        
│   └── icons/        
│
└── docs/            
    ├── report_assets/   
    └── time_log.txt     
```