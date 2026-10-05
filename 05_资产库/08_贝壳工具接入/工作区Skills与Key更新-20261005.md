# 当前工作区 Skills 与 Key 更新

> 2026-10-05用户授权：把7个既有官方贝壳Skills设为当前工作区的Skills，并说明更新Key后的本机接入方式。本轮不更换Key、不采集房源、不改官方Skill内容。

## 1. 当前项目级安装

项目位置：`/Users/xbpd/Projects/ai口播数字人-实习项目介绍/07-测试2`。

- Skills实际文件在[`.pi/skills/`](../../.pi/skills/)下的7个`beike-*`目录；不是指向全局的软链接。
- [`.pi/settings.json`](../../.pi/settings.json)显式启用7个项目入口与`/skill:<名称>`命令。
- 官方版本：买房0.3.10、租房0.3.15，行情/政策/学区/卖房/装修均0.1.10。
- CLI继续使用本机`~/.local/bin/beike` 0.2.26；Skills项目级、CLI及默认凭证用户级，两者范围不同。

本轮执行的官方安装形式：

```bash
curl -fsSL https://raw.githubusercontent.com/LianjiaTech/beike-ai-platform/master/skills/install.sh | bash -s -- --skills-dir "$PWD/.pi/skills" --no-cli
```

下载与完整性检查成功、退出码0。Pi的`DefaultResourceLoader`连续两次reload确认实际选中的7个入口全部来自当前工作区；项目外仍使用全局版本。

**当前会话生效：在Pi中执行`/reload`，或重新进入本工作区。**若提示项目资源信任，核对目录后确认；当前聊天尚未自动热重载。可用`/skill:beike-buy`显式载入买房技能，不代表启动房源查询。

### 同名提示边界

保留了`~/.agents/skills/`的全局安装，不删除、不改名。当前Pi版本的项目资源过滤不能关闭用户级自动发现，因此加载器会提示7个同名碰撞；实测每项的winner都是项目文件。它们不是7个额外执行器，也不改变项目级来源。

另有1个既存的、与贝壳无关的全局YAML诊断，项目内外均可复现；本轮未修改那个全局技能，不宣称全环境零诊断。不为消除提示改Pi源码或影响其他工作区。

## 2. ZIP如何接入

沿用已登记AST-014：[Windows原始参考ZIP](贝壳房源抓取一键包-Windows-20260819.zip)，不重复复制、不重新打包；SHA为`a2d5620e1ce34dabf0869ba4967047f405826f5092df618be271982933cd55a3`。

它保留Windows双击抓取方案作参考，**不在Mac执行其exe或cmd**。Mac实际使用本机官方CLI和上述项目Skills；参考包仍不是图片自动下载器或VR模型下载器。

上次用户级安装及授权结果保留为[历史接入说明](README.md)，官方来源快照保持原样；本页是后续项目级配置，不覆盖旧记录。

## 3. 换新Key后怎样接入

1. 在[贝壳凭证页面](https://building.ke.com/console)撤销已暴露/失效的Key，取得新的有效Key。
2. 在**本机macOS终端（默认zsh）**执行下列代码，再按隐藏提示粘贴新Key。不要把新Key发到聊天，不要直接把它写在命令、`.pi/settings.json`或项目文件里。

```zsh
unsetopt XTRACE
read -r -s "BEIKE_KEY?粘贴新 Key（输入不显示）："
printf '\n'
if [[ -n "$BEIKE_KEY" ]]; then
  beike auth "$BEIKE_KEY" --save --pretty
else
  printf '未输入 Key，没有更新授权。\n'
fi
unset BEIKE_KEY
beike doctor --pretty
```

3. `doctor`同时显示**API可达、Key有效**才算接入成功；若失败，检查新Key是否有效与网络，不凭Key文件存在判成功。
4. 复制一段普通文字覆盖剪贴板。无需重新安装Skills或修改ZIP。

官方`auth --save`写入`~/.beike/BEIKE_MCP_API_KEY`，文件权限600。该默认凭证供这台电脑、这个用户的贝壳CLI使用，**不只限当前工作区**；项目里不保存副本，分享工作区/ZIP时不要附带用户凭证目录。

隐藏输入避免Key进入终端输入回显和命令历史；CLI仍按官方形式接收短时进程参数，请在可信本机操作，勿开启shell调试/终端录制。如果设置过`BEIKE_MCP_API_KEY`环境变量，需移除或替换旧值并重启相关终端/Agent，避免旧环境值覆盖新保存的文件；不要用`printenv`或`cat`展示Key。

**本轮只验证上述流程的zsh语法和虚构Key模拟分支，没有执行真实Key更新，也没有读取或记录任何凭证值/哈希。**

## 4. 证据与回退

- [变更前保护基线](../../04_测试与验收/资料整理核验/工作区贝壳Skills前基线-20261005.json)。
- [官方项目安装输出](../../04_测试与验收/资料整理核验/工作区贝壳Skills安装输出-20261005.log)。
- [Pi实际加载来源核验](../../04_测试与验收/资料整理核验/工作区贝壳Skills加载核验-20261005.json)。
- [项目文件/Key示例/保护最终核验](../../04_测试与验收/资料整理核验/工作区贝壳Skills最终核验-20261005.json)。

回退只移除本次新增的7个项目技能目录，并恢复本次新建项目配置的先前状态；若`.pi`后来增加其他文件，不删除整个目录。全局Skills、全局设置、CLI、已归档ZIP、原素材与冻结合同保持不变，凭证无需恢复。
