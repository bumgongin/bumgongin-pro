# styles.py
# 범공인 Pro v24 Enterprise - Style Definition Module (v24.22.6)
# Fix: Adaptive Layout & Optimized Spacing

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
            padding-bottom: 8rem !important;
            max-width: 100% !important;
            height: 100% !important;
            overflow-y: auto !important;
            -webkit-overflow-scrolling: touch !important;
            overscroll-behavior: contain !important;
        }

        /* --------------------------------------------------------------------- */
        /* [CARD UI] Optimized Layout                                            */
        /* --------------------------------------------------------------------- */
        .listing-card {
            background-color: #ffffff;
            border-bottom: 1px solid #f0f0f0;
            padding: 10px 4px;
            margin-bottom: 0px;
            transition: background-color 0.1s;
            pointer-events: auto !important;
            display: flex;
            flex-direction: column;
            gap: 2px;
        }
        
        .listing-card:active { background-color: #f5f5f5; }
        
        .card-row-1 { display: flex; align-items: center; gap: 6px; margin-bottom: 2px; }
        .card-tag {
            font-size: 0.75rem; font-weight: 700; color: #1565c0;
            background-color: #e3f2fd; padding: 2px 4px; border-radius: 4px;
            white-space: nowrap;
        }
        .card-price { font-size: 1.0rem; font-weight: 800; color: #d32f2f; white-space: nowrap; }
        
        .card-row-2 { 
            font-size: 0.85rem; color: #212121; font-weight: 500; 
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }
        
        .card-row-3 { font-size: 0.8rem; color: #757575; gap: 8px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

        @media (min-width: 1024px) {
            .listing-card {
                flex-direction: row; 
                justify-content: space-between;
                align-items: center;
                padding: 8px 16px;
            }
            .card-row-1, .card-row-2, .card-row-3 { margin-bottom: 0; flex: 1; }
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
        /* [UI ELEMENTS] Buttons & Checkboxes                                    */
        /* --------------------------------------------------------------------- */
        .stButton button { 
            min-height: 44px !important; 
            font-size: 14px !important;
            font-weight: 600 !important; 
            width: 100%;
            border-radius: 6px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
            pointer-events: auto !important; 
            white-space: nowrap !important;
            padding: 0 4px !important;
        }
        
        /* 체크박스 정렬 보정 */
        div[data-testid="stCheckbox"] {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100%;
            padding-top: 12px; 
            min-height: 44px;
        }
        div[data-testid="stCheckbox"] label {
            margin-bottom: 0px !important;
        }

        /* 사이드바 */
        section[data-testid="stSidebar"] {
            overflow-y: auto !important; 
            pointer-events: auto !important; 
            overscroll-behavior: contain !important;
            touch-action: pan-y !important;
        }
        
        /* 버튼 색상 */
        div[data-testid="stHorizontalBlock"] button[kind="secondary"] { 
            border: 1px solid #d0d0d0; background-color: #f8f9fa; color: #333; 
        }
        div[data-testid="stHorizontalBlock"] button[kind="primary"] { 
            background-color: #ff4b4b; color: white; border: none; 
        }

        /* --------------------------------------------------------------------- */
        /* [MOBILE ADAPTIVE] Flexible Row Layout                                 */
        /* --------------------------------------------------------------------- */
        @media (max-width: 768px) { 
            .stDataEditor { font-size: 13px !important; }
            h1 { font-size: 18px !important; margin: 0 !important; padding: 0 !important; }
            div[data-testid="stToast"] { bottom: 20px; left: 10px; right: 10px; width: auto; }
            
            /* 버튼 그룹 자연스러운 줄바꿈 허용 */
            div[data-testid="stHorizontalBlock"] {
                flex-wrap: wrap !important;
                gap: 6px !important;
            }
            
            /* 컬럼 최소 너비 보장 */
            div[data-testid="column"] {
                min-width: 30% !important;
                flex: 1 !important;
            }
        }
        </style>
    """, unsafe_allow_html=True)
