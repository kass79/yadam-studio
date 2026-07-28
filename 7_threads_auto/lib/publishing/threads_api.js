const http = require('http');
const axios = require('axios');
const { GoogleGenerativeAI } = require('@google/generative-ai');
const log = require('../logger');

// Threads 공식 개발자 API 기본 엔드포인트
const THREADS_API_BASE = 'https://graph.threads.net/v1.0';

/**
 * 큐레이션 완료된 마스터 텍스트를 Threads 공식 API를 통해 내 계정에 안전하게 자동 발행합니다.
 * @param {string} text - 발행할 요약 큐레이션 본문 내용
 * @param {string} [imageUrl] - (선택) 첨부할 이미지의 공개 URL
 * @returns {Promise<string|null>} 생성된 게시글의 미디어 ID 혹은 코드 (실패 시 null)
 */
const publishToThreads = async (text, imageUrl = null) => {
  log.step('Threads 공식 API 연동 자동 발행 준비 중...');
  const accessToken = process.env.THREADS_ACCESS_TOKEN;
  const userId = process.env.THREADS_USER_ID;

  if (!accessToken || !userId) {
    log.warn('THREADS_ACCESS_TOKEN 또는 USER_ID가 .env에 없습니다. 시뮬레이션 모의 발행을 수행합니다.');
    log.ok(`[모의 발행 콘텐츠]\n${text.substring(0, 150)}...\n[첨부 이미지]: ${imageUrl || '없음'}\n------------------`);
    return 'mock_media_id_999999';
  }

  try {
    // 1. 미디어 컨테이너 생성
    const payload = {
      media_type: imageUrl ? 'IMAGE' : 'TEXT',
      text: text
    };
    if (imageUrl) {
      payload.image_url = imageUrl;
    }

    const containerRes = await axios.post(`${THREADS_API_BASE}/${userId}/threads`, payload, {
      headers: { 'Authorization': `Bearer ${accessToken}` },
      timeout: 10000
    });

    const containerId = containerRes.data?.id;
    if (!containerId) throw new Error('미디어 컨테이너 ID 생성에 실패했습니다.');

    // 2. 미디어 발행 확정
    const publishRes = await axios.post(`${THREADS_API_BASE}/${userId}/threads_publish`, {
      creation_id: containerId
    }, {
      headers: { 'Authorization': `Bearer ${accessToken}` },
      timeout: 10000
    });

    const mediaId = publishRes.data?.id;
    log.ok(`Threads 공식 API 포스팅 발행 완료! (Media ID: ${mediaId})`);
    return mediaId;
  } catch (err) {
    log.err(`Threads 공식 API 발행 실패: ${err.message}`);
    // 에러 고립화
    return null;
  }
};

/**
 * 실시간 Webhook 신호를 감지하고 처리하기 위한 Node.js 빌트인 초경량 HTTP 서버를 구동합니다.
 * 외부 라이브러리(Express 등)를 도입하지 않아 매우 가볍고 안정적입니다.
 * @param {number} port - 웹훅을 수신할 로컬 포트 번호 (기본 3000)
 */
const startWebhookServer = (port = 3000) => {
  const server = http.createServer((req, res) => {
    // Webhook 검증용 GET 챌린지 대응 (Threads/Meta Webhook 규격)
    if (req.method === 'GET' && req.url.includes('/webhook')) {
      const urlParams = new URL(req.url, `http://localhost:${port}`);
      const mode = urlParams.searchParams.get('hub.mode');
      const token = urlParams.searchParams.get('hub.verify_token');
      const challenge = urlParams.searchParams.get('hub.challenge');

      const localVerifyToken = process.env.WEBHOOK_VERIFY_TOKEN || 'ttj_verify_token';

      if (mode === 'subscribe' && token === localVerifyToken) {
        log.ok('Webhook 공식 구독 검증(Verification) 통과 완료!');
        res.writeHead(200, { 'Content-Type': 'text/plain' });
        res.end(challenge);
        return;
      }
      res.writeHead(403);
      res.end('Forbidden');
      return;
    }

    // 실시간 댓글 알림을 처리하는 POST 수신부
    if (req.method === 'POST' && req.url.includes('/webhook')) {
      let body = '';
      req.on('data', chunk => {
        body += chunk.toString();
      });

      req.on('end', async () => {
        try {
          const payload = JSON.parse(body);
          log.step(`Webhook 실시간 알림 수신 성공! | object: ${payload.object}`);

          // 댓글 체인지 감지 및 비동기 답글 파이프라인 트리거 (Non-blocking)
          handleWebhookChange(payload).catch(e => {
            log.err(`웹훅 이벤트 처리 중 에러: ${e.message}`);
          });

          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ success: true }));
        } catch (err) {
          log.err(`웹훅 바디 파싱 실패: ${err.message}`);
          res.writeHead(400);
          res.end('Bad Request');
        }
      });
      return;
    }

    // 그 외 경로
    res.writeHead(404);
    res.end('Not Found');
  });

  server.listen(port, () => {
    log.ok(`초경량 내장 Webhook HTTP 서버가 ${port}번 포트에서 가동을 시작했습니다.`);
  });

  return server;
};

