const axios = require('axios');
const log = require('../logger');

// 모니터링할 핵심 오피니언 리더 계정 정의
const TARGET_LEADERS = [
  { id: 'OfficialLoganK', name: 'Logan Kilpatrick' },
  { id: 'alexalbert__', name: 'Alex Albert' },
  { id: 'mckaywrigley', name: 'McKay Wrigley' }
];

/**
 * 지정된 핵심 오피니언 리더들의 최신 타임라인 게시글을 추적 수집합니다.
 * D-1(어제)부터 현재 실시간까지의 작성분 중 계정당 최대 3개씩 추출합니다.
 * 에러 고립화(Graceful Degradation)에 따라, 오류 발생 시 빈 배열을 반환합니다.
 */
const fetchOpinionLeaderPosts = async () => {
  log.step('AI 오피니언 리더 모니터링 수집 시작...');
  const results = [];
  const rapidApiKey = process.env.RAPIDAPI_KEY;

  if (!rapidApiKey) {
    log.warn('RAPIDAPI_KEY가 .env에 없습니다. 모의(Mock) 오피니언 리더 데이터를 반환합니다.');
    return getMockOpinions();
  }

  // D-1 날짜 기준 계산
  const yesterday = new Date();
  yesterday.setDate(yesterday.getDate() - 1);

  for (const leader of TARGET_LEADERS) {
    try {
      log.step(`오피니언 리더 @${leader.id} 트래킹 중...`);
      const response = await axios.get('https://twitter-api45.p.rapidapi.com/user_tweets.php', {
        params: { username: leader.id },
        headers: {
          'x-rapidapi-key': rapidApiKey,
          'x-rapidapi-host': 'twitter-api45.p.rapidapi.com'
        },
        timeout: 10000
      });

      const tweets = response.data?.timeline || [];
      const leaderPosts = tweets
        .map(tweet => ({
          source: 'X',
          author: leader.id,
          content: tweet.text || '',
          url: `https://x.com/${leader.id}/status/${tweet.id}`,
          published_at: tweet.created_at ? new Date(tweet.created_at).toISOString() : new Date().toISOString(),
          metrics: {
            likes: parseInt(tweet.favorites_count || 0, 10),
            comments: parseInt(tweet.replies_count || 0, 10)
          }
        }))
        // D-1부터 현재 실시간 게시글 필터링
        .filter(post => {
          const postDate = new Date(post.published_at);
          return postDate >= yesterday;
        })
        .slice(0, 3); // 계정당 최대 3개 추출

      results.push(...leaderPosts);
      log.ok(`@${leader.id} 게시글 ${leaderPosts.length}개 추출 성공`);
    } catch (err) {
      log.warn(`오피니언 리더 @${leader.id} 모니터링 에러 고립 (Graceful Degradation): ${err.message}`);
    }
  }

  return results;
};

/**
 * API 한도 초과나 오프라인 환경 구동성을 담보하기 위한 모의(Mock) 데이터 공급 장치
 */
const getMockOpinions = () => [
  {
    source: 'X',
    author: 'OfficialLoganK',
    content: 'Google Gemini 2.5 Flash sets a new milestone in developer workflow. High concurrency multi-agent pipelines are now 2x faster with Antigravity.',
    url: 'https://x.com/OfficialLoganK/status/987654321',
    published_at: new Date().toISOString(),
    metrics: { likes: 3200, comments: 450 }
  },
  {
    source: 'X',
    author: 'alexalbert__',
    content: 'Anthropic Claude Code is not just a coding assistant; it is a full-featured agent environment that optimizes system prompts iteratively for best token usage.',
    url: 'https://x.com/alexalbert__/status/987654322',
    published_at: new Date().toISOString(),
    metrics: { likes: 2800, comments: 390 }
  },
  {
    source: 'X',
    author: 'mckaywrigley',
    content: 'Building prompt-driven software via Cursor/Codex. We are entering an era where system-level architectures are composed by AI orchestration agents.',
    url: 'https://x.com/mckaywrigley/status/987654323',
    published_at: new Date().toISOString(),
    metrics: { likes: 1900, comments: 280 }
  }
];

module.exports = {
  fetchOpinionLeaderPosts
};
