# Current Session

## 상태: M1 완료, M2 대기

## 완료된 작업
- [x] 아이디어 검증 (Phase 1-6)
- [x] Obsidian 프로젝트 명세 작성
- [x] GitHub 리포 생성 (public)
- [x] 초기 디렉토리 구조 세팅
- [x] claude-discord-bot 코드 분석 (재사용 패턴 식별)
- [x] Node.js + TypeScript 프로젝트 초기화
- [x] Config 로딩 시스템 (yaml + .env + env vars)
- [x] Claude provider 추상화 (CLI + API 듀얼 모드)
- [x] CI/CD 설정 (GitHub Actions)

## 다음 작업
- [ ] M2: Discord 봇 코어 (discord.js 프레임워크 + 대화 루프)
- [ ] M2: 메시지 분할기 (2000자 제한)
- [ ] M3: Vault 매니저 (마크다운 읽기/쓰기/검색)

## 주의사항
- Claude 연동은 CLI 모드(`claude -p` subprocess)가 기본. API 모드는 Phase 2.
- CLI 모드만 vault 접근/MCP 연동 가능. API 모드는 채팅만.
- claude-discord-bot은 Python/discord.py → 직접 포크 대신 패턴만 TypeScript로 재구현
