const axios = require('axios');
const fs = require('fs');
const path = require('path');
const log = require('../logger');

/**
 * 폴더 및 파일명에 쓸 YYMMDD_시간 포맷 구하기 (예: 오후 1시면 1300)
 */
const getFormattedDateTime = () => {
  const now = new Date();
  const yy = String(now.getFullYear()).slice(-2);
  const mm = String(now.getMonth() + 1).padStart(2, '0');
  const dd = String(now.getDate()).padStart(2, '0');
  const hh = String(now.getHours()).padStart(2, '0');
  const min = String(now.getMinutes()).padStart(2, '0');
  return `${yy}${mm}${dd}_${hh}${min}`;
};


/**
 * Apify Actor의 실행이 성공적으로 끝날 때까지 주기적으로 상태를 폴링하여 대기합니다.
 * @param {string} runId - Actor 실행 ID
 * @param {string} token - Apify API 토큰
 * @returns {Promise<string>} 완료된 Dataset ID
 */
const waitForApifyRun = async (runId, token) => {
  const maxRetries = 40; // 3초씩 최대 2분 대기
  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await axios.get(`https://api.apify.com/v2/actor-runs/${runId}`, {
        params: { token },
        timeout: 5000
      });
      const status = response.data?.data?.status;
      log.step(`Apify Actor [${runId}] 상태 확인 중... (${status})`);

      if (status === 'SUCCEEDED') {
        const datasetId = response.data?.data?.defaultDatasetId;
        if (!datasetId) throw new Error('성공했으나 defaultDatasetId를 찾지 못했습니다.');
        return datasetId;
      }

      if (['FAILED', 'ABORTED', 'TIMED-OUT'].includes(status)) {
        throw new Error(`Actor 실행이 비정상 종료되었습니다: ${status}`);
      }
    } catch (e) {
      if (e.message.includes('비정상 종료')) throw e;
      log.warn(`폴링 중 일시적 오류: ${e.message}`);
    }
    await new Promise(r => setTimeout(r, 3000));
  }
  throw new Error('Apify Actor 실행 대기 시간 초과(Timeout)');
};

/**
 * X(Twitter) 및 Threads의 메인스트림 트렌드 게시글을 Apify Scraper를 연동해 실시간 수집합니다.
 * D-1(어제) 기준 좋아요(Likes) 내림차순 정렬 상위 5개씩 (총 10개) 추출합니다.
 * 에러 고립화(Graceful Degradation)에 따라, 오류 발생 시 빈 배열을 반환합니다.
 */
