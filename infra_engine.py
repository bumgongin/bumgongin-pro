import requests
import pandas as pd
import re
import math

# ==========================================
# 1. API 환경 설정
# ==========================================
NAVER_VPC_CLIENT_ID = "j6kk02fqy0"
NAVER_VPC_CLIENT_SECRET = "Lm0UTMBLuPWeDQJ4OZNn3ec82tvgAvllqJ46ceuU"
NAVER_VPC_ENDPOINT = "https://maps.apigw.ntruss.com/"

NAVER_VPC_HEADERS = {
    "x-ncp-apigw-api-key-id": NAVER_VPC_CLIENT_ID,
    "x-ncp-apigw-api-key": NAVER_VPC_CLIENT_SECRET,
    "Content-Type": "application/json"
}

KAKAO_REST_KEY = "72e1d9f46c8c70448510d2f6215ad512"
KAKAO_HEADERS = {"Authorization": f"KakaoAK {KAKAO_REST_KEY}"}
TIMEOUT_SEC = 1.5

# ==========================================
# 2. 유틸리티 함수
# ==========================================
def _call_kakao_local(endpoint, params):
    url = f"https://dapi.kakao.com/v2/local/search/{endpoint}.json"
    try:
        response = requests.get(url, headers=KAKAO_HEADERS, params=params, timeout=TIMEOUT_SEC)
        if response.status_code == 200:
            return response.json().get('documents', [])
        return []
    except Exception:
        return []

def _extract_exit_number(place_name):
    if not place_name or not isinstance(place_name, str): return ""
    try:
        match = re.search(r'(\d+번\s?출구)', place_name)
        if match: return match.group(1)
    except Exception: pass
    return ""

def _calculate_walking_data(origin_x, origin_y, dest_x, dest_y):
    if not (origin_x and origin_y and dest_x and dest_y): return 0, 0
    url = "https://apis-navi.kakaomobility.com/v1/directions"
    params = {"origin": f"{origin_x},{origin_y}", "destination": f"{dest_x},{dest_y}", "priority": "RECOMMEND", "car_type": 1}
    try:
        response = requests.get(url, headers=KAKAO_HEADERS, params=params, timeout=TIMEOUT_SEC)
        if response.status_code == 200:
            routes = response.json().get('routes', [])
            if routes:
                summary = routes[0].get('summary', {})
                d = summary.get('distance', 0)
                return d, round(d/67, 1)
    except Exception: pass
    try:
        dx = (float(dest_x) - float(origin_x)) * 88000
        dy = (float(dest_y) - float(origin_y)) * 111000
        d = int(math.sqrt(dx**2 + dy**2) * 1.25)
        return d, round(d/67, 1)
    except Exception: return 0, 0

# ==========================================
# 3. 핵심 분석 함수 (v24.28.0 리스트형 엔진)
# ==========================================

