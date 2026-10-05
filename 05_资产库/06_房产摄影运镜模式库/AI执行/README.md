# AI 执行入口：沙湖九号统一方法库

## 读取顺序与适用范围

1. 项目 `HANDOFF.md`、`00_入口/00_当前.md` 与风险页，先确认授权边界。
2. 本目录 `方法库.json`：25个规范方法，来源路径相对项目根，可包含 `../08-真人录制/`；原片只读引用。
3. 本目录 `点位.json`：SDK 27点的房间归属、坐标、原生高度、邻接和已测范围。
4. 本目录 `画廊.html`：可播放原片与后期反例，不是整片台本或成片。

初次验收：**18项原配方可复用；3项后期技术通过但视觉拒绝；4项blocked，未现场执行。** 后续按用户批准新增6项独立安全变体（P03V1/P05V1/P06V1/P07V1/P08V1/P09V1），均实测接受。原拒绝/禁用记录不解禁；P10按用户“暂不付费”决定延期，尚无真实AI实测，不标记通过。 10项采集、6项后期、5项叙事示范均按单项闭环处理。叙事仅为静默图文，不表示口播、数字人或整片已完成。Shot 1–3原状态不变，Shot 4待用户审查，Shot 5未授权。

## 配置与门禁

- `type`：`capture / post / narrative`；`policy`：`default / optional / prohibited`。
- `verification` 与 `visual` 独立；技术通过不表示视觉接受或政策准入。无视频的 blocked 保留理由，不能虚构通过记录。
- `production_ready=true` 只代表**本房源这条配方**可复用，不是任何路线、任何朝向、任何房源的通用许可，也不认证离墙净空。
- `recipe` 是实测配方；`evidence` 是路径+SHA-256；`tests` 保留失败版本；`sources` 是原来源引用；`execution` 表示执行器而非整片批处理。
- `catalog.py select ID` 在输出前检查策略、房源、事实档案、场景/点位哈希、所选凭据、配方一致性和输入素材溯源。发现漂移时停止，不通过手改索引中的 `production_ready` 绕过。
- `--experiment` 只用于查看已实测反例的配方；P07–P10即使带此参数仍拒绝。反例不得进入正式视频。
- 原始视频、图片和take审查不可覆盖；新实验必须用新的take ID。可重新生成的只有统一索引、点位表与画廊。

## 已测配方速查

| ID | 所选take | 配方边界 |
|---|---|---|
| C01 | establish-04 | P1，yaw3.18，FOV80，原地2.2秒；最终执行器复验 |
| C02 | continuous-01 | P9→P1→P2，各5秒；**后退展开**，不可倒称向前推镜 |
| C03 | door-03 | P9→P10，yaw3.18→3.85，5秒过门；其他两版墙/柱主导已拒绝 |
| C04 | dollhouse-03 | 显式模型机位飞出总览→硬切P25；**不是平滑俯冲**，使用时必须标注“三维户型示意” |
| C05 | push-01 | P1→P9，yaw3.18，5秒真实坐标前推 |
| C06 | lookback-01 | P1，yaw3.18→6.32，12秒约180°慢回望；不可压成3秒快转 |
| C07 | micro-01 | P25，yaw3.18→3.4，3秒原地微摇；不是orbit |
| C08 | sweep-01 | P25，yaw3.4→4.15，5秒从窗至室内；空房，不声称已有床 |
| C09 | fov-02 | 厨房P5，yaw0.04，4秒FOV80→75；不是dolly |
| C10 | reverse-01 | P9，yaw0.04，2.5秒反打；不声称12米长轴 |
| P01 | cut-01 | 2秒切点，窗居中作共同锚点；不证明两个空间相邻 |
| P02 | dissolve-01 | 8帧短叠化，30fps下实际0.267秒；仅可选后期 |
| P04 | zoom-cut-01 | 最大5%中心数码裁切配硬切；不是真实前推 |
| N01 | identity-01 | 身份、建面约163平米、4室2厅、户型图；4秒静默卡 |
| N02 | selling-02 | “客厅，直通阳台”；旧“大面窗户”版本与玻璃门画面不符，已拒绝 |
| N03 | question-01 | “这里，你会怎么布置？”；空卧室微摇，不虚构家具 |
| N04 | corroborate-01 | “回望客餐厅 / 核对空间关系”；短素材冻结尾帧补至4秒 |
| N05 | action-01 | “打开完整VR，继续看房”；仅指已实测链接，不承诺评论、二维码服务或成片 |

P03长叠化、P05横滑、P06白闪保留可播放拒绝反例。P07缺完整遮挡源帧；P08禁止高速甩镜；P09未实现碎片合成；P10无生成服务及几何一致性证据。完整评估见 `04_测试与验收/方法库实测/blocked-assessment.json`。

## 安全变体（与原效果严格区分）

JSON根字段`methods`仍为25个原方法，`variants`为独立变体；原方法的`safe_alternatives`仅指向可选替代，不自动修改原policy或视觉结论。选择器必须使用变体ID，不能继续选被禁用的原ID。

