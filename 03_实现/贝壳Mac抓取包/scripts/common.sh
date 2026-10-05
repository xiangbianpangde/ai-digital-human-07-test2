#!/bin/bash
# Runtime uses only macOS system tools and the bundled official CLI.
set +x
set -euo pipefail
PACKAGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
SKILLS=(beike-buy beike-market beike-policy beike-rent beike-school beike-sell beike-decor)
CLI="$HOME/.local/bin/beike"

fail() { printf '\n错误：%s\n' "$1" >&2; exit "${2:-1}"; }
require_mac() { [ "$(/usr/bin/uname -s)" = Darwin ] || fail '此包仅支持 macOS。'; }
verify_package() {
  [ -f "$PACKAGE_ROOT/SHA256SUMS" ] || fail '缺少 SHA256SUMS，请重新完整解压。' 9
  (cd "$PACKAGE_ROOT" && /usr/bin/shasum -a 256 -c SHA256SUMS >/dev/null 2>&1) || fail '工具包文件缺失或校验不一致，已停止。请使用完整可信副本。' 9
}
require_cli() { [ -x "$CLI" ] || fail '尚未安装本机 CLI，请先运行 1-一键安装.command。' 1; }
native_arch() {
  local arch
  arch="$(/usr/bin/uname -m)"
  if [ "$arch" = arm64 ]; then printf 'arm64\n';
  elif [ "$arch" = x86_64 ]; then
    if [ "$(/usr/sbin/sysctl -n hw.optional.arm64 2>/dev/null || true)" = 1 ]; then printf 'arm64\n'; else printf 'amd64\n'; fi
  else fail "不支持的CPU架构：$arch"; fi
}
sha_file() { /usr/bin/shasum -a 256 "$1" | /usr/bin/awk '{print $1}'; }
json_tool() { /usr/bin/osascript -l JavaScript "$PACKAGE_ROOT/scripts/result.js" "$@"; }
api_check() {
  local verdict
  verdict="$(json_tool check "$1")" || { printf '无法解析CLI返回。\n' >&2; return 1; }
  if [ "$verdict" = OK ]; then return 0; fi
  printf '%s\n' "$verdict" >&2
  return 1
}
doctor_check() {
  local tmp code api key
  require_cli
  tmp="$(/usr/bin/mktemp -t beike-mac-doctor.XXXXXX)"
  code=0
  "$CLI" doctor --pretty >"$tmp" 2>&1 || code=$?
  api=0; key=0
  /usr/bin/grep -Eq 'API[[:space:]]*可达' "$tmp" && api=1 || true
  /usr/bin/grep -Eq 'Key[[:space:]]*有效' "$tmp" && key=1 || true
  /bin/rm -f "$tmp"
  if [ "$api" = 1 ]; then printf '✓ API 可达\n'; else printf '✗ API 未确认可达\n'; fi
  if [ "$key" = 1 ]; then printf '✓ Key 有效\n'; else printf '✗ Key 未通过验证（不显示凭证内容）\n'; fi
  [ "$code" = 0 ] && [ "$api" = 1 ] && [ "$key" = 1 ]
}
default_workspace() {
  local dir parent
  dir="$PACKAGE_ROOT"
  while [ "$dir" != / ]; do
    if [ -f "$dir/AGENTS.md" ] || [ -d "$dir/.pi" ]; then printf '%s\n' "$dir"; return; fi
    parent="$(/usr/bin/dirname "$dir")"; dir="$parent"
  done
  /usr/bin/dirname "$PACKAGE_ROOT"
}
update_key() {
  local key
  require_cli
  [ -t 0 ] || fail '更新Key必须在本机交互终端操作；不要把真实Key放入脚本、聊天或参数。' 3
  printf '请在 https://building.ke.com/console 获取新Key；不要发到聊天。\n'
  key=''
  IFS= read -r -s -p '粘贴新Key（输入不显示）：' key || true
  printf '\n'
  [ -n "$key" ] || { unset key; printf '未输入Key，原授权不变。\n'; return 3; }
  if ! "$CLI" auth "$key" --save >/dev/null 2>&1; then
    unset key
    printf 'CLI未能完成保存，请检查本机安装及新Key。\n' >&2
    return 3
  fi
  unset key
  unset BEIKE_MCP_API_KEY || true
  if doctor_check; then
    printf '授权已更新到本机用户目录。请复制普通文字覆盖剪贴板。\n'
  else
    printf '新Key尚未通过服务验证，请重新核对；不要将Key发到聊天。\n' >&2
    return 3
  fi
}
