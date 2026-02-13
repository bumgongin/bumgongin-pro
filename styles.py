# styles.py
# 범공인 Pro v24 Enterprise - Style Definition Module (v24.22.3)
# Feature: 3-Layer Slim Card & Pagination UI

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
        }
        
        .main .block-container {
            pointer-events: auto !important;
            padding-top: 1rem !important;
            padding-bottom: 8rem !important; /* 하단 액션바 공간 확보 */
            max-width: 100% !important;
            height: 100% !important;
            overflow-y: auto !important;
            -webkit-overflow-scrolling: touch !important;
            overscroll-behavior: contain !important;
        }

        /* --------------------------------------------------------------------- */
        /* [SLIM CARD] 3-Layer Design                                            */
        /* --------------------------------------------------------------------- */
        .listing-card {
            background-color: #ffffff;
            border-bottom: 1px solid #f0f0f0; /* 구분선만 남김 */
            padding: 10px 4px; /* 상하 패딩 축소 */
            margin-bottom: 0px;
            transition: background-color 0.1s;
            pointer-events: auto !important;
        }
        
        .listing-card:active {
            background-color: #f5f5f5;
        }
        
        /* 1단: 구분 + 가격 (강조) */
        .card-row-1 {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 4px;
        }
        .card-tag {
            font-size: 0.8rem;
            font-weight: 700;
            color: #1565c0;
            background-color: #e3f2fd;
            padding: 2px 6px;
            border-radius: 4px;
            white-space: nowrap;
        }
        .card-price {
            font-size: 1.05rem;
            font-weight: 800;
            color: #d32f2f;
        }
        
        /* 2단: 주소 + 층수 (기본) */
        .card-row-2 {
            font-size: 0.9rem;
            color: #212121;
            font-weight: 500;
            margin-bottom: 2px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        /* 3단: 상세 스펙 (회색) */
        .card-row-3 {
            font-size: 0.8rem;
            color: #757575;
            display: flex;
            gap: 8px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        /* --------------------------------------------------------------------- */
        /* [LIST MODE] Data Editor                                               */
        /* --------------------------------------------------------------------- */
        div[data-testid="stDataEditor"] {
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            background-color: #ffffff;
            touch-action: pan-y !important;
            -webkit-user-drag: none !important;
            pointer-events: auto !important;
        }

        div[data-testid="stDataEditor"] > div {
            overflow-y: auto !important; 
            overscroll-behavior: contain !important;
            -webkit-overflow-scrolling: touch !important; 
            scrollbar-width: thin;
        }
        
        div[data-testid="stDataEditor"] * {
            user-select: none !important;
            -webkit-user-select: none !important;
        }

        /* --------------------------------------------------------------------- */
        /* [UI ELEMENTS]                                                         */
        /* --------------------------------------------------------------------- */
        .stButton button { 
            min-height: 48px !important; 
            font-size: 15px !important; 
            font-weight: 600 !important; 
            width: 100%;
            border-radius: 6px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
            pointer-events: auto !important; 
        }
        
        input[type=number], input[type=text] { 
            min-height: 45px !important; 
            font-size: 16px !important; 
            pointer-events: auto !important; 
        }
        
        div[data-baseweb="select"] > div {
            min-height: 45px !important;
            pointer-events: auto !important; 
        }
        
        /* Pagination Controls */
        .pagination-container {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 20px;
            margin-top: 10px;
            margin-bottom: 20px;
        }
        
        /* Sidebar */
        section[data-testid="stSidebar"] {
            overflow-y: auto !important; 
            pointer-events: auto !important; 
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
        
        /* Action Buttons */
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
