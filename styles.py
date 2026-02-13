# styles.py
# 범공인 Pro v24 Enterprise - Style Definition Module (v24.21.10)
# Final Fix: Browser Scroll Override & Drag Block

import streamlit as st

def apply_custom_css():
    st.markdown("""
        <style>
        /* --------------------------------------------------------------------- */
        /* [CORE] Scroll Sovereignty (브라우저 스크롤 주권 강탈)                 */
        /* --------------------------------------------------------------------- */
        
        /* 1. 페이지 전체 스크롤 원천 차단 (위아래 들썩임 방지) */
        html, body {
            overflow: hidden !important;
            height: 100% !important;
            overscroll-behavior-y: none !important;
        }
        
        /* 2. 메인 뷰 컨테이너도 고정 */
        .stAppViewContainer {
            overflow: hidden !important;
            height: 100% !important;
        }

        /* 3. 데이터 에디터 컨테이너 (유일한 스크롤 허용 구역) */
        div[data-testid="stDataEditor"] {
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            background-color: #ffffff;
            touch-action: pan-y !important; /* 수직 스크롤만 허용 */
            -webkit-user-drag: none !important; /* 행 드래그 방지 */
        }

        /* 4. 리스트 내부 스크롤바 제어 */
        div[data-testid="stDataEditor"] > div {
            overflow-y: auto !important; /* 여기서만 스크롤 가능 */
            -webkit-overflow-scrolling: touch !important; /* iOS 관성 스크롤 */
            scrollbar-width: thin;
            scrollbar-color: #888 #f1f1f1;
        }
        
        /* 스크롤바 디자인 */
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: #f1f1f1; border-radius: 3px; }
        ::-webkit-scrollbar-thumb { background: #bbb; border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: #888; }

        /* --------------------------------------------------------------------- */
        /* [TOUCH OPTIMIZATION] Interaction Lock                                 */
        /* --------------------------------------------------------------------- */
        
        /* 텍스트 선택 및 드래그 방지 (리스트 내부) */
        div[data-testid="stDataEditor"] * {
            user-select: none !important;
            -webkit-user-select: none !important;
            /* overflow: visible 제거됨 (스크롤 로직 보호) */
        }

        /* 버튼 스타일 */
        .stButton button { 
            min-height: 50px !important; 
            font-size: 15px !important; 
            font-weight: 600 !important; 
            width: 100%;
            border-radius: 8px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
            transition: all 0.15s;
        }
        .stButton button:active { transform: scale(0.98); }
        
        /* 입력창 스타일 */
        input[type=number], input[type=text] { 
            min-height: 48px !important; 
            font-size: 16px !important; 
            padding-left: 12px !important;
        }
        
        /* 멀티셀렉트 터치 영역 */
        div[data-baseweb="select"] > div {
            min-height: 48px !important;
            align-items: center;
        }

        /* --------------------------------------------------------------------- */
        /* [LAYOUT] Sidebar & UI Structure                                       */
        /* --------------------------------------------------------------------- */
        
        /* 사이드바는 별도 스크롤 허용 */
        section[data-testid="stSidebar"] {
            overflow-y: auto !important; 
        }
        
        section[data-testid="stSidebar"] .block-container {
            padding-top: 2rem;
            padding-bottom: 5rem;
        }
        
        /* 컨테이너 내부 간격 */
        [data-testid="stSidebar"] div[data-testid="stVerticalBlock"] {
            gap: 1rem;
        }
        
        /* 검색 라벨 스타일 */
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
            h1 { font-size: 20px !important; margin-bottom: 0.5rem !important; }
            div[data-testid="column"] { margin-bottom: 5px; }
            div.stSelectbox { margin-bottom: 8px; }
            
            div[data-testid="stToast"] {
                bottom: 20px; left: 10px; right: 10px; width: auto;
            }
        }
        </style>
    """, unsafe_allow_html=True)
