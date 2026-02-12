import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# [1. 시스템 설정]
st.set_page_config(
    page_title="범공인 Pro (v24.15)",
    layout="wide",
    initial_sidebar_state="collapsed"  # 모바일 편의성 위해 사이드바 기본 닫힘
)

# 사장님이 만드신 '값만 붙여넣기' 완료된 새 시트 주소
SHEET_URL = "https://docs.google.com/spreadsheets/d/1bmTnLu-vMvlAGRSsCI4a8lk00U38covWl5Wfn9JZYVU/edit"

# [2. 스타일: 모바일 터치 최적화]
st.markdown("""
    <style>
    /* 버튼 크기 키우기 */
    .stButton button { min-height: 50px !important; font-size: 16px !important; font-weight: bold !important; }
    /* 모바일 폰트 조정 */
    @media (max-width: 768px) { 
        .stDataEditor { font-size: 13px !important; }
        h1 { font-size: 24px !important; }
    }
    </style>
""", unsafe_allow_html=True)

# [3. 데이터 로드 엔진]
@st.cache_data(ttl=60) # 60초마다 갱신
def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # 탭 이름 지정 없이 기본(첫번째) 시트를 읽어와 에러 방지
    df = conn.read(spreadsheet=SHEET_URL, ttl=0)
    
    # [컬럼 매핑] 사장님 시트의 '실제 이름' -> 시스템 '내부 이름'으로 변경
    # 공백 제거 및 이름 통일
    df.columns = df.columns.str.strip()
    mapping = {
        "보증금(만원)": "보증금",
        "월차임(만원)": "월차임",
        "권리금_입금가(만원)": "권리금",
        "전용면적(평)": "면적",
        "매물 특징": "내용",
        "지역_번지": "번지",
        "관리비(만원)": "관리비"
    }
    df = df.rename(columns=mapping)
    
    # NaN(빈값) 처리
    df = df.fillna("")
    
    # [핵심 에러 수정] '선택' 컬럼이 이미 엑셀에 있다면 삭제 후 다시 생성 (중복 방지)
    if '선택' in df.columns:
        df = df.drop(columns=['선택'])
    
    # 시스템용 체크박스 컬럼 생성 (맨 앞에 추가)
    df.insert(0, '선택', False)
    
    return df

# [4. 메인 실행 로직]
st.title("🏙️ 범공인 매물장")

try:
    # 데이터 로드 시도
    df_main = load_data()
    
    # 성공 메시지 (모바일에서도 잘 보이게)
    st.success(f"✅ 데이터 {len(df_main)}건 로드 완료!")
    
    # [MODULE: LIST_SECTION] 리스트 출력
    # 모바일에서 스크롤 하기 편하도록 height를 600으로 설정
    edited_df = st.data_editor(
        df_main,
        use_container_width=True, # 화면 꽉 차게
        hide_index=True,
        height=600, # 목록을 길게 보여줌
        column_config={
            "선택": st.column_config.CheckboxColumn(width="small"),
            "보증금": st.column_config.NumberColumn("보증금(만)", format="%d"),
            "월차임": st.column_config.NumberColumn("월세(만)", format="%d"),
            "면적": st.column_config.NumberColumn("면적(평)", format="%.1f"),
            "내용": st.column_config.TextColumn("특징", width="large"),
        },
        # 보여줄 컬럼 순서 지정 (모바일에서 중요한 것부터)
        column_order=["선택", "구분", "지역_구", "지역_동", "보증금", "월차임", "면적", "번지", "내용"]
    )

except Exception as e:
    st.error("🚨 데이터 로드 중 문제가 발생했습니다.")
    st.error(f"에러 내용: {e}")
    st.info("💡 팁: 구글 시트의 공유 권한이 '링크가 있는 모든 사용자(편집자)'인지 확인해주세요.")

# [5. 액션 패널 (준비 중)]
st.divider()
st.caption("Developed by Gemini & Pro-Mode")
