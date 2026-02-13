# styles.py
# 범공인 Pro v24 Enterprise - Style Definition Module (v24.21.8)
# Verified: Hyper Scroll Lock & Touch Optimization

import streamlit as st

def apply_custom_css():
    st.markdown("""
        <style>
        /* --------------------------------------------------------------------- */
        /* [CORE] Mobile Scroll Jail System (Hyper-Lock)                         */
        /* --------------------------------------------------------------------- */
        
        /* 1. 페이지 전체 오버스크롤(당겨서 새로고침) 차단 */
        html, body {
            overscroll-behavior-y: contain !important;
        }
        
        /* 2. 메인 컨테이너 스크롤 제어 */
        .stAppViewContainer {
            overscroll-behavior-y: contain !important;
        }

        /* 3. 데이터 리스트 컨테이너 (높이 고정) */
        div[data-testid="stDataEditor"] {
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            background-color: #ffffff;
            height: 520px !important; /* 강제 고정 */
        }

        /* 4. 리스트 내부 스크롤바 커스터마이징 */
        div[data-testid="stDataEditor"] > div {
            height: 100% !important;
            overflow-y: auto !important;
            -webkit-overflow-scrolling: touch !important; /* iOS 필수 */
            scrollbar-width: thin;
            scrollbar-color: #888 #f1f1f1;
        }
        
        /* 스크롤바 디자인 */
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: #f1f1f1; border-radius: 3px; }
        ::-webkit-scrollbar-thumb { background: #bbb; border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: #888; }

        /* --------------------------------------------------------------------- */
        /* [TOUCH OPTIMIZATION] Fat-Finger Friendly                              */
        /* --------------------------------------------------------------------- */
        
        /* 버튼: 높이 48px 이상 */
        .stButton button { 
            min-height: 48px !important; 
            font-size: 15px !important; 
            font-weight: 600 !important; 
            width: 100%;
            border-radius: 8px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
            transition: all 0.15s;
        }
        .stButton button:active { transform: scale(0.98); }
        
        /* 입력창: 높이 48px 이상 */
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
        /* [LAYOUT] Sidebar & Filter UI                                          */
        /* --------------------------------------------------------------------- */
        
        /* 사이드바 여백 */
        section[data-testid="stSidebar"] .block-container {
            padding-top: 2rem;
            padding-bottom: 5rem;
        }
        
        /* 컨테이너 내부 간격 */
        [data-testid="stSidebar"] div[data-testid="stVerticalBlock"] {
            gap: 1rem;
        }
        
        /* 검색 라벨 스타일 (돋보기 버튼용) */
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
