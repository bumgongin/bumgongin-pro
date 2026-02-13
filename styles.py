# styles.py
# 범공인 Pro v24 Enterprise - Style Definition Module (Final)
# Version: 24.21.5

import streamlit as st

def apply_custom_css():
    st.markdown("""
        <style>
        /* --------------------------------------------------------------------- */
        /* [CORE] Mobile Scroll & Container Control                              */
        /* --------------------------------------------------------------------- */
        
        /* 전체 페이지 오버스크롤 방지 */
        body {
            overscroll-behavior-y: none;
        }

        /* 데이터 리스트 컨테이너 디자인 */
        div[data-testid="stDataEditor"] {
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            background-color: #ffffff;
        }

        /* 리스트 내부 스크롤바 (높이 제한 코드 삭제됨) */
        div[data-testid="stDataEditor"] > div {
            overflow-y: auto !important;
            -webkit-overflow-scrolling: touch !important;
            scrollbar-width: thin;
            scrollbar-color: #888 #f1f1f1;
        }
        
        /* 스크롤바 디자인 */
        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-track { background: #f1f1f1; border-radius: 4px; }
        ::-webkit-scrollbar-thumb { background: #bbb; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #888; }

        /* --------------------------------------------------------------------- */
        /* [TOUCH OPTIMIZATION] Fat-Finger Friendly Interface                    */
        /* --------------------------------------------------------------------- */
        
        /* 버튼 스타일 */
        .stButton button { 
            min-height: 50px !important; 
            font-size: 15px !important; 
            font-weight: 600 !important; 
            width: 100%;
            border-radius: 8px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
            transition: all 0.2s;
        }
        .stButton button:active { transform: scale(0.98); }
        
        /* 입력창 스타일 */
        input[type=number], input[type=text] { 
            min-height: 45px !important; 
            font-size: 16px !important; 
            padding-left: 12px !important;
        }
        
        /* 멀티셀렉트 터치 영역 */
        div[data-baseweb="select"] > div {
            min-height: 45px !important;
            align-items: center;
        }

        /* --------------------------------------------------------------------- */
        /* [LAYOUT] Sidebar & Spacing                                            */
        /* --------------------------------------------------------------------- */
        
        /* 사이드바 여백 */
        section[data-testid="stSidebar"] .block-container {
            padding-top: 2rem;
            padding-bottom: 5rem;
        }
        
        /* 사이드바 내부 간격 */
        [data-testid="stSidebar"] div[data-testid="stVerticalBlock"] {
            gap: 1rem;
        }
        
        /* Expander 헤더 */
        div[data-testid="stExpander"] details summary p { 
            font-size: 1.05rem; 
            font-weight: 600; 
            color: #333;
            padding: 8px 0;
        }

        /* --------------------------------------------------------------------- */
        /* [BUTTONS] Semantic Colors                                             */
        /* --------------------------------------------------------------------- */
        
        /* 보조 버튼 (회색) */
        div[data-testid="stHorizontalBlock"] button[kind="secondary"] { 
            border: 1px solid #d0d0d0; 
            background-color: #f8f9fa;
            color: #333;
        }
        
        /* 위험/주요 버튼 (빨강) */
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
            h1 { font-size: 22px !important; margin-bottom: 0.5rem !important; }
            div[data-testid="column"] { margin-bottom: 5px; }
            div.stSelectbox { margin-bottom: 8px; }
            
            div[data-testid="stToast"] {
                bottom: 10px; left: 10px; right: 10px; width: auto;
            }
        }
        </style>
    """, unsafe_allow_html=True)
