# Tiny Second-hand Shopping Platform

Flask 기반 중고거래 플랫폼입니다. 회원가입, 상품 등록·검색, 1:1 메시지, 악성 사용자·상품 신고 및 차단, 사용자 간 가상 포인트 송금, 관리자 콘솔을 제공합니다.

> 지갑은 교육용 가상 포인트입니다. 실제 화폐, 계좌 또는 결제 수단과 연결되지 않습니다.

## 주요 기능

- 회원가입, 로그인, 프로필 관리
- 상품 등록, 조회, 검색, 수정, 판매 상태 및 공개 상태 관리
- 사용자 간 DB 기반 1:1 메시지
- 비밀번호 재인증을 포함한 가상 포인트 송금 및 거래 내역
- 사용자·상품 신고와 중복 신고 방지
- 관리자 사용자 차단, 상품 비공개, 신고 처리, 거래·감사 로그 조회
- CSRF, 접근 제어, 입력 검증, 요청 속도 제한, 보안 헤더

## 기술 구성

- Python 3.10+
- Flask 3.1.3 / Jinja2
- Flask-SQLAlchemy / SQLite
- Flask-WTF CSRF
- Flask-Limiter
- pytest / pytest-cov

애플리케이션은 기능별 Blueprint로 분리되어 있습니다.

```text
app/
├── __init__.py       # 애플리케이션 팩토리, 공통 보안 처리, CLI
├── models.py         # 사용자, 상품, 메시지, 송금, 신고, 감사 로그
├── auth.py           # 가입, 로그인, 프로필
├── products.py       # 상품과 검색
├── messages.py       # 1:1 메시지
├── wallet.py         # 가상 포인트 송금
├── reports.py        # 신고 접수
├── admin.py          # 관리자 콘솔
├── security.py       # 인증·권한·입력 검증
├── templates/        # Jinja2 화면
└── static/           # CSP와 호환되는 정적 스타일
tests/                # 기능·보안 회귀 테스트
REPORT.md             # 개발 전 과정 보고서 원본
```

## 실행 방법

아래 과정은 linux·macOS의 Bash 환경을 기준으로 합니다. Python 3.10 이상이 필요합니다.

### 1. 프로젝트 디렉터리로 이동

현재 실습 환경에서는 다음과 같이 이동합니다.

```bash
cd /home/jhlee/whs/secure_coding
```

GitHub에서 새로 내려받은 경우에는 다음 명령을 사용합니다.

```bash
git clone <GITHUB_REPOSITORY_URL>
cd <REPOSITORY_DIRECTORY>
```

### 2. 가상환경 생성 및 의존성 설치

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

터미널을 다시 열었다면 실행 전에 `source .venv/bin/activate`를 다시 입력해야 합니다.

### 3. 환경 변수 설정

```bash
cp .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"
```

두 번째 명령이 출력한 무작위 문자열을 `.env`의 `SECRET_KEY` 값으로 교체합니다. 로컬 HTTP 실행에서는 `COOKIE_SECURE=false`를 유지합니다.

```dotenv
SECRET_KEY=위에서_생성한_무작위_문자열
DATABASE_URL=sqlite:///market.sqlite3
COOKIE_SECURE=false
INITIAL_DEMO_BALANCE=100000
```

설정을 현재 셸에 로드합니다.

```bash
set -a
source .env
set +a
```

`.env`는 Git에 포함되지 않습니다. 새 터미널에서 실행할 때는 가상환경 활성화와 환경 변수 로드를 다시 수행합니다.

### 4. 데이터베이스 초기화

최초 실행 시 한 번 수행합니다. 같은 명령을 다시 실행해도 기존 테이블과 데이터는 삭제되지 않습니다.

```bash
flask --app run.py init-db
```

관리자 기능을 시험하려면 관리자 계정을 만듭니다.

```bash
flask --app run.py create-admin
```

명령이 사용자명과 비밀번호를 물어보면 직접 입력합니다. 비밀번호는 대문자·소문자·숫자·특수문자를 포함한 10자 이상이어야 합니다. 일반 사용자는 웹 화면의 회원가입 메뉴에서 생성할 수 있습니다.