const fetchMainstreamTrends = async () => {
  log.step('X(Twitter) 메인스트림 트렌드 수집 시작...');
  const results = [];
  let formattedX = [];
  let formattedInfluencerX = [];

  const tokenX = process.env.APIFY_TOKEN_X;
  const tokenThreads = process.env.APIFY_TOKEN_THREADS;

  // 어제 날짜 계산 (D-1 기준, YYYY-MM-DD 포맷)
  const yesterday = new Date();
  yesterday.setDate(yesterday.getDate() - 1);
  const targetDate = yesterday.toISOString().split('T')[0];

  const today = new Date();
  const todayDate = today.toISOString().split('T')[0];
  log.step(`타겟 조회 날짜 (D-1): ${targetDate} ~ 오늘: ${todayDate}`);

  // 1. X(Twitter) Apify Scraper 연동
  if (!tokenX) {
    log.warn('APIFY_TOKEN_X가 .env에 없습니다. X 수집 모의 Fallback을 가동합니다.');
    results.push(...getMockX());
  } else {
    try {
      log.step('Apify X Scraper Actor 기동 중...');
      const xRunRes = await axios.post(`https://api.apify.com/v2/acts/danek~twitter-scraper-ppr/runs?token=${tokenX}`, {
        max_posts: 20,
        query: `(AI agent) min_faves:100 -filter:replies since:${targetDate} until:${todayDate}`
      }, { timeout: 30000 });

      const runId = xRunRes.data?.data?.id;
      if (!runId) throw new Error('Apify X Run ID 생성에 실패했습니다.');

      // 실행 완료 시까지 대기 후 데이터셋 ID 추출
      const datasetId = await waitForApifyRun(runId, tokenX);

      // 데이터셋 아이템 가져오기
      const datasetItemsRes = await axios.get(`https://api.apify.com/v2/datasets/${datasetId}/items`, {
        params: { token: tokenX },
        timeout: 30000
      });

      const xPosts = datasetItemsRes.data || [];
      formattedX = xPosts
        .filter(post => {
          const screenName = post.screen_name || post.user_info?.screen_name || post.user?.screenName || post.username || 'unknown';
          const isSelfReply = post.in_reply_to_screen_name && post.in_reply_to_screen_name === screenName;

          // 타인에게 보낸 단순 멘션 답글은 제외
          if (post.in_reply_to_screen_name && !isSelfReply) return false;

          const likes = parseInt(post.favorites || post.likeCount || post.favoriteCount || 0, 10);
          // 자기 스레드 대댓글이 아니면서 좋아요가 10개 미만인 경우 제외
          if (!isSelfReply && likes < 10) return false;
          return true;
        })
        .map(post => {
          // Apify 스키마 구조에 따른 동적 바인딩
          const likes = parseInt(post.favorites || post.likeCount || post.favoriteCount || 0, 10);
          const comments = parseInt(post.replies || post.replyCount || 0, 10);
          const screenName = post.screen_name || post.user_info?.screen_name || post.user?.screenName || post.username || 'unknown';
          
          let content = post.text || post.fullText || '';
          if (post.quoted && (post.quoted.text || post.quoted.fullText)) {
            content += '\n\n[인용된 원본 트윗]\n' + (post.quoted.text || post.quoted.fullText);
          }

          return {
            source: 'X',
            author: screenName,
            content: content,
            url: post.url || (post.tweet_id ? `https://x.com/${screenName}/status/${post.tweet_id}` : `https://x.com/${screenName}/status/${post.id}`),
            published_at: post.created_at ? new Date(post.created_at).toISOString() : (post.createdAt ? new Date(post.createdAt).toISOString() : new Date().toISOString()),
            metrics: { likes, comments }
          };
        })
        .sort((a, b) => b.metrics.likes - a.metrics.likes)
        .slice(0, 20);

      results.push(...formattedX);
      log.ok(`Apify X Scraper 연동 수집 완료 (${formattedX.length}개 추출)`);
    } catch (err) {
      log.warn(`X Apify 수집 모듈 에러 고립 (Graceful Degradation): ${err.message}`);
      formattedX = getMockX();
      results.push(...formattedX);
    }
  }

  // 2. X Influencer Apify Scraper 연동 (Threads 대신 대체)
  if (!tokenThreads) {
    log.warn('APIFY_TOKEN_THREADS가 .env에 없습니다. X Influencer 수집 모의 Fallback을 가동합니다.');
    results.push(...getMockInfluencerX());
  } else {
    try {
      log.step('Apify X Influencer Scraper Actor 기동 중...');
      const influencerRunRes = await axios.post(`https://api.apify.com/v2/acts/danek~twitter-scraper-ppr/runs?token=${tokenThreads}`, {
        max_posts: 20,
        search_type: 'Latest',
        query: `from:alexalbert__ OR from:OfficialLoganK OR from:hwchase17 OR from:mckaywrigley OR from:swyx OR from:mreflow -filter:replies min_faves:10 since:${targetDate}`
      }, { timeout: 30000 });

      const runId = influencerRunRes.data?.data?.id;
      if (!runId) throw new Error('Apify X Influencer Run ID 생성에 실패했습니다.');

      // 실행 완료 시까지 대기 후 데이터셋 ID 추출
      const datasetId = await waitForApifyRun(runId, tokenThreads);

      // 데이터셋 아이템 가져오기
      const datasetItemsRes = await axios.get(`https://api.apify.com/v2/datasets/${datasetId}/items`, {
        params: { token: tokenThreads },
        timeout: 30000
      });

      const xPosts = datasetItemsRes.data || [];
      formattedInfluencerX = xPosts
        .filter(post => {
          const screenName = post.screen_name || post.user_info?.screen_name || post.user?.screenName || post.username || 'unknown';
          const isSelfReply = post.in_reply_to_screen_name && post.in_reply_to_screen_name === screenName;

          // 타인에게 보낸 단순 멘션 답글은 제외
          if (post.in_reply_to_screen_name && !isSelfReply) return false;

          const likes = parseInt(post.favorites || post.likeCount || post.favoriteCount || 0, 10);
          // 자기 스레드 대댓글이 아니면서 좋아요가 10개 미만인 경우 제외
          if (!isSelfReply && likes < 10) return false;
          return true;
        })
        .map(post => {
          const likes = parseInt(post.favorites || post.likeCount || post.favoriteCount || 0, 10);
          const comments = parseInt(post.replies || post.replyCount || 0, 10);
          const screenName = post.screen_name || post.user_info?.screen_name || post.user?.screenName || post.username || 'unknown';
          
          let content = post.text || post.fullText || '';
          if (post.quoted && (post.quoted.text || post.quoted.fullText)) {
            content += '\n\n[인용된 원본 트윗]\n' + (post.quoted.text || post.quoted.fullText);
          }

          return {
            source: 'X_Influencer',
            author: screenName,
            content: content,
            url: post.url || (post.tweet_id ? `https://x.com/${screenName}/status/${post.tweet_id}` : `https://x.com/${screenName}/status/${post.id}`),
            published_at: post.created_at ? new Date(post.created_at).toISOString() : (post.createdAt ? new Date(post.createdAt).toISOString() : new Date().toISOString()),
            metrics: { likes, comments }
          };
        })
        .sort((a, b) => b.metrics.likes - a.metrics.likes)
        .slice(0, 20);

      results.push(...formattedInfluencerX);
      log.ok(`Apify X Influencer Scraper 연동 수집 완료 (${formattedInfluencerX.length}개 추출)`);
    } catch (err) {
      log.warn(`X Influencer Apify 수집 모듈 에러 고립 (Graceful Degradation): ${err.message}`);
      formattedInfluencerX = getMockInfluencerX();
      results.push(...formattedInfluencerX);
    }
  }

  // 3. 마크다운 결과 파일 저장 자동화 (사용자 규칙)
  try {
    const dateTimeStr = getFormattedDateTime();
    const outputDirPath = path.join(process.cwd(), 'output', dateTimeStr);

    if (!fs.existsSync(outputDirPath)) {
      fs.mkdirSync(outputDirPath, { recursive: true });
    }

    // X Markdown 작성
    const xMdHeader = `# 🐦 X(Twitter) Raw 수집 데이터 (${dateTimeStr})\n\n` +
      `- **수집 일시**: ${new Date().toLocaleString()}\n` +
      `- **총 수집 개수**: ${formattedX.length}개\n\n` +
      `---\n\n`;
    const xMdBody = formattedX.map((post, idx) => {
      return `## [${idx + 1}] @${post.author} (좋아요: ${post.metrics?.likes || 0} | 댓글: ${post.metrics?.comments || 0})\n` +
        `- **작성일**: ${post.published_at}\n` +
        `- **URL**: [링크 이동](${post.url})\n` +
        `- **본문 내용**:\n` +
        `> ${post.content.replace(/\n/g, '\n> ')}\n\n` +
        `---\n\n`;
    }).join('');

    fs.writeFileSync(path.join(outputDirPath, `twitter_raw_${dateTimeStr}.md`), xMdHeader + xMdBody, 'utf8');
    log.ok(`X raw 데이터 저장 완료: output/${dateTimeStr}/twitter_raw_${dateTimeStr}.md`);

    // X Influencer Markdown 작성
    const influencerMdHeader = `# 🧑‍💻 X(Twitter) Influencer Raw 수집 데이터 (${dateTimeStr})\n\n` +
      `- **수집 일시**: ${new Date().toLocaleString()}\n` +
      `- **총 수집 개수**: ${formattedInfluencerX.length}개\n\n` +
      `---\n\n`;
    const influencerMdBody = formattedInfluencerX.map((post, idx) => {
      return `## [${idx + 1}] @${post.author} (좋아요: ${post.metrics?.likes || 0} | 댓글: ${post.metrics?.comments || 0})\n` +
        `- **작성일**: ${post.published_at}\n` +
        `- **URL**: [링크 이동](${post.url})\n` +
        `- **본문 내용**:\n` +
        `> ${post.content.replace(/\n/g, '\n> ')}\n\n` +
        `---\n\n`;
    }).join('');

    fs.writeFileSync(path.join(outputDirPath, `twitter_influencer_raw_${dateTimeStr}.md`), influencerMdHeader + influencerMdBody, 'utf8');
    log.ok(`X Influencer raw 데이터 저장 완료: output/${dateTimeStr}/twitter_influencer_raw_${dateTimeStr}.md`);

  } catch (err) {
    log.err(`결과 마크다운 파일 저장 실패: ${err.message}`);
  }

  return results;
};

/**
 * X 로컬 대체 모의 데이터
 */
const getMockX = () => [
  {
    source: 'X',
    author: 'ai_innovator',
    content: 'OpenAI has just announced the release of GPT-5. The reasoning and multi-modal pipeline is absolutely stunning. #AI',
    url: 'https://x.com/ai_innovator/status/1234567890',
    published_at: new Date().toISOString(),
    metrics: { likes: 4500, comments: 820 }
  }
];

/**
 * X Influencer 로컬 대체 모의 데이터
 */
const getMockInfluencerX = () => [
  {
    source: 'X_Influencer',
    author: 'swyx',
    content: 'The new AI agents are crazy good.',
    url: 'https://x.com/swyx/status/1234567891',
    published_at: new Date().toISOString(),
    metrics: { likes: 3000, comments: 150 }
  }
];

module.exports = {
  fetchMainstreamTrends
};
