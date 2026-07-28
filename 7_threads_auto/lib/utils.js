const axios = require('axios');
const fs = require('fs');
const fsPromises = fs.promises;
const path = require('path');
require('dotenv').config({ path: path.join(__dirname, '..', '.env') });

const CURRENT_DIR = path.join(__dirname, '..');

// .env에서 사용자 정보 읽기
const getUserCredentials = () => {
  const fullEmail = process.env.EMAIL || '';
  const password = process.env.PASSWORD || '';
  const nickName = process.env.NICK_NAME || '';
  const id = fullEmail.split('@')[0];
  return { id, fullEmail, password, nickName };
};

// 쿠키 문자열 생성
const buildCookieString = (cookies) =>
  cookies.map(c => `${c.name}=${c.value}`).join('; ');

// threads.com GET 요청으로 닉네임 + fb_dtsg 동시 추출
const fetchSessionInfo = async (cookieString) => {
  const response = await axios.get('https://www.threads.com/', {
    headers: {
      'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
      'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
      'accept-language': 'ko-KR,ko;q=0.9',
      'cookie': cookieString,
    },
    maxRedirects: 5,
  });

  const html = response.data;

  const dtsgMatch = html.match(/DTSGInitialData",[^{]*{"token":"([^"]+)"/);
  const fb_dtsg = dtsgMatch ? dtsgMatch[1] : null;

  const lsdMatch = html.match(/"LSD",\[\],\{"token":"([^"]+)"/);
  const lsd = lsdMatch ? lsdMatch[1] : null;

  const usernameMatch = html.match(/"viewer":\{[^}]*"username":"([^"]+)"/);
  const nickName = usernameMatch ? usernameMatch[1] : null;

  const avMatch = html.match(/"viewer":\{"id":"(\d+)"/);
  const av = avMatch ? avMatch[1] : null;

  const bloksMatch = html.match(/"bloks_version_id":"([a-f0-9]+)"/);
  const bloksVersionId = bloksMatch ? bloksMatch[1] : null;

  return { fb_dtsg, lsd, nickName, av, bloksVersionId };
};

// .env의 NICK_NAME 업데이트
const saveNickName = async (nickName) => {
  const envFile = path.join(CURRENT_DIR, '.env');
  const data = await fsPromises.readFile(envFile, 'utf8');
  const lines = data.split('\n');
  const idx = lines.findIndex(l => l.trim().startsWith('NICK_NAME='));
  const updated = idx === -1
    ? [...lines, `NICK_NAME=${nickName}`]
    : lines.map((l, i) => i === idx ? `NICK_NAME=${nickName}` : l);
  await fsPromises.writeFile(envFile, updated.join('\n'));
  process.env.NICK_NAME = nickName;
};

module.exports = {
  getUserCredentials,
  buildCookieString,
  fetchSessionInfo,
  saveNickName,
};
