# Phase 1: MVP 로드맵

## 목표
Discord에서 대화하면 로컬 Obsidian vault에 지식이 축적되는 기본 루프 완성.

## 마일스톤

### M1: 프로젝트 기반 구축
- [x] Python 프로젝트 초기화 (pyproject.toml)
- [x] 기본 설정 파일 구조 (.env + python-dotenv)
- [x] CI/CD 설정 (GitHub Actions: ruff + mypy)
- [x] 코어 모듈 포팅 (claude-discord-bot → second-brain-kit)

### M2: Discord 봇 코어
- [x] 봇 실행 테스트 (로컬 환경)
- [x] Claude CLI 연동 검증 (메시지 → Claude → 응답 루프)
- [x] 메시지 분할 검증 (2000자 제한, 코드블록 존중)
- [x] 파일 첨부/전송 검증
- [x] 에러 핸들링 강화

### M3: Vault 매니저
- [ ] 마크다운 파일 읽기/쓰기
- [ ] YAML frontmatter 파싱/생성
- [ ] 기본 검색 (파일명, 태그, 전문 검색)
- [ ] 자동 태깅 (Claude가 대화에서 주제 추출 → 태그 생성)

### M4: MCP 매니저
- [ ] MCP 서버 레지스트리 (지원 MCP 목록)
- [ ] 설치 스크립트 (npm install + 설정 파일 생성)
- [ ] 3개 MCP 지원: Google Calendar, Todoist, RSS Reader
- [ ] 설정 위저드 (API 키/OAuth 입력 가이드)

### M5: 인스톨러 v1
- [ ] CLI 기반 설치 스크립트 (Linux)
- [ ] Obsidian 설치 확인/안내
- [ ] vault 구조 + 템플릿 자동 생성
- [ ] Discord 봇 토큰 설정 가이드
- [ ] 데몬 등록 (systemd user service)

## 완료 기준
- 비개발자가 README를 따라 30분 내에 세팅 가능
- Discord에서 대화하면 vault에 노트가 생성됨
- MCP 3개 중 1개 이상 작동
