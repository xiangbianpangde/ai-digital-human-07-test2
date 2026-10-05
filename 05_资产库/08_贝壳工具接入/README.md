# 贝壳工具接入资料

> 2026-10-05：用户明确授权归档 Windows ZIP 参考包并执行官方 Skills 安装命令。当前电脑为 macOS / Apple Silicon，实际查询使用官方 Mac arm64 CLI，不运行 ZIP 内的 Windows 程序。

## 1. 已完成与安装位置

用户指定的命令已实际执行，退出码为0：

```bash
curl -fsSL https://raw.githubusercontent.com/LianjiaTech/beike-ai-platform/master/skills/install.sh | bash
```

| 对象 | 当前结果 |
|---|---|
| CLI | `~/.local/bin/beike`，0.2.26，Mach-O arm64；与官方 darwin-arm64 发布包中的二进制一致 |
| Skills | `~/.agents/skills/`，7个业务技能；本机已是官方清单版本，安装器幂等跳过重复覆盖 |
| 版本 | `beike-buy` 0.3.10、`beike-rent` 0.3.15；market/policy/school/sell/decor均0.1.10 |
| 完整性 | 独立下载7个官方发布ZIP，校验清单SHA及全部归档成员；与已安装文件全部匹配 |
| 授权 | `beike doctor --pretty`退出0，API可达、既有本机Key有效；凭证文件权限600 |
| 会话加载 | 本会话已能识别7个业务Skills；新会话应重新加载或重启后检查，不宣称所有工具入口均已实测 |

安装前备份：`~/.local/share/beike-install-backups/20261005T115507+0800/`，仅包含原CLI、7个Skills及文件校验信息，不含凭证。需要回滚时先核对该目录的`backup-info.json`，仅恢复它记录的CLI和Skill路径，不恢复或覆盖个人授权。

本机已经有有效授权，因此没有把用户在聊天里提供的凭证保存或传给命令。**进入聊天记录的Key建议在贝壳凭证页面撤销并换新，在本机重新授权；不要再次发送到聊天、代码或资料库。**

## 2. 原始包与官方来源快照

- [用户提供的Windows参考ZIP](贝壳房源抓取一键包-Windows-20260819.zip)：与Downloads原包SHA一致，归档只读；含CLI 0.2.24、Windows双击入口及7个Skills。它不是当前Mac安装源，也不是房源数据包。
- [官方Skills安装脚本快照](官方Skills安装脚本-20261005.sh)：原样保留，只读、不作为项目自动执行器。
- [官方Skills清单快照](官方Skills清单-20261005.json)。
- [官方CLI清单快照](官方CLI清单-20261005.json)。

来源：[贝壳AI Platform](https://github.com/LianjiaTech/beike-ai-platform)、[官方安装入口](https://raw.githubusercontent.com/LianjiaTech/beike-ai-platform/master/skills/install.sh)、[凭证管理](https://building.ke.com/console)。这些清单是本次快照，不保证以后仍为最新版。

## 3. 如何用于下一次资料获取

只安装已有官方能力，本轮没有创建自定义Pi Skill或Mac版抓取脚本。七个Skills是AI调用CLI的指导文件；获取详情和素材信息可复用以下形式，**下面的占位命令未执行**：

```bash
beike buy detail -c '<城市>' --id '<房源ID>' -t house --pretty
beike buy material -c '<城市>' --id '<房源ID>' -t house --pretty
```

二手房为`house`，新房为`newhouse`；小区为`resblock`，原Windows脚本只对小区查询详情。返回字段、图片/户型图地址和VR入口取决于房源、权限与接口。本轮未调用详情或素材接口，不将用户另放入的房源目录当成本轮采集结果。

**素材信息或链接不等于图片原文件/VR模型已下载归档。** 下一次取得明确城市和ID及采集范围后，再逐项验证房源匹配、真实素材返回、原图保存、来源/哈希与新会话重放；不回填G02为完成。户型图/房产事实获取也不替代单镜设计→实测→审核流程。

Windows参考包的安装器有一处限制：完整性检查要求内置CLI压缩包存在，普通缺失会提前失败，不能依赖后面的下载兜底。它的PowerShell抓取入口只保存CLI输出的Markdown，没有独立下载图片或VR模型的逻辑。

## 4. 接入验收凭据

凭据均不记录Key值或个人授权内容：

- [接入前保护基线](../../04_测试与验收/资料整理核验/贝壳接入前基线-20261005.json)。
- [官方命令执行记录](../../04_测试与验收/资料整理核验/贝壳官方安装执行-20261005.json)、[安装输出](../../04_测试与验收/资料整理核验/贝壳官方安装输出-20261005.log)。
- [Skills发布文件核验](../../04_测试与验收/资料整理核验/贝壳Skills文件核验-20261005.json)、[CLI发布文件核验](../../04_测试与验收/资料整理核验/贝壳CLI文件核验-20261005.json)。
- [脱敏授权状态](../../04_测试与验收/资料整理核验/贝壳授权状态-20261005.json)。
- [最终接入与保护核验](../../04_测试与验收/资料整理核验/贝壳接入后核验-20261005.json)。

实时状态见[当前入口](../../00_入口/00_当前.md)。原素材、冻结房产合同、原镜头与终片、相邻工程和其他房源资料保持不变；没有开始采集、拍摄、配音、数字人制作或付费媒体调用。
