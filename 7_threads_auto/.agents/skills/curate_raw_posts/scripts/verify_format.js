const fs = require('fs');
const path = require('path');

const targetFile = process.argv[2];

if (!targetFile) {
  console.error('검증할 대상 마크다운 파일 경로를 입력하세요.');
  process.exit(1);
}

if (!fs.existsSync(targetFile)) {
  console.error(`파일이 존재하지 않습니다: ${targetFile}`);
  process.exit(1);
}

const content = fs.readFileSync(targetFile, 'utf8');
const lines = content.split('\n');

let hasError = false;

// 1. ** 강조 기호 검출 (굵은 글씨 금지)
if (content.includes('**')) {
  console.error('❌ [오류] 마크다운 굵은 글씨 강조 기호(**)가 감지되었습니다. 원형 텍스트로만 작성해야 합니다.');
  hasError = true;
}

// 2. 해시태그 검출 (마크다운 제목 기호인 # 뒤에 공백이 있는 경우는 제외하고, 단어 앞에 붙은 #태그 검출)
// 정규식 설명: 공백이나 줄바꿈 뒤에 #이 오고 바로 단어가 이어지는 경우 (예: #태그)
const hashtagRegex = /(?:^|\s)#[^\s#]+/g;
const hashtags = content.match(hashtagRegex);
if (hashtags && hashtags.length > 0) {
  // 실제 마크다운 제목 포맷인지 한 번 더 걸러줌 (보통 헤더는 # 뒤에 스페이스가 있으므로 위 정규식에서 이미 걸러지긴 함)
  const realHashtags = hashtags.filter(tag => !tag.startsWith('##') && !tag.includes('# '));
  if (realHashtags.length > 0) {
    console.error(`❌ [오류] 해시태그가 감지되었습니다: ${realHashtags.join(', ')}`);
    hasError = true;
  }
}

// 3. 참고 URL 형식 검출
// 포스트별로 마지막에 '참고 URL : http' 양식이 있는지 검증. 
// 보통 파일 전체 맨 밑이나 각 포스트 블록의 맨 밑.
// 여기서는 가장 간단하게 파일 내용 어딘가에 "참고 URL : http" 형태가 있는지 확인
const urlRegex = /참고 URL :\s*https?:\/\//g;
if (!urlRegex.test(content)) {
  console.error('❌ [오류] "참고 URL : https://..." 양식이 누락되었거나 형식이 올바르지 않습니다.');
  hasError = true;
}

if (hasError) {
  process.exit(1);
} else {
  console.log('✅ [검증 통과] 마크다운 포맷 제약사항(강조 금지, 해시태그 금지, 참고 URL 형식)을 모두 준수하였습니다.');
  process.exit(0);
}
