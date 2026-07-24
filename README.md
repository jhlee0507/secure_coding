# Tiny Second-hand Shopping Platform

> **Secure SDLC를 적용한 Flask 기반 교육용 중고거래 플랫폼**

---

## 기능

* 사용자가 플랫폼에 회원가입하고 로그인하며 비밀번호를 변경할 수 있어야 함.
* 상품을 등록하고 조회·검색·수정할 수 있어야 함.
* 플랫폼 사용자 간 1:1 소통과 새 메시지 자동 확인이 가능해야 함.
* 악성 사용자나 상품을 신고하고 관리자가 차단할 수 있어야 함.
* 사용자 간 가상 포인트를 송금할 수 있어야 함.
* 관리자가 사용자, 상품, 신고, 거래 및 감사 로그를 관리할 수 있어야 함.
* CSRF, 접근 제어, 입력 검증, 요청 속도 제한 등 보안 대책을 적용할 것.

> 지갑은 교육용 가상 포인트이며 실제 화폐, 계좌 또는 결제 수단과 연결되지 않습니다.


---

## 환경 설정

### 1) 저장소 복제

```bash
git clone https://github.com/jhlee0507/secure_coding.git
cd secure_coding
```

### 2) 가상환경 생성 및 패키지 설치

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3) 환경 변수 설정

```bash
cp .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"
```

생성된 문자열을 `.env` 파일의 `SECRET_KEY` 값으로 설정한 뒤 환경 변수를 불러옵니다.

```bash
set -a
source .env
set +a
```

운영 환경에서는 `.env`의 `APP_ENV=production`, `COOKIE_SECURE=true`를 함께 설정해야 합니다. 이때 안전한 `SECRET_KEY` 또는 Secure 쿠키 설정이 빠지면 애플리케이션이 실행을 거부합니다.

### 4) 데이터베이스 초기화

```bash
flask --app run.py init-db
```

관리자 계정이 필요한 경우 다음 명령을 추가로 실행합니다.

```bash
flask --app run.py create-admin
```

---

## 실행 방법

```bash
python run.py
```

브라우저에서 [http://127.0.0.1:5000](http://127.0.0.1:5000)에 접속합니다.

---

## 테스트

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

보안 문제 제보 방법은 [SECURITY.md](SECURITY.md)를 확인하세요.
