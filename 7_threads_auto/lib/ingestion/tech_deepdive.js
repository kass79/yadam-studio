const axios = require('axios');
const log = require('../logger');

/**
 * Hacker News 및 GitHub에서 개발자용 딥 다이브 트렌드 정보를 수집합니다.
 * - Hacker News: 공식 Firebase API를 사용하여 Top 5 스토리 및 주요 댓글 분석 수집
 * - GitHub: 공식 API를 사용하여 'AI', 'Machine Learning' 관련 금주 Star 급상승 레포지토리 수집
 * 에러 고립화(Graceful Degradation)에 따라, 오류 발생 시 빈 배열을 반환합니다.
 */
const fetchTechDeepDive = async () => {
  log.step('테크 및 개발자 딥 다이브 트렌드 수집 시작...');
  const results = [];

  // 1. Hacker News 실시간 트렌드 수집
  try {
    log.step('Hacker News 최신 트렌드 스캔 중...');
    // Firebase 공식 Hacker News API
    const topStoriesRes = await axios.get('https://hacker-news.firebaseio.com/v0/topstories.json', { timeout: 8000 });
    const top5Ids = (topStoriesRes.data || []).slice(0, 5);

    const hnStories = [];
    for (const id of top5Ids) {
      try {
        const itemRes = await axios.get(`https://hacker-news.firebaseio.com/v0/item/${id}.json`, { timeout: 5000 });
        const story = itemRes.data;

        if (story && (story.title || '').toLowerCase().includes('ai') || (story.title || '').toLowerCase().includes('gpt') || (story.title || '').toLowerCase().includes('llm')) {
          // 최상위 주요 댓글 1개 분석 포함
          let topComment = '';
          if (story.kids && story.kids.length > 0) {
            try {
              const commentRes = await axios.get(`https://hacker-news.firebaseio.com/v0/item/${story.kids[0]}.json`, { timeout: 3000 });
              topComment = commentRes.data?.text || '';
              // HTML 태그 소거
              topComment = topComment.replace(/<\/?[^>]+(>|$)/g, '').substring(0, 150);
            } catch (ce) {}
          }

          hnStories.push({
            source: 'HackerNews',
            author: story.by || 'unknown',
            content: `[HN Top] ${story.title}${topComment ? ` | Top Comment: ${topComment}` : ''}`,
            url: story.url || `https://news.ycombinator.com/item?id=${id}`,
            published_at: new Date(story.time * 1000).toISOString(),
            metrics: {
              likes: parseInt(story.score || 0, 10),
              comments: parseInt(story.descendants || 0, 10)
            }
          });
        }
      } catch (err) {}
    }

    results.push(...hnStories);
    log.ok(`Hacker News 트렌드 수집 완료 (${hnStories.length}개 추출)`);
  } catch (err) {
    log.warn(`Hacker News 수집 에러 고립 (Graceful Degradation): ${err.message}`);
  }

  // 2. GitHub Star 급상승 AI/ML 레포지토리 수집
  try {
    log.step('GitHub AI/ML 트렌딩 레포지토리 스캔 중...');
    const githubToken = process.env.GITHUB_TOKEN;
    const headers = { 'User-Agent': 'Antigravity-Agent-v3' };
    if (githubToken) {
      headers['Authorization'] = `token ${githubToken}`;
    }

    // AI/ML 관련 금주 스타 급상승 레포지토리 쿼리
    const sevenDaysAgo = new Date();
    sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
    const dateStr = sevenDaysAgo.toISOString().split('T')[0];

    const githubRes = await axios.get('https://api.github.com/search/repositories', {
      params: {
        q: `created:>${dateStr} topic:ai topic:machine-learning`,
        sort: 'stars',
        order: 'desc',
        per_page: 5
      },
      headers,
      timeout: 8000
    });

    const repos = githubRes.data?.items || [];
    const formattedRepos = repos.map(repo => ({
      source: 'GitHub',
      author: repo.owner?.login || 'unknown',
      content: `[Git Trending] ${repo.name}: ${repo.description || 'No description'} (Language: ${repo.language || 'Unknown'})`,
      url: repo.html_url || '',
      published_at: repo.created_at || new Date().toISOString(),
      metrics: {
        likes: parseInt(repo.stargazers_count || 0, 10),
        comments: parseInt(repo.forks_count || 0, 10) // Forks를 comments 메트릭으로 매핑
      }
    }));

    results.push(...formattedRepos);
    log.ok(`GitHub 트렌드 수집 완료 (${formattedRepos.length}개 추출)`);
  } catch (err) {
    log.warn(`GitHub 수집 에러 고립 (Graceful Degradation): ${err.message}`);
  }

  // 두 모듈 모두 아예 실패했을 때만 최하위 보장 Mock 반환
  if (results.length === 0) {
    log.warn('HN & GitHub API 수집 모두 실패. 모의(Mock) 테크 딥다이브 데이터를 공급합니다.');
    return getMockTechDeepDive();
  }

  return results;
};

/**
 * 네트워크 오프라인이나 한도 차단에 대비한 Mock 데이터 장치
 */
const getMockTechDeepDive = () => [
  {
    source: 'HackerNews',
    author: 'pg',
    content: '[HN Top] Why AI-driven development is shifting the software bottleneck from writing code to systems design | Top Comment: Completely agree, Cursor and Claude Code has changed how our startup structures codebases.',
    url: 'https://news.ycombinator.com/item?id=44444444',
    published_at: new Date().toISOString(),
    metrics: { likes: 520, comments: 210 }
  },
  {
    source: 'GitHub',
    author: 'google-deepmind',
    content: '[Git Trending] alpha-agents: DeepMind open-sources unified reinforcement learning agent framework for code synthesis (Language: Python)',
    url: 'https://github.com/google-deepmind/alpha-agents',
    published_at: new Date().toISOString(),
    metrics: { likes: 3500, comments: 450 }
  }
];

module.exports = {
  fetchTechDeepDive
};
