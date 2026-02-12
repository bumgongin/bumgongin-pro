import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# [시스템 설정]
st.set_page_config(page_title="범공인 Pro - 진단 모드")

st.title("🩺 시스템 진단: 구글 시트 탭 이름 검증")

SHEET_URL = "https://docs.google.com/spreadsheets/d/1bmTnLu-vMvlAGRSsCI4a8lk00U38covWl5Wfn9JZYVU/edit"

try:
    # 1. 연결 설정
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    st.info("📡 구글 시트와 통신 중입니다...")
    
    # 2. 메타데이터 또는 전체 데이터 로드 시도
    # streamlit-gsheets는 직접적인 탭 목록 조회 함수가 없으므로, 
    # 에러 메시지나 기본 동작을 통해 정보를 역추적하거나, 
    # 가장 확실한 방법인 'gspread' 라이브러리 방식이 아닌 'pandas' 읽기 시도로 확인합니다.
    
    # (참고) streamlit-gsheets의 read()는 기본적으로 첫 번째 시트를 읽습니다.
    # 하지만 탭 목록을 직접 가져오는 기능은 제한적이므로, 
    # 여기서는 '모든 시트'를 읽어오기보다, 사용자가 지정한 리스트와 실제가 맞는지 테스트합니다.
    
    st.markdown("### 1. 현재 설정된 목표 탭 이름 (코드 상)")
    target_sheets = ["임대", "임대(종료)", "매매", "매매(종료)", "임대브리핑", "매매브리핑"]
    st.code(str(target_sheets))
    
    st.divider()
    
    st.markdown("### 2. 실제 연결 테스트 및 이름 검증")
    
    results = []
    
    # 각 시트 이름을 하나씩 대입해서 실제로 읽히는지 테스트
    for sheet_name in target_sheets:
        try:
            # ttl=0으로 캐시 없이 즉시 로드 시도
            df = conn.read(spreadsheet=SHEET_URL, worksheet=sheet_name, ttl=0, nrows=1)
            status = "✅ 성공"
            rows = len(df)
            msg = "연결 양호"
        except Exception as e:
            status = "❌ 실패"
            msg = str(e)
            
        results.append({
            "시트 이름 (입력값)": f"[{sheet_name}]", # 대괄호로 감싸 공백 확인
            "연결 상태": status,
            "진단 결과": msg
        })
    
    # 결과 테이블 표시
    st.table(pd.DataFrame(results))
    
    st.warning("""
    **💡 진단 결과 해석 가이드:**
    1. **'❌ 실패'**가 뜬 시트는 구글 시트 하단의 탭 이름과 코드가 **100% 일치하지 않는 것**입니다.
    2. 에러 메시지에 `WorksheetNotFound` 등이 포함되어 있다면 이름 오타입니다.
    3. **해결책:** 구글 시트를 열고 탭 이름을 더블 클릭한 뒤, **앞/뒤 공백**이 없는지 확인하세요.
    """)

except Exception as e:
    st.error(f"🚨 치명적 오류: {e}")
