// ==============================================================================
// 🌟 LAYER 1: 환경 설정 및 API 크레덴셜 로딩 (Constants & Credentials)
// ==============================================================================

const path = require('path');
require('dotenv').config({ path: path.join(__dirname, '.env') });
const log = require('./lib/logger');

// v3.0 API-Driven 전역 실행 제어 모드
const RUN_MODE = process.env.RUN_MODE || '1'; // '1': 웹훅 대기 무한루프, '2': 1회 실행 후 즉시 종료
const PORT = process.env.PORT || 3000;         // 내장 Webhook 서버 구동 포트

// 수집 비동기 독립 모듈 임포트
const { fetchMainstreamTrends } = require('./lib/ingestion/twitter_threads');
const { fetchOpinionLeaderPosts } = require('./lib/ingestion/opinions');
const { fetchTechDeepDive } = require('./lib/ingestion/tech_deepdive');

// 발행 및 웹훅 모듈 임포트
const { publishToThreads, startWebhookServer } = require('./lib/publishing/threads_api');


// ==============================================================================
// 🌟 LAYER 2: Webhook 초경량 서버 구동 및 생명주기 관리
// ==============================================================================

let webhookServerInstance = null;

/**
 * 실시간 답글 대응을 위한 내장 HTTP Webhook 서버를 활성화합니다.
 */
const initWebhookLifecycle = () => {
  log.section('Webhook 라이프사이클 가동');
  try {
    webhookServerInstance = startWebhookServer(PORT);
  } catch (err) {
    log.err(`웹훅 서버 기동 실패: ${err.message}`);
  }
};


// ==============================================================================
// 🌟 LAYER 3: 비동기 데이터 수집 엔진 (에러 격리 결합 장치)
// ==============================================================================

/**
 * D-1 기준의 여러 플랫폼 데이터를 비동기 병렬 구조로 동시 수집합니다.
 * 에러 고립화(Graceful Degradation) 기술에 의해 특정 API 오류가 나더라도
 * 성공한 플랫폼의 소스만 온전히 보존 및 반환합니다.
 */
const runIngestionPipeline = async () => {
  log.section('데이터 수집 단계 (Ingestion)');
  
  // 병렬 수집 요청 전개
  const tasks = [
    fetchMainstreamTrends(),
    fetchOpinionLeaderPosts(),
    fetchTechDeepDive()
  ];

  // Promise.allSettled를 통한 완벽한 오류 격리
  const results = await Promise.allSettled(tasks);
  const consolidatedRawData = [];

  results.forEach((res, idx) => {
    const modules = ['Mainstream Trends', 'Opinion Leaders', 'Tech DeepDive'];
    if (res.status === 'fulfilled') {
      consolidatedRawData.push(...res.value);
    } else {
      log.err(`${modules[idx]} 수집 파트 치명적 실패 (에러 고립됨): ${res.reason?.message}`);
    }
  });

  log.ok(`수집 통합 완료: 총 ${consolidatedRawData.length}개의 날것(Raw) 데이터 확보`);
  return consolidatedRawData;
};


// ==============================================================================
// 🌟 LAYER 4: 정규화 파서 및 Gemini 2.5 AI 큐레이터 연동 [DEPRECATED]
// ==============================================================================

/**
 * [공지] 
 * 수집된 데이터를 가공하고 큐레이션하는 기능은 하드코딩된 로직을 완전히 폐기하고
 * 에이전트 자율 스킬 기반 워크플로우(create_raw_posts/SKILL.md)로 100% 이관되었습니다.
 * 
 * 더 이상 start.js가 자동으로 AI를 호출하여 본문을 창작하지 않습니다.
 */
const runCurationPipeline = async (rawData) => {
  log.section('데이터 가공 & AI 큐레이션 단계 (Skill-driven)');
  log.info('현재 큐레이션 기능은 에이전트 스킬로 이관되어 start.js에서 자동 수행하지 않습니다.');
  log.info('수집된 Raw Data를 기반으로 에이전트에게 큐레이션을 지시해주세요.');
  return null;
};


// ==============================================================================
// 🌟 LAYER 5: Threads 공식 API 전송 및 발행 장치
// ==============================================================================

