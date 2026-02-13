# styles.py

# 범공인 Pro v24 Enterprise - Style Definition Module (v24.23.7)

# Feature: Map Controller & Mobile Card Optimized Layout



import streamlit as st



def apply_custom_css():

    st.markdown("""

        <style>

        /* --------------------------------------------------------------------- */

        /* [CORE] Dynamic Viewport Locking (100dvh)                              */

        /* --------------------------------------------------------------------- */

        html, body {

            height: 100dvh !important;

            overflow: hidden !important;

            overscroll-behavior: none !important;

            margin: 0 !important; padding: 0 !important;

        }

        

        .stAppViewContainer {

            height: 100dvh !important;

            overflow: hidden !important;

            touch-action: none;

        }

        

        /* 메인 컨텐츠 영역 스크롤 제어 */

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

        /* [MAP UI] Container & Controller Style                                 */

        /* --------------------------------------------------------------------- */

        .map-container {

            width: 100%; height: 250px;

            border-radius: 12px; overflow: hidden;

            box-shadow: 0 2px 8px rgba(0,0,0,0.1);

            border: 1px solid #e0e0e0;

            margin-bottom: 20px; background-color: #f8f9fa;

            display: flex; justify-content: center; align-items: center;

        }



        /* 지도 줌 컨트롤러 버튼 그룹 (하나로 뭉친 스타일) */

        div[data-testid="stHorizontalBlock"] button[kind="secondary"].map-control-btn {

            margin: 0 !important;

            border-radius: 0 !important;

            border-right: none !important;

            min-height: 40px !important;

            width: 40px !important;

            padding: 0 !important;

        }

        div[data-testid="stHorizontalBlock"] button[kind="secondary"].map-control-btn:last-child {

            border-right: 1px solid #d0d0d0 !important;

            border-top-right-radius: 6px !important;

            border-bottom-right-radius: 6px !important;

        }

        div[data-testid="stHorizontalBlock"] button[kind="secondary"].map-control-btn:first-child {

            border-top-left-radius: 6px !important;

            border-bottom-left-radius: 6px !important;

        }



        /* --------------------------------------------------------------------- */

        /* [CARD UI] 3-Layer Slim & Mobile Optimized                             */

        /* --------------------------------------------------------------------- */

        .listing-card {

            background-color: #ffffff;

            border-bottom: 1px solid #f0f0f0;

            /* 모바일 패딩 확장 (여백의 미) */

            padding: 15px 12px; 

            margin-bottom: 0px;

            transition: background-color 0.1s;

            pointer-events: auto !important;

            display: flex; 

            flex-direction: column; 

            gap: 6px; /* 내부 요소 간격 조정 */

        }

        

        .listing-card:active { background-color: #f5f5f5; }

        

        /* 1단: 가격 및 태그 (칼각 정렬) */

        .card-row-1 { 

            display: flex; 

            align-items: center; 

            gap: 8px; 

            margin-bottom: 2px;

            padding-left: 2px; /* 미세 좌측 여백 */

        }

        .card-tag {

            font-size: 0.75rem; font-weight: 700; color: #1565c0;

            background-color: #e3f2fd; padding: 3px 6px; border-radius: 4px; white-space: nowrap;

        }

        .card-price { 

            font-size: 1.1rem; 

            font-weight: 800; 

            color: #d32f2f; 

            white-space: nowrap;

            letter-spacing: -0.5px;

        }

        

        /* 2단: 주소 및 층수 (가독성 확보) */

        .card-row-2 { 

            font-size: 0.9rem; 

            color: #212121; 

            font-weight: 600; 

            white-space: nowrap; 

            overflow: hidden; 

            text-overflow: ellipsis;

            padding-left: 2px;

            margin-bottom: 2px;

        }

        

        /* 3단: 상세 스펙 (정보 전달력) */

        .card-row-3 { 

            font-size: 0.85rem; 

            color: #666; 

            gap: 8px; 

            white-space: nowrap; 

            overflow: hidden; 

            text-overflow: ellipsis;

            padding-left: 2px;

        }



        /* PC Responsive (가로 배치) */

        @media (min-width: 1024px) {

            .listing-card { flex-direction: row; padding: 12px 20px; justify-content: space-between; align-items: center; }

            .card-row-1, .card-row-2, .card-row-3 { margin-bottom: 0; flex: 1; }

            

            /* PC에서는 상세 버튼을 우측에 작게 */

            .card-btn-container { width: auto !important; margin-top: 0 !important; }

            .stButton.card-detail-btn button { width: auto !important; }

        }



        /* --------------------------------------------------------------------- */

        /* [LIST MODE] Data Editor Style                                         */

        /* --------------------------------------------------------------------- */

        div[data-testid="stDataEditor"] {

            border: 1px solid #e0e0e0; border-radius: 8px; background-color: #ffffff;

            touch-action: pan-y !important; -webkit-user-drag: none !important; pointer-events: auto !important;

        }

        div[data-testid="stDataEditor"] > div {

            overflow-y: auto !important; overscroll-behavior: contain !important;

            -webkit-overflow-scrolling: touch !important; scrollbar-width: thin;

        }

        div[data-testid="stDataEditor"] * { user-select: none !important; -webkit-user-select: none !important; }



        /* --------------------------------------------------------------------- */

        /* [UI ELEMENTS] Interactive Components                                  */

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

        

        div[data-testid="stCheckbox"] {

            display: flex; justify-content: center; align-items: center;

            height: 100%; padding-top: 12px; min-height: 44px;

        }

        div[data-testid="stCheckbox"] label { margin-bottom: 0px !important; }



        section[data-testid="stSidebar"] {

            overflow-y: auto !important; pointer-events: auto !important;

            overscroll-behavior: contain !important; touch-action: pan-y !important;

        }

        section[data-testid="stSidebar"] .block-container { padding-top: 2rem; padding-bottom: 5rem; }



        div[data-testid="stHorizontalBlock"] button[kind="secondary"] { border: 1px solid #d0d0d0; background-color: #f8f9fa; color: #333; }

        div[data-testid="stHorizontalBlock"] button[kind="primary"] { background-color: #ff4b4b; color: white; border: none; }



        /* --------------------------------------------------------------------- */

        /* [MOBILE ADAPTIVE] Extreme UX Optimization                             */

        /* --------------------------------------------------------------------- */

        @media (max-width: 768px) { 

            .stDataEditor { font-size: 13px !important; }

            h1 { font-size: 18px !important; margin: 0 !important; padding: 0 !important; }

            

            div[data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; gap: 6px !important; }

            div[data-testid="column"] { min-width: 30% !important; flex: 1 !important; }

            

            /* 모바일에서 카드 내 상세 버튼 꽉 차게 */

            .card-btn-container {

                width: 100% !important;

                margin-top: 8px !important;

            }

            .stButton.card-detail-btn button {

                width: 100% !important;

                background-color: #f1f3f4 !important;

                border: 1px solid #e0e0e0 !important;

                color: #333 !important;

            }

        }

        </style>

    """, unsafe_allow_html=True)
