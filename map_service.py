# map_service.py (전체 교체용)
# Feature: Naver Map API Integration (Dynamic Height Support)

import streamlit as st
import requests

# .streamlit/secrets.toml 파일에 [naver_map] 섹션이 정의되어 있어야 합니다.
try:
    NAVER_CLIENT_ID = st.secrets["naver_map"]["client_id"]
    NAVER_CLIENT_SECRET = st.secrets["naver_map"]["client_secret"]
except Exception:
    # 로컬 테스트용 혹은 시크릿 없을 경우 더미 값 (실제 작동 안함)
    NAVER_CLIENT_ID = ""
    NAVER_CLIENT_SECRET = ""

def get_naver_geocode(address):
    """
    주소를 입력받아 위도(Latitude), 경도(Longitude)를 반환합니다.
    """
    if not address:
        return None, None
    
    url = "https://maps.apigw.ntruss.com/map-geocode/v2/geocode"
    
    headers = {
        "X-NCP-APIGW-API-KEY-ID": NAVER_CLIENT_ID,
        "X-NCP-APIGW-API-KEY": NAVER_CLIENT_SECRET
    }
    
    try:
        response = requests.get(url, headers=headers, params={"query": address})
        
        if response.status_code == 200:
            data = response.json()
            if data.get('addresses'):
                x = data['addresses'][0]['x']
                y = data['addresses'][0]['y']
                return y, x
        return None, None
            
    except Exception as e:
        print(f"Geocoding Error: {e}")
        return None, None

def fetch_map_image(lat, lng, zoom_level=16, height=300):
    """
    위도, 경도, 줌 레벨, 높이를 받아 정적 지도 이미지(Binary)를 반환합니다.
    (네이버 API 제한에 맞춰 높이는 최대 1024px로 자동 조정됩니다)
    """
    if not lat or not lng:
        return None
    
    url = "https://maps.apigw.ntruss.com/map-static/v2/raster"
    
    headers = {
        "X-NCP-APIGW-API-KEY-ID": NAVER_CLIENT_ID,
        "X-NCP-APIGW-API-KEY": NAVER_CLIENT_SECRET
    }
    
    # [안전장치] 네이버 API 최대 한계치인 1024를 넘지 않도록 조정
    safe_height = min(int(height), 1024)
    
    # 지도 옵션 설정 (가로 너비 1000 고정, 높이는 가변)
    params = {
        "w": "1000",
        "h": str(safe_height), 
        "center": f"{lng},{lat}",
        "level": str(zoom_level),
        "markers": f"type:t|size:mid|pos:{lng} {lat}|label:매물",
        "scale": "2" # 고해상도 디스플레이 대응
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            return response.content
        else:
            print(f"Naver Static Map API Error: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Map Fetch Error: {e}")
        return None