| ID | 已接受take | 实际实现 |
|---|---|---|
| P03V1 | long-graphic-01 | 图形说明层0.5秒长叠化，建筑画面硬切；不跨空间叠影 |
| P05V1 | edge-slide-01 | 左缘装饰滑条最多24px，建筑画面不横滑/拼接 |
| P06V1 | soft-pulse-01 | 白层最大8/255透明度的单次轻亮，不是全白闪屏 |
| P07V1 | graphic-occlusion-02 | 明确标注的后期遮罩，切点完整遮底1帧；不是现场贴墙遮挡 |
| P08V1 | direction-cut-01 | 同一空卧室已测慢摇方向匹配后硬切；不执行高速甩镜 |
| P09V1 | tile-reveal-02 | 96块二维图形分片揭示实景；不是打碎房屋或三维破面 |

遮挡与分片首版的半透明说明栏会漏底，已追加`visual-superseded.json`撤销复用许可，保留原记录后重做02版。自动检查覆盖编码后遮罩帧alpha完整性，不只相信代码参数。

```sh
python3 03_实现/方法库/catalog.py select P07V1
python3 03_实现/方法库/repair.py \
  04_测试与验收/方法库实测/graphic-occlusion-02/recipe.json graphic-occlusion-repeat-01
```

每次仅一个变体，新的take ID必须未使用，生成后仍需视觉review。`repair.py`只读已accept采集输入，拒绝变体/父方法ID不一致；P08V1固定同房间方向匹配输入。执行器哈希漂移时select拒绝使用。

最新修复复验：`acceptance-repair-02.json`，23项自动测试、391个哈希、34条当前有效/历史反例视频全帧解码。撤销的两个遮罩首版不作为有效take计入此复验。

P10预算依据在`04_测试与验收/方法库实测/P10-budget-01.json`：Replicate FILM官方估价约US$0.03/次，拟最多3次，建议预留US$0.50测试预算；这是预估而非固定收费。用户已选择“暂不付费”，权威决定见`P10-decision-01.json`：本次execution_permission=false，付费调用0次，不检查网页登录或充值。未来新授权后才安全登录/配置凭据及实测；不能在聊天或资产库落明文密钥。预算提案不构成许可。

## 单项执行

所有命令在项目根运行。先核对索引、选中凭据和实际加载房源；不把全表依次自动拍成整片。

```sh
python3 03_实现/方法库/catalog.py select C03
```

采集示例使用当前已验证配方文件。`door-repeat-01` 必须是未使用的新ID：

```sh
python3 -u 03_实现/方法库/run.py capture \
  04_测试与验收/方法库实测/door-03/recipe.json door-repeat-01
```

启动后会打印本次随机端口/token，并写入新take的 `connection.json`。读取其中 `eval`，**通过原生 `agent_browser` 工具**在 `--session methodlib` 执行，timeout至少覆盖动作总时长（建议90000ms）；不可从 bash/subprocess 调用浏览器CLI。接收端最多等待180秒。不得复用旧连接。

```text
agent_browser({args:["--session","methodlib","eval", connection.eval], timeoutMs:90000})
```

浏览器执行器只接受单项、最多8步，限制FOV75–85°、已存在的机位、邻接移动、缓慢摇摄、显式模型机位；真实到达并等待贴图。`connection.json` 的token仅供当次本地接收。Python只接收、转码与检查，不控制浏览器。

后期或图文示范读取已接受素材，每次仅一个方法：

```sh
python3 03_实现/方法库/catalog.py select P02
python3 03_实现/方法库/render.py \
  04_测试与验收/方法库实测/dissolve-01/recipe.json dissolve-repeat-01
```

输出技术检查后仍是视觉 `pending`。人工打开接触表，短转场还需检查 `transition.png`；只登记实际看过的图片。拒绝项使用 `reject`，修改后换新take重新闭环：

```sh
python3 03_实现/方法库/run.py review dissolve-repeat-01 accept \
  '填写本次真实观察理由，不复制历史结论' --reviewed contact.png transition.png
python3 03_实现/方法库/catalog.py build
```

改变yaw、点位、时长、文本、输入素材或特效幅度均视为新变体，不能自动继承旧accept。`render.py` 固定叙事文本，拒绝未测试措辞；N01无采集输入，其余N项只接受一个已验收采集take。

## 验收与限制

```sh
PYTHONDONTWRITEBYTECODE=1 python3 03_实现/方法库/verify.py
```

追加保存复验结果时使用 `--out 04_测试与验收/方法库实测/新的验收ID.json`，文件存在即拒绝覆盖。首份完整验收为 `acceptance-01.json`：16项自动测试、305个来源/证据哈希核对、28条技术有效视频全帧解码、10个所选采集配方的终态核验。浏览器5类拒绝测试另见 `browser-guards.json`。

- 原生SDK的 `position.y-standingPosition.y` 范围为约1.155–1.189m（概括为约1.17m），不平移全景相机伪造高度；真人摄影仍按1.5–1.6m。
- 邻接只证明原生点位可达，所有 `metric_clearance=unverified`；未做离墙≥0.5m量测认证。
- SDK提供全部27点房间归属，但视觉通过只覆盖当前配方涉及的P1/P2/P5/P9/P10/P25及C04模型示意，**不表示27点逐一试拍**。
- 点位表沿用SDK“卧室B、卫生间A/B”等原名；历史“P21主卫”“阳台A/公卫/衣帽间无点位”不应继续作为执行依据。
- 全帧解码只证明视频有效；接触表是视觉采样，不是逐帧人工观看整段视频。短转场逐帧表只覆盖切点附近。
- SDK模型切换与canvas录屏已实测；桌面Computer Use签名失败，未通过。不可把SDK结果写成桌面服务验收。
