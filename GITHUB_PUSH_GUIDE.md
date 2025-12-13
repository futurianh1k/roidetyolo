# GitHub 푸시 가이드

## 📋 현재 상태

✅ **모든 변경사항이 로컬 Git에 커밋 완료**  
⏳ **GitHub에 푸시 대기 중** (4개 커밋)

---

## 🔄 푸시 대기 중인 커밋

```
1c6378a - Fix Streamlit version compatibility (최신)
36a2436 - Add main branch current status documentation
eddd781 - Add ROI TypeError fix documentation
bf9c111 - Fix ROI edit TypeError
```

---

## 📥 로컬 환경에서 GitHub 푸시 방법

### 방법 1: Personal Access Token (PAT) 사용 (권장)

#### 1단계: GitHub에서 Personal Access Token 생성

1. GitHub 로그인 → https://github.com/settings/tokens
2. **"Tokens (classic)"** 클릭
3. **"Generate new token (classic)"** 클릭
4. 토큰 이름 입력: `roidetyolo-push`
5. **`repo`** 권한 선택 (전체 체크)
6. **"Generate token"** 클릭
7. 생성된 토큰 복사 (한 번만 표시됨!)

#### 2단계: 로컬에서 푸시

```bash
cd ~/yolo/roidetyolo

# 푸시 (토큰을 비밀번호로 사용)
git push origin main

# Username: futurianh1k
# Password: [복사한 Personal Access Token 붙여넣기]
```

#### 3단계: 토큰 저장 (선택사항)

매번 입력하지 않으려면:
```bash
git config --global credential.helper store
git push origin main
# 한 번 입력하면 저장됨
```

---

### 방법 2: SSH 키 사용

#### 1단계: SSH 키 생성 (없는 경우)

```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
# Enter 3번 (기본 경로, 비밀번호 없이)
```

#### 2단계: 공개 키 확인 및 복사

```bash
cat ~/.ssh/id_ed25519.pub
# 출력된 내용 전체 복사
```

#### 3단계: GitHub에 SSH 키 등록

1. GitHub 로그인 → https://github.com/settings/keys
2. **"New SSH key"** 클릭
3. Title: `ubuntu-yolo-server`
4. Key: 복사한 공개 키 붙여넣기
5. **"Add SSH key"** 클릭

#### 4단계: Remote URL을 SSH로 변경

```bash
cd ~/yolo/roidetyolo
git remote set-url origin git@github.com:futurianh1k/roidetyolo.git
git remote -v  # 확인
```

#### 5단계: 푸시

```bash
git push origin main
```

---

### 방법 3: GitHub CLI (gh) 사용

#### 1단계: GitHub CLI 설치

```bash
# Ubuntu/Debian
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install gh -y
```

#### 2단계: 인증

```bash
gh auth login
# GitHub.com 선택
# HTTPS 선택
# Yes (authenticate with GitHub credentials)
# 브라우저에서 인증 완료
```

#### 3단계: 푸시

```bash
cd ~/yolo/roidetyolo
git push origin main
```

---

## 🧪 푸시 후 확인

### GitHub 웹에서 확인

1. https://github.com/futurianh1k/roidetyolo
2. **main** 브랜치 선택
3. 최근 커밋 확인:
   - `Fix Streamlit version compatibility...`
   - `Add main branch current status documentation`
   - `Add ROI TypeError fix documentation`
   - `Fix ROI edit TypeError...`

### 로컬에서 확인

```bash
cd ~/yolo/roidetyolo

# 푸시 상태 확인
git status

# 로그 확인
git log origin/main..HEAD --oneline
# (출력이 없으면 푸시 완료)
```

---

## 📊 푸시할 변경사항

| 파일 | 변경 내용 |
|------|----------|
| `streamlit_app.py` | ✅ use_column_width 적용 (576, 823번 라인) |
| `STREAMLIT_VERSION_FIX.md` | ✅ 신규 문서 추가 (3.6KB) |
| `ROI_FIX_GUIDE.md` | ✅ 신규 문서 추가 (2.3KB) |
| `MAIN_BRANCH_STATUS.md` | ✅ 신규 문서 추가 (4.7KB) |
| `ROI_FIX_SUMMARY.md` | ✅ 신규 문서 추가 (3.2KB) |

---

## ⚠️ 주의사항

### 이미 로컬에 수정한 파일이 있는 경우

로컬 파일(`~/yolo/roidetyolo/streamlit_app.py`)이 이미 수정되어 있다면:

```bash
cd ~/yolo/roidetyolo

# 현재 로컬 변경사항 확인
git status

# 로컬 변경사항이 있다면 백업
cp streamlit_app.py streamlit_app.py.local_backup

# 샌드박스 수정사항 가져오기 (충돌 시 병합 필요)
git pull origin main
```

---

## 🎯 빠른 푸시 명령어 (PAT 방식)

```bash
cd ~/yolo/roidetyolo

# 푸시 (Personal Access Token 입력 필요)
git push origin main

# 성공 메시지 확인:
# "To https://github.com/futurianh1k/roidetyolo.git"
# "   old_hash..new_hash  main -> main"
```

---

## 📝 트러블슈팅

### 오류 1: "Authentication failed"
**원인**: Personal Access Token이 잘못되었거나 만료됨  
**해결**: 새 토큰 생성 후 재시도

### 오류 2: "rejected (non-fast-forward)"
**원인**: 원격 저장소에 더 최신 커밋이 있음  
**해결**:
```bash
git pull --rebase origin main
git push origin main
```

### 오류 3: "Permission denied (publickey)"
**원인**: SSH 키가 등록되지 않음  
**해결**: 방법 2의 SSH 키 등록 과정 진행

---

**작성일**: 2025-06-01  
**브랜치**: main  
**커밋 대기**: 4개
