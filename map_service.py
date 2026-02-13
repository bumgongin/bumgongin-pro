# map_service.py
# 범공인 Pro v24 Enterprise - Map Service Module (v24.23.7)
# Feature: Naver Map API Integration (VPC Endpoint & Dynamic Zoom)

import streamlit as st
import requests
import urllib.parse

# NAVER CLOUD PLATFORM API CONFIG
# .streamlit/secrets.toml 파일에 [naver_map] 섹션이 정의되어 있어야 합니다.
NAVER_CLIENT_ID = st.secrets["naver_map"]["client_id"]
NAVER_CLIENT_SECRET = st.secrets["naver_map"]["client_secret"]

def get_naver_geocode(address):
    """
    주소를 입력받아 위도(Latitude), 경도(Longitude)를 반환합니다.
    Target Endpoint: https://maps.apigw.ntruss.com/map-geocode/v2/geocode
    """
    if not address:
        return None, None
    
    # VPC Endpoint 강제 적용
    url = "https://maps.apigw.ntruss.com/map-geocode/v2/geocode"
    
    headers = {
        "X-NCP-APIGW-API-KEY-ID": NAVER_CLIENT_ID,
        "X-NCP-APIGW-API-KEY": NAVER_CLIENT_SECRET
    }
    params = {"query": address}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            # 검색 결과가 존재하는지 확인
            if data.get('addresses'):
                # x: 경도(longitude), y: 위도(latitude)
                x = data['addresses'][0]['x']
                y = data['addresses'][0]['y']
                return y, x
            else:
                return None, None
        else:
            print(f"Naver Geocode API Error: {response.status_code}")
            return None, None
            
    except Exception as e:
        print(f"Geocoding Internal Error: {e}")
        return None, None

def fetch_map_image(lat, lng, zoom_level=16):
    """
    위도, 경도, 줌 레벨을 받아 정적 지도 이미지(Binary)를 반환합니다.
    Target Endpoint: https://maps.apigw.ntruss.com/map-static/v2/raster
    """
    if not lat or not lng:
        return None
    
    # VPC Endpoint 강제 적용
    url = "https://maps.apigw.ntruss.com/map-static/v2/raster"
    
    headers = {
        "X-NCP-APIGW-API-KEY-ID": NAVER_CLIENT_ID,
        "X-NCP-APIGW-API-KEY": NAVER_CLIENT_SECRET
    }
    
    # 지도 옵션 설정 (너비, 높이, 중심좌표, 줌레벨, 마커)
    # zoom_level 파라미터 연동 (기본값 16)
    params = {
        "w": "600",
        "h": "300",
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
        print(f"Map Fetch Internal Error: {e}")
        return None