/**
 * 생성된 마스터 큐레이션 본문을 Threads 공식 API를 연동해 발행합니다.
 */
const runPublishingPipeline = async (curatedContent) => {
  log.section('Threads 공식 API 포스팅 발행 단계 (Publishing)');
  const mediaId = await publishToThreads(curatedContent);
  return mediaId;
};


// ==============================================================================
// 🌟 LAYER 6: Webhook 기반 AI 자동 응대 핸들러
// ==============================================================================

/**
 * [가상 시뮬레이션 장치] 로컬 모의 구동 및 수동 Webhook 트리거 테스트를 지원합니다.
 * 실제 유입은 LAYER 2의 HTTP POST 수신부를 통해 비동기로 핸들링됩니다.
 */
const simulateWebhookEvent = async (mediaId) => {
  if (RUN_MODE === '2') return;

  log.section('실시간 모의 댓글 Webhook 시뮬레이션');
  log.step('3초 뒤 가상 사용자 댓글 Webhook 유입 시뮬레이션을 개시합니다...');
  
  setTimeout(async () => {
    // 가상의 meta webhook 페이로드 구조
    const mockPayload = {
      object: 'threads',
      entry: [{
        id: 'mock_entry_id',
        time: Math.floor(Date.now() / 1000),
        changes: [{
          field: 'comments',
          value: {
            id: 'mock_comment_998877',
            text: '와, 오늘 AI 트렌드 요약 진짜 최고네! 앤스로픽 팁 유익하다.',
            media_id: mediaId || 'mock_media_id_999999'
          }
        }]
      }]
    };

    try {
      const { handleWebhookChange } = require('./lib/publishing/threads_api');
      await handleWebhookChange(mockPayload);
    } catch (e) {
      log.err(`모의 웹훅 테스트 실패: ${e.message}`);
    }
  }, 3000);
};


// ==============================================================================
// 🌟 LAYER 7: 메인 파이프라인 실행 스케줄러 및 오케스트레이터
// ==============================================================================

/**
 * AI 트렌드 큐레이션 및 공식 API 발행 파이프라인 (v3.0) 통합 실행
 */
const main = async () => {
  log.divider();
  log.step('🚀 [PRD v3.0] API-Driven 자동화 파이프라인 가동 개시...');
  
  // 시스템 실시간 타임스탬프 로깅 및 타겟 데이트 크로스체크 데코레이션
  const now = new Date();
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  
  log.info(`[시스템 시간 실시간 감지] 현재 서버 시각: ${now.toLocaleString()}`);
  log.info(`[자동 계산 수집 타겟 범위] D-1 어제 날짜: ${yesterday.toISOString().split('T')[0]}`);
  log.divider();

  try {
    // 1. 데이터 수집 단계 (독립 병렬, 에러 격리 탑재)
    // 참고: Apify 기반 X/Threads 수집은 ingest_raw_posts 스킬로 이관되어 병행 운용 가능
    const rawData = await runIngestionPipeline();

    // 2. 데이터 가공 및 정규화 (에이전트 스킬 수행 안내)
    await runCurationPipeline(rawData);

    // 3. Threads 공식 API 연동 발행 (큐레이션 결과물이 있을 때 별도 스킬화 권장)
    log.info('큐레이션 결과 발행은 에이전트를 통해 매뉴얼/스킬 기반으로 수행됩니다.');
    const mediaId = 'manual_mode_media_id';

    // 4. 실시간 댓글 감지용 웹훅 서버 가동
    initWebhookLifecycle();

    // 5. 로컬 모의 실시간 웹훅 댓글 반응 시뮬레이션 실행
    await simulateWebhookEvent(mediaId);

    // 실행 모드 대기 분기
    if (RUN_MODE === '2') {
      log.divider();
      log.ok('RUN_MODE=2 완료 기조: 즉시 종료를 처리합니다.');
      process.exit(0);
    } else {
      log.info('에이전트가 실시간 Webhook 대기 모드로 상주합니다. (종료: Ctrl + C)');
    }

  } catch (error) {
    log.err(`통합 파이프라인 오류: ${error.message}`);
    process.exit(1);
  }
};

// 최상위 핸들러
main().catch(error => {
  log.err(`애플리케이션 메인 크래시: ${error.message}`);
  process.exit(1);
});