### 5. 개발 서버 실행

```bash
python run.py
```

다음 메시지가 나타나면 정상적으로 실행된 것입니다.

```text
* Running on http://127.0.0.1:5000
```

브라우저에서 [http://127.0.0.1:5000](http://127.0.0.1:5000)에 접속합니다. 서버는 실행한 터미널에서 `Ctrl+C`를 누르면 종료됩니다.

### 6. 다시 실행할 때

데이터베이스 초기화와 패키지 설치는 다시 할 필요가 없습니다.

```bash
cd /home/jhlee/whs/secure_coding
source .venv/bin/activate
set -a
source .env
set +a
python run.py
```

### 운영 환경 실행 예시

운영 환경에서는 충분히 긴 무작위 `SECRET_KEY`를 사용하고 HTTPS 환경에서 `COOKIE_SECURE=true`로 설정해야 합니다.

```bash
COOKIE_SECURE=true gunicorn --workers 2 --bind 127.0.0.1:8000 'run:app'
```

Gunicorn 앞에 HTTPS를 종료하는 리버스 프록시를 두고, 프록시·방화벽·백업 정책을 함께 구성해야 합니다. 기본 메모리 기반 rate-limit 저장소는 단일 프로세스 데모용입니다. 다중 서버 환경에서는 Redis 등 공유 저장소로 변경합니다.

## 테스트

```bash
pip install -r requirements-dev.txt
pytest -q
pytest --cov=app --cov-report=term-missing
```

2026-07-22 기준 결과:

```text
24 passed
TOTAL 609 statements, 86% coverage
```

`pip-audit -r requirements.txt` 결과 알려진 취약점은 0건입니다. 초기 고정 버전 Flask 3.1.1에서 `PYSEC-2026-2151`이 발견되어 수정 버전 3.1.3으로 갱신했습니다.

## 보안 설계 요약

- 비밀번호는 Werkzeug `scrypt`로 해시하며 평문을 저장하지 않습니다.
- 로그인 성공 시 기존 세션을 지워 세션 고정 공격을 방지합니다.
- 모든 상태 변경 요청은 POST와 CSRF 토큰을 사용합니다.
- 서버에서 입력 길이·형식·범위를 다시 검증합니다.
- ORM 바인딩 쿼리를 사용해 SQL 삽입을 방지합니다.
- 상품 수정은 소유자, 관리 기능은 관리자만 수행할 수 있습니다.
- 송금은 비밀번호를 재확인하고 조건부 차감과 기록을 하나의 DB 트랜잭션으로 처리합니다.
- 로그인, 가입, 상품 등록, 메시지, 송금, 신고에 요청 속도 제한을 적용합니다.
- 사용자 입력은 Jinja 자동 이스케이프를 거치며 CSP에서 인라인 스크립트를 허용하지 않습니다.
- 관리자 작업과 로그인·송금 등 중요 사건을 감사 로그로 남깁니다.

자세한 위협 모델, 체크리스트와 개선 내역은 [REPORT.md](REPORT.md)를 확인하세요. 보안 문제의 제보 절차는 [SECURITY.md](SECURITY.md)에 있습니다.

## 제출용 보고서 만들기

```bash
python scripts/build_report.py \
  --class-name '01반' \
  --student-name '홍길동' \
  --phone-suffix '1234' \
  --repository 'https://github.com/USER/REPOSITORY'
```

`dist/[WHS][secure-coding][01반]홍길동(1234).html`이 생성됩니다. Chrome에서 인쇄 → PDF 저장을 선택하거나 다음 명령으로 PDF를 생성할 수 있습니다.

```bash
google-chrome --headless --no-sandbox \
  --print-to-pdf='dist/[WHS][secure-coding][01반]홍길동(1234).pdf' \
  'file:///ABSOLUTE/PATH/TO/dist/[WHS][secure-coding][01반]홍길동(1234).html'
```
