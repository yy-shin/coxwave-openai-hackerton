# 오븐 AI

> 기획부터 영상 생성까지, AI 에이전트가 알아서 해드립니다

## 데모

<video src="docs/demo.mp4" controls></video>

## 문제 정의

Sora, Veo 등 다양한 비디오 생성 모델이 등장했지만, 실무에서 마케팅 영상을 제작하기엔 여전히 어렵습니다:

| 제약 사항 | 실무 영향 |
|-----------|-----------|
| **10초 내외의 짧은 영상 길이** | 30초 이상 광고 제작 시 여러 클립 수동 조합 필요 |
| **프롬프트 설계의 어려움** | 원하는 결과물을 얻기 위한 반복적인 시행착오 |
| **목적에 맞는 모델 선택** | Sora vs Veo 등 모델별 특성 파악 및 선택 부담 |
| **일관된 스토리라인 유지** | 여러 클립 간 톤앤매너, 스타일 통일 어려움 |

## 솔루션

LLM 기반 멀티에이전트가 **역질문 → 스토리보드 → 영상 생성 → 조합**을 자동 처리합니다.

```
사용자 요청 → 역질문으로 구체화 → 스토리보드 생성 → 세그먼트별 3개 영상 병렬 생성 → 사용자 선택 → 최종 영상
```

| 기존 방식 | OvenAI |
|-----------|--------|
| 영상 1개 제작에 **1-2주** | **5분 내 초안** |
| 외주 비용 **수백만원/편** | **API 비용만** |
| 기획-제작 간 **다수의 커뮤니케이션** | 에이전트가 **원스톱 처리** |

## 조건 충족 여부

- [x] OpenAI API 사용 (GPT-5.2, Sora, Agents SDK)
- [x] 멀티에이전트 구현 (Guardrail Agent → Main Agent → Video Generation)
- [x] 실행 가능한 데모

## 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                 Frontend (React + ChatKit.js)                   │
│   [요청/역질문] → [스토리보드] → [클립 선택] → [최종 영상]         │
└─────────────────────────────────────────────────────────────────┘
                              │ WebSocket
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              Backend (FastAPI + ChatKit Server)                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              OvenAI Agent (OpenAI Agents SDK)             │  │
│  │                                                           │  │
│  │  [Guardrail] → [Clarifying] → [Storyboard] → [Generation] │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              Video Generation Service                     │  │
│  │         [Sora Provider]    [Veo Provider]                 │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## 기술 스택

- **AI Agent**: OpenAI Agents SDK, GPT-5.2 (High Reasoning)
- **Video Generation**: OpenAI Sora, Google Veo
- **Backend**: Python 3.12, FastAPI, ChatKit Server
- **Frontend**: React, TypeScript, ChatKit.js, Tailwind CSS

## 설치 및 실행

```bash
# 환경 설정
cp .env.sample .env
# OPENAI_API_KEY, GOOGLE_API_KEY 입력

# 실행
npm run
```

## 향후 계획

- Video Editing 기능 (SAM2 기반 Asset Detection 및 제거)
- Sound / Music Generation 연동
- 더 많은 비디오 모델 지원 (Kling, Runway 등)

## 팀원

| 이름 | 역할 |
|------|------|
| 신윤열 | PM / 기획 |
| 강혜민 | Agent 개발 |
| 이성진 | Backend 개발 |
| 박유호 | Frontend 개발 |
