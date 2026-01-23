#!/bin/bash

# Tableau Meta JSON MVP 데모 실행 스크립트

echo "🚀 Tableau Meta JSON MVP Demo"
echo "================================"
echo ""

# 1. Python 버전 확인
echo "Python 버전 확인 중..."
python3 --version

# 2. Rich 라이브러리 설치 확인 및 설치
echo ""
echo "필수 패키지 설치 중..."
python3 -m pip install rich --quiet --upgrade

# 3. PYTHONPATH 설정
export PYTHONPATH=$PYTHONPATH:.

# 4. 데모 실행
echo ""
echo "데모를 시작합니다..."
echo ""
python3 demo_mvp.py