def get_commercial_analysis(lat, lng):
    """
    [통합 상권 분석]
    1. 지하철역 정밀 분석 (기존 유지)
    2. 주변 10대 필수 시설 리스트 (신규: 거리순 정렬)
    3. Top 10 앵커 브랜드 스캔 (기존 유지)
    """
    result = {
        "subway": {"station": "정보 없음", "exit": "", "dist": 0, "walk": 0},
        "facilities": pd.DataFrame(columns=['장소명', '업종', '거리(m)', '도보(분)']), # 신규 리스트
        "anchors": pd.DataFrame(columns=["브랜드", "지점명", "거리(m)", "도보(분)"])
    }

    try:
        if not lat or not lng: return result

        # [Step 1] 지하철역 분석
        sub_params = {"category_group_code": "SW8", "x": lng, "y": lat, "radius": 700, "sort": "distance"}
        subways_raw = _call_kakao_local("category", sub_params)
        subways = [s for s in subways_raw if '지하철,전철' in s.get('category_name', '')]

        if subways:
            nearest = subways[0]
            clean_name = re.sub(r'\(.*\)', '', nearest.get('place_name', '')).strip()
            station_name = clean_name.split()[0]
            
            # 출구 및 도보
            exit_params = {"query": f"{station_name} 출구", "x": lng, "y": lat, "radius": 700, "sort": "distance"}
            exits = _call_kakao_local("keyword", exit_params)
            target = exits[0] if exits else nearest
            exit_n = _extract_exit_number(target.get('place_name', '')) if exits else ""
            
            d, t = _calculate_walking_data(lng, lat, target.get('x'), target.get('y'))
            result["subway"] = {"station": station_name, "exit": exit_n, "dist": d, "walk": t}

        # [Step 2] 주변 10대 필수 시설 리스트 (New Logic)
        # 검색 대상: 편의점, 은행, 카페, 병원, 약국, 음식점 (반경 300m)
        target_cats = {
            "편의점": "CS2", "은행": "BK9", "카페": "CE7", 
            "병원": "HP8", "약국": "PM9", "음식점": "FD6"
        }
        
        all_places = []
        for cat_name, code in target_cats.items():
            # 각 카테고리별 상위 5개씩만 가볍게 수집
            p = {"category_group_code": code, "x": lng, "y": lat, "radius": 300, "sort": "distance", "size": 5}
            items = _call_kakao_local("category", p)
            for item in items:
                all_places.append({
                    "장소명": item.get('place_name'),
                    "업종": cat_name,
                    "거리(m)": int(item.get('distance', 0)),
                    "도보(분)": round(int(item.get('distance', 0)) / 67, 1)
                })
        
        # 거리순 정렬 후 상위 10개 추출
        if all_places:
            df_fac = pd.DataFrame(all_places)
            df_fac = df_fac.sort_values(by="거리(m)").head(10).reset_index(drop=True)
            result["facilities"] = df_fac

        # [Step 3] Top 10 앵커 시설 스캔
        anchors_list = []
        target_anchors = ["스타벅스", "맥도날드", "올리브영", "다이소", "버거킹", "써브웨이", "메가커피", "파리바게뜨", "컴포즈커피", "배스킨라빈스"]
        
        for anchor in target_anchors:
            p = {"query": anchor, "x": lng, "y": lat, "radius": 1000, "sort": "distance"}
            data = _call_kakao_local("keyword", p)
            if data:
                n = data[0]
                d = int(n.get('distance', 0))
                anchors_list.append({
                    "브랜드": anchor, "지점명": n.get('place_name'), 
                    "거리(m)": d, "도보(분)": round(d/67, 1)
                })
            else:
                anchors_list.append({"브랜드": anchor, "지점명": "없음", "거리(m)": "-", "도보(분)": "-"})
        
        result["anchors"] = pd.DataFrame(anchors_list)

    except Exception as e:
        print(f"[Commercial Analysis Error] {e}")
        return result

    return result

def get_demand_analysis(lat, lng):
    """
    [함수 2] 수요 분석 (기존 유지)
    """
    cols = ["구분", "시설명", "거리(m)"]
    default_df = pd.DataFrame(columns=cols)
    try:
        if not lat or not lng: return default_df
        
        demand = []
        seen = set()
        
        # 오피스, 교육, 행정 통합 검색
        targets = [
            (["지식산업센터", "오피스", "빌딩"], "업무시설", 500, "keyword"),
            ({"학교": "SC4", "학원": "AC5"}, "교육", 500, "category"),
            (["주민센터", "우체국", "구청", "경찰서"], "행정/공공", 800, "keyword")
        ]

        for keys, label_type, rad, method in targets:
            if method == "keyword":
                for k in keys:
                    p = {"query": k, "x": lng, "y": lat, "radius": rad}
                    items = _call_kakao_local("keyword", p)
                    for i in items:
                        if i['id'] not in seen:
                            demand.append({"구분": label_type, "시설명": i['place_name'], "거리(m)": int(i['distance'])})
                            seen.add(i['id'])
            else: # category
                for name, code in keys.items():
                    p = {"category_group_code": code, "x": lng, "y": lat, "radius": rad}
                    items = _call_kakao_local("category", p)
                    for i in items:
                        if i['id'] not in seen:
                            demand.append({"구분": f"{label_type}({name})", "시설명": i['place_name'], "거리(m)": int(i['distance'])})
                            seen.add(i['id'])

        if demand:
            df = pd.DataFrame(demand).sort_values(by="거리(m)").head(15).reset_index(drop=True)
            return df
        return default_df

    except Exception:
        return default_df
