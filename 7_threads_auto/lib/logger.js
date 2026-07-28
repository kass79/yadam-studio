const c = {
  reset:   '\x1b[0m',
  bold:    '\x1b[1m',
  dim:     '\x1b[2m',
  green:   '\x1b[32m',
  yellow:  '\x1b[33m',
  red:     '\x1b[31m',
  cyan:    '\x1b[36m',
  blue:    '\x1b[34m',
  gray:    '\x1b[90m',
  white:   '\x1b[97m',
};

const section = (title) => {
  const pad = 48 - title.length;
  const line = '─'.repeat(Math.max(pad, 2));
  console.log(`\n${c.bold}${c.blue}┌ ${title} ${line}${c.reset}`);
};

const ok  = (msg) => console.log(`${c.green}  ✓${c.reset} ${msg}`);
const warn = (msg) => console.log(`${c.yellow}  ⚠${c.reset} ${msg}`);
const err  = (msg) => console.error(`${c.red}  ✗${c.reset} ${c.bold}${msg}${c.reset}`);
const info = (msg) => console.log(`${c.cyan}  ℹ${c.reset} ${c.dim}${msg}${c.reset}`);
const step = (msg) => console.log(`    ${c.gray}→${c.reset} ${msg}`);

const action = (icon, label, success, detail = '') => {
  const status = success
    ? `${c.green}✓${c.reset}`
    : `${c.yellow}–${c.reset}`;
  const extra = detail ? `  ${c.dim}${detail}${c.reset}` : '';
  console.log(`   ${icon} ${c.white}${label.padEnd(10)}${c.reset} ${status}${extra}`);
};

const user = (name) =>
  console.log(`\n${c.bold}👤  @${name}${c.reset}`);

const post = (url) =>
  console.log(`    ${c.gray}${url}${c.reset}`);

const divider = () =>
  console.log(`${c.gray}${'─'.repeat(52)}${c.reset}`);

module.exports = { section, ok, warn, err, info, step, action, user, post, divider };
