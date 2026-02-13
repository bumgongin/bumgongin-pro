# styles.py
# 범공인 Pro v24 Enterprise - Style Definition Module (v24.21.14)
# Final Fix: Touch Restoration & Multi-Layer Scroll Lock

import streamlit as st

def apply_custom_css():
    st.markdown("""
        <style>
        /* --------------------------------------------------------------------- */
        /* [CORE] Multi-Layer Viewport Locking System (100dvh)                   */
        /* --------------------------------------------------------------------- */
        
        /* 1. 최상위 레벨 고정 */
        html, body {
            height: 100dvh !important;
            overflow: hidden !important;
            overscroll-behavior: none !important;
            margin: 0 !important;
            padding: 0 !important;
            /* pointer-events: none 삭제됨 -> 터치 부활 */
        }
        
        /* 2. 앱 컨테이너 2차 고정 (중첩 차단) */
        .stAppViewContainer {
            height: 100dvh !important;
            overflow: hidden !important;
            overscroll-behavior: contain !important;
            /* touch-action: none 삭제됨 -> 내부 스크롤 허용 */
        }
        
        /* 3. 메인 컨텐츠 영역 (실제 터치 공간) */
        .main .block-container {
            padding-top: 1rem !important;
            padding-bottom: 2rem !important;
            max-width: 100% !important;
            height: 100% !important;
            overflow-y: auto !important; /* 메인 스크롤만 허용 */
            -webkit-overflow-scrolling: touch !important;
            overscroll-behavior: contain !important; /* 3차 차단 */
        }

        /* 4. 데이터 에디터 컨테이너 (스크롤 감옥) */
        div[data-testid="stDataEditor"] {
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            background-color: #ffffff;
            /* 수직 스크롤은 허용하되, 부모로 전파 차단 */
            touch-action: pan-y !important; 
            overscroll-behavior: contain !important; /* 4차 차단 */
            -webkit-user-drag: none !important;
        }

        /* 5. 리스트 내부 스크롤바 제어 */
        div[data-testid="stDataEditor"] > div {
            overflow-y: auto !important; 
            overscroll-behavior: contain !important;
            -webkit-overflow-scrolling: touch !important; 
            scrollbar-width: thin;
        }
        
        /* 스크롤바 디자인 */
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: #f1f1f1; border-radius: 3px; }
        ::-webkit-scrollbar-thumb { background: #bbb; border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: #888; }

        /* --------------------------------------------------------------------- */
        /* [TOUCH OPTIMIZATION] Interaction Lock                                 */
        /* --------------------------------------------------------------------- */
        
        div[data-testid="stDataEditor"] * {
            user-select: none !important;
            -webkit-user-select: none !important;
        }

        /* 버튼 스타일 */
        .stButton button { 
            min-height: 48px !important; 
            font-size: 15px !important; 
            font-weight: 600 !important; 
            width: 100%;
            border-radius: 6px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        }
        .stButton button:active { transform: scale(0.98); }
        
        /* 입력창 스타일 */
        input[type=number], input[type=text] { 
            min-height: 45px !important; 
            font-size: 16px !important; 
        }
        
        /* 멀티셀렉트 터치 영역 */
        div[data-baseweb="select"] > div {
            min-height: 45px !important;
        }

        /* --------------------------------------------------------------------- */
        /* [LAYOUT] Sidebar & UI Structure                                       */
        /* --------------------------------------------------------------------- */
        
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

        /* --------------------------------------------------------------------- */
        /* [ACTION BUTTONS] Semantic Colors                                      */
        /* --------------------------------------------------------------------- */
        
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

        /* --------------------------------------------------------------------- */
        /* [RESPONSIVE] Mobile Adjustment                                        */
        /* --------------------------------------------------------------------- */
        @media (max-width: 768px) { 
            .stDataEditor { font-size: 13px !important; }
            h1 { font-size: 18px !important; margin: 0 !important; padding: 0 !important; }
            div[data-testid="column"] { margin-bottom: 5px; }
            div.stSelectbox { margin-bottom: 5px; }
            
            div[data-testid="stToast"] {
                bottom: 20px; left: 10px; right: 10px; width: auto;
            }
        }
        </style>
    """, unsafe_allow_html=True)
