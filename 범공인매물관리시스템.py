import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="데이터 긴급 진단 모드", layout="wide")

# [1. 새 주소 박제]
SHEET_URL = "https://docs.google.com/spreadsheets/d/1bmTnLu-vMvlAGRSsCI4a8lk00U38covWl5Wfn9JZYVU/edit"

st.title("🔍 데이터 연결 긴급 진단")

try:
    # [2. 연결 시도]
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # [3. 시트의 진짜 이름들 확인]
    # 사장님이 만든 구글 시트에 어떤 탭들이 있는지 강제로 출력합니다.
    st.subheader("1. 구글 시트 탭 목록 확인")
    # 아래 함수는 시트 내부의 모든 워크시트 이름을 가져오려 시도합니다.
    df_test = conn.read(spreadsheet=SHEET_URL, ttl=0) 
    st.write("✅ 시트 연결 성공! 현재 읽어온 데이터의 컬럼들:", df_test.columns.tolist())
    st.write(f"✅ 현재 로드된 데이터 행 개수: {len(df_test)}건")

    # [4. '임대' 탭 강제 로드 테스트]
    st.subheader("2. '임대' 탭 로드 테스트")
    try:
        df_real = conn.read(spreadsheet=SHEET_URL, worksheet="임대", ttl=0)
        st.success(f"🎉 '임대' 탭에서 {len(df_real)}개의 데이터를 찾았습니다!")
        st.dataframe(df_real.head(10)) # 데이터 10줄만 먼저 보여줌
    except Exception as e:
        st.error(f"❌ '임대' 탭을 읽는 데 실패했습니다. 원인: {e}")
        st.info("💡 해결책: 구글 시트 하단 탭 이름이 정확히 '임대'인지 확인하세요. (띄어쓰기 주의!)")

except Exception as global_e:
    st.error(f"🚨 시스템 전체 오류 발생: {global_e}")
    st.warning("💡 해결책: Secrets에 주소가 제대로 들어갔는지, 구글 시트 공유 권한이 '편집자'인지 다시 확인하세요.")

st.markdown("---")
st.write("📝 **위의 진단 결과에서 '0건'이 나오거나 에러가 뜨면 그 메시지를 저에게 알려주세요.**")