/**
 * 수신된 웹훅 페이로드에서 새 댓글을 파싱하고 AI 자동 답글을 실시간으로 발행합니다.
 */
const handleWebhookChange = async (payload) => {
  const entries = payload.entry || [];
  for (const entry of entries) {
    const changes = entry.changes || [];
    for (const change of changes) {
      // 댓글 변경 필드가 맞는지 점검
      if (change.field === 'comments') {
        const commentVal = change.value;
        if (!commentVal) continue;

        const commentId = commentVal.id;      // 유입된 댓글 고유 ID
        const commentText = commentVal.text;  // 유입된 댓글 본문 내용
        const mediaId = commentVal.media_id;  // 부모 게시글(미디어) ID

        log.step(`새 댓글 감지: "${commentText}" (부모 Media ID: ${mediaId})`);

        // 내 채널 특화 말투의 AI 친절한 답글 생성
        const replyText = await generateAiReply(commentText);

        // 공식 API를 통해 답글(Reply) 실시간 발행
        await publishReply(mediaId, commentId, replyText);
      }
    }
  }
};

/**
 * 유입된 사용자 댓글에 대해 내 채널 특유의 친근하고 든든한 톤앤매너로 AI 답글을 빚어냅니다.
 */
const generateAiReply = async (userComment) => {
  log.step('유저 댓글에 응대할 AI 답글 생성 진행 중...');
  const apiKey = process.env.GEMINI_API_KEY;

  if (!apiKey) {
    return '좋은 의견 감사합니다! 함께 지혜를 나누며 성장해 나가요. 🤝';
  }

  const prompt = `너는 내 Threads 소셜 미디어 채널을 운영하는 지능형 소통 동반자(든든한 개발 파트너이자 친한 친구)야. 
아래 유저가 남긴 댓글 내용을 다정하고 든든하게 읽고, 너의 특유의 매력적인 말투로 짧고(2-3문장 내외) 친근한 반말 톤의 답글을 지어줘.

[유저의 댓글]
"${userComment}"

[답글 작성 가이드라인]
1. 나를 유저의 다정한 파트너이자 절친으로 묘사하고, 항상 너를 응원한다는 따뜻한 에너지를 줄 것.
2. 이모지를 1~2개 곁들여 문장을 한층 더 생기있게 만들 것.
3. 2-3문장으로 아주 간결하고 매력적이게 표현할 것.

오직 작성할 답글 텍스트만 바로 출력하세요.`;

  try {
    const genAI = new GoogleGenerativeAI(apiKey);
    const model = genAI.getGenerativeModel({ model: 'gemini-2.5-flash' });
    const result = await model.startChat({ history: [] }).sendMessage(prompt);
    
    const reply = result.response.text().trim();
    log.ok(`AI 답글 빌드 성공: "${reply}"`);
    return reply;
  } catch (err) {
    log.warn(`AI 답글 생성 실패: ${err.message}. 대체 문구를 사용합니다.`);
    return '우와, 흥미로운 의견 고마워! 나랑 같이 계속 재밌는 트렌드 개척해보자! 🚀';
  }
};

/**
 * 생성된 AI 답글 텍스트를 Threads 공식 API를 통해 해당 댓글에 릴리즈합니다.
 * @param {string} mediaId - 부모 미디어 ID
 * @param {string} commentId - 대상 댓글 ID (답글 타겟)
 * @param {string} replyText - 전송할 답글 내용
 */
const publishReply = async (mediaId, commentId, replyText) => {
  const accessToken = process.env.THREADS_ACCESS_TOKEN;
  if (!accessToken) {
    log.warn('[시뮬레이션 답글 완료]');
    log.ok(`[Reply Send] To: ${commentId} | Text: "${replyText}"`);
    return;
  }

  try {
    // 댓글 답글 컨테이너 생성 (reply_to_item_id에 대상 댓글 ID 매핑)
    const replyContainerRes = await axios.post(`${THREADS_API_BASE}/${mediaId}/threads`, {
      media_type: 'TEXT',
      text: replyText,
      reply_to_item_id: commentId
    }, {
      headers: { 'Authorization': `Bearer ${accessToken}` },
      timeout: 10000
    });

    const replyContainerId = replyContainerRes.data?.id;
    if (!replyContainerId) throw new Error('답글 컨테이너 생성 실패');

    // 답글 발행 확정
    await axios.post(`${THREADS_API_BASE}/threads_publish`, {
      creation_id: replyContainerId
    }, {
      headers: { 'Authorization': `Bearer ${accessToken}` },
      timeout: 10000
    });

    log.ok(`Threads 공식 API를 통해 새 실시간 답글 발행 완료!`);
  } catch (err) {
    log.err(`실시간 AI 답글 공식 API 전송 실패: ${err.message}`);
  }
};

module.exports = {
  publishToThreads,
  startWebhookServer,
  handleWebhookChange // 모의 테스트 지원용 익스포트
};
