# styles.py
# 범공인 Pro v24 Enterprise - Style Definition Module (v24.22.2)
# Final Fix: Touch Capability Restored

import streamlit as st

def apply_custom_css():
    st.markdown("""
        <style>
        /* --------------------------------------------------------------------- */
        /* [CORE] Dynamic Viewport Locking System (100dvh)                       */
        /* --------------------------------------------------------------------- */
        
        html, body {
            height: 100dvh !important;
            overflow: hidden !important;
            overscroll-behavior: none !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        
        .stAppViewContainer {
            height: 100dvh !important;
            overflow: hidden !important;
            touch-action: none;
            /* pointer-events: none; 삭제됨 -> 터치 정상화 */
        }
        
        /* --------------------------------------------------------------------- */
        /* [CONTENT AREA] Scrollable Zone                                        */
        /* --------------------------------------------------------------------- */
        
        .main .block-container {
            padding-top: 1rem !important;
            padding-bottom: 5rem !important; /* 하단 여백 충분히 확보 */
            max-width: 100% !important;
            height: 100% !important;
            overflow-y: auto !important;
            -webkit-overflow-scrolling: touch !important;
            overscroll-behavior: contain !important;
        }

        /* --------------------------------------------------------------------- */
        /* [LIST MODE] Data Editor Style                                         */
        /* --------------------------------------------------------------------- */
        
        div[data-testid="stDataEditor"] {
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            background-color: #ffffff;
            touch-action: pan-y !important;
            -webkit-user-drag: none !important;
        }

        div[data-testid="stDataEditor"] > div {
            overflow-y: auto !important; 
            overscroll-behavior: contain !important;
            -webkit-overflow-scrolling: touch !important; 
            scrollbar-width: thin;
        }

        /* --------------------------------------------------------------------- */
        /* [CARD MODE] Mobile Card UI                                            */
        /* --------------------------------------------------------------------- */
        
        .listing-card {
            background-color: #ffffff;
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 12px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            border: 1px solid #f0f0f0;
            transition: transform 0.1s ease;
        }
        
        .listing-card:active {
            background-color: #f9f9f9;
        }
        
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }
        
        .card-tag {
            background-color: #e3f2fd;
            color: #1565c0;
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 0.8rem;
            font-weight: 700;
        }
        
        .card-price {
            font-size: 1.1rem;
            font-weight: 800;
            color: #d32f2f;
        }
        
        .card-info {
            font-size: 0.95rem;
            color: #424242;
            margin-bottom: 4px;
            line-height: 1.4;
        }
        
        .card-meta {
            font-size: 0.85rem;
            color: #757575;
            margin-top: 8px;
            display: flex;
            gap: 10px;
        }

        /* --------------------------------------------------------------------- */
        /* [COMMON] Interactive Elements                                         */
        /* --------------------------------------------------------------------- */
        
        div[data-testid="stDataEditor"] * {
            user-select: none !important;
            -webkit-user-select: none !important;
        }

        .stButton button { 
            min-height: 48px !important; 
            font-size: 15px !important; 
            font-weight: 600 !important; 
            width: 100%;
            border-radius: 6px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        }
        
        input[type=number], input[type=text] { 
            min-height: 45px !important; 
            font-size: 16px !important; 
        }
        
        div[data-baseweb="select"] > div {
            min-height: 45px !important;
        }
        
        section[data-testid="stSidebar"] {
            overflow-y: auto !important; 
            overscroll-behavior: contain !important;
            touch-action: pan-y !important;
        }
        
        section[data-testid="stSidebar"] .block-container {
            padding-top: 2rem;
            padding-bottom: 5rem;
        }
        
        [data-testid="stSidebar"] div[data-testid="stVerticalBlock"] {
            gap: 1rem;
        }
        
        .search-label {
            font-size: 1.2rem;
            cursor: pointer;
            margin-left: 5px;
        }
        
        div[data-testid="stHorizontalBlock"] button[kind="secondary"] { 
            border: 1px solid #d0d0d0; 
            background-color: #f8f9fa; 
            color: #333; 
        }
        div[data-testid="stHorizontalBlock"] button[kind="primary"] { 
            background-color: #ff4b4b; 
            color: white; 
            border: none; 
        }

        @media (max-width: 768px) { 
            .stDataEditor { font-size: 13px !important; }
            h1 { font-size: 18px !important; margin: 0 !important; padding: 0 !important; }
            div[data-testid="column"] { margin-bottom: 5px; }
            div.stSelectbox { margin-bottom: 5px; }
            div[data-testid="stToast"] { bottom: 20px; left: 10px; right: 10px; width: auto; }
        }
        </style>
    """, unsafe_allow_html=True)
