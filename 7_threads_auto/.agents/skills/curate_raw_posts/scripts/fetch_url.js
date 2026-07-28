const axios = require('axios');

/**
 * HTML 문자열에서 script, style, 태그를 소거하여 순수 텍스트만 추출
 */
const cleanHtml = (html) => {
  if (!html) return '';
  let text = html.replace(/<(script|style)\b[^>]*>([\s\S]*?)<\/\1>/gi, '');
  text = text.replace(/<[^>]*>/g, ' ');
  text = text.replace(/\s+/g, ' ').trim();
  return text.slice(0, 3000); // 프롬프트 토큰 제약용 (3000자 제한)
};

const fetchUrlContent = async (url) => {
  if (!url) {
    console.error('URL이 제공되지 않았습니다.');
    process.exit(1);
  }
  
  try {
    const response = await axios.get(url, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
      },
      timeout: 5000
    });
    const cleanedText = cleanHtml(response.data);
    console.log(cleanedText);
  } catch (err) {
    console.error(`접속 오류 또는 딥리딩 실패: ${err.message}`);
    process.exit(1);
  }
};

const targetUrl = process.argv[2];
fetchUrlContent(targetUrl);
