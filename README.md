# Saturn’s Rings

![Saturn’s Rings](assets/saturns-rings-logo.png)

**一起生活、探索与创造。**

Saturn’s Rings 是两个人共同生活与工作的双平台 Skills 源码库，面向旅行、研究、购物计划、编程与日常创作。同一套核心规则，分别构建 GPT 与 Grok 独立安装包；现有技能见下方清单。

品牌原名 Little Universe Skills。仓库目标名称为 `saturns-rings`；GitHub 仓库路径需由管理员在 Settings → General 中完成重命名，再更新同步任务的仓库指向。
Plugin 显示名为 **Saturn’s Rings**；已安装 Plugin 的内部包名与各 Skill 的 `name` 保持稳定，以便原位更新。

## 目录与维护原则

```text
shared/<skill>/                 共用领域规则、参考资料、模板与辅助代码
platforms/grok/<skill>/         Grok 入口与平台专属文件
platforms/gpt/<skill>/          GPT 入口与平台专属文件
platforms/gpt/_common/          打入每个 GPT 包的运行约定
scripts/                       构建、校验与独立打包
migration/grok-baseline.json    迁移基准与原文件哈希
```

按用户指定，迁移前 `skills/` 全部作为 Grok 版基准，来源 commit 为
`b60ccc2d630c0f0fe444e015032e5be67ffb403d`。首次迁移的 Grok 构建结果与原来的
40 个文件逐字节一致；原文中已有的 ChatGPT 字样和 OpenAI metadata 也保留，
不把历史命名当成平台兼容保证。没有改变或重新安装用户正在运行的 Grok Bots。
旧 `skills/<name>` 路径已迁移；引用它的外部安装脚本需改用构建结果。

**平台目录是源码适配层，不是完整安装包。** 必须先构建，不能直接把稀疏目录装到宿主。
构建按「shared → 平台 _common → 平台 skill」组合；文件覆盖须在该平台
`overrides.json` 显式声明，意外同名或失效声明会报错。共用文件只维护一份。
所有包内部引用均限定在自身目录，不依赖运行时读 GitHub、其他 Skill 或 repo 外文件。

## 五个 Skills

| 名称 | 用途 | GPT 适配重点 |
|---|---|---|
| travel-planner | 两人艺术文化美食旅行规划 | 文件保存、只读 Grok 原件、协作不可用时自检 |
| art-culture-expert-guide | 跨文明建筑、艺术、历史与文化遗产专家导览 | 证据研究、图像与空间核验、自然中文讲解 |
| travel-food-guide | 当地当季餐饮研究与推荐卡片 | 点评／小红书不可访问时保留质量门槛并降级 |
| hand-drawn-poster | 上半摄影、下半纸本手绘的海报 | 遵循宿主图像工具规则，精确拼接须有能力和许可 |
| safety-charter | 授权、隐私、防注入与协作安全检查 | 移除固定路径与虚假全局生效声明，修正跳数示例 |

本次 art-culture-expert-guide 是从 travel-architecture-deep-guide 迁移的新 Skill ID；部署时先安装验证新版本，再移除旧版。其他 Skills 保持原标识。
安全原则也打入每个 GPT 包的运行约定，避免依赖安全 Skill 自动全局触发。
海报在无法获得可检验文件时只做视觉验收，不承诺精确像素或原图像素完全保留。

## 验证与构建

Python 3.12，依赖固定为 `requirements-dev.txt` 中的版本：

```bash
python -m pip install -r requirements-dev.txt
python scripts/validate-skills.py
python -m unittest discover -s tests -v
python scripts/build-skills.py --platform gpt --output build/gpt-install
python scripts/package-skills.py --sha "$(git rev-parse HEAD)" --output dist
```

`build-skills.py` 只接受空输出目录，产物位于 `<output>/<platform>/<skill>/`。
省略 `--platform` 会生成两套。每个 ZIP 命名为
`<platform>-<skill>-<full-commit-sha>.zip`，内部顶层仍为 `<skill>/`，保留完整自包含目录。
每次发布生成 10 个 ZIP；`build-<sha>.json` 记录平台、源码 SHA、文件清单、大小和 SHA-256。
压缩及解压后各不超过 25,000,000 bytes；包时间戳固定，可重复构建。

验证包括两平台 Skill 集合一致、frontmatter、UI metadata、引用不越界、禁止符号链接、
显式覆盖、独立解包校验及失败退出码。静态校验不能证明动态旅行事实已核实，亦不能证明平台运行效果。

## 发布和 GPT 安装

- `validate.yml` 在 PR 和 push 时验证两平台，check 名仍为 `validate-skills`。
- `publish.yml` 在 main push 后验证、测试并上传 10 个独立包，Artifact 名 `skills-<sha>`，保留 30 天。
- Actions → Package Skills → 成功的 main run → Artifacts 可下载；下载包不代表已安装。
- 当前 ChatGPT Work 若提供 Git 支持的 Skills 工作区，按该环境 Skill Creator 的正式持久化流程安装：
  构建 GPT 完整目录 → 按 frontmatter `name` 匹配已有技能、保留原目录身份 → 更新既有技能并新增缺失技能 →
  原位校验 → 每次仅提交一个技能目录 → 推送 Skills 工作区当前分支，再处理下一个技能。
  当前保存服务拒绝一次提交多个 Skill；不要把多技能更改合成一次推送。
  服务可能在保存后追加规范化提交或为新技能分配目录 ID；下一次操作前先 fetch 并快进，重新按 name 定位。
  遇到 fetch-first 时先读取远端更新，将当前单技能提交 rebase 后再推送，不 force push。
  验证时允许宿主补充 UI metadata，但指令和参考正文必须与构建结果一致。
  成功推送才算保存；仓库分支和安装来源 SHA 须记录，不能把本地复制当成已安装。
- 不在公共 repo 写入个人 Skills 工作区地址、token 或私人 ID。不支持上述机制的宿主须使用其正式安装入口，
  不猜测私有 API。GitHub CI 不持有安装凭证，不自动更新 GPT；后续源码改动需要再次构建并显式同步安装。
- Grok 安装使用构建后的 `grok/<skill>` 或对应独立包；本次不替换运行中的 Grok 安装。

公开仓库只保存通用规则与代码；照片、订单、私人行程、凭证与内部链接不提交。
私人文件按用户当前指定位置及对应平台实际存储能力处理，保存失败如实说明。
保留 PR 工作流，不直接推 main，不自动合并，不创建 Tag 或 Release。

## main Ruleset：人工配置

首次 PR CI 运行后，在 PR Checks 或 Actions job 页面确认实际 check name。
`validate-skills` 是工作流声明的预期名称；未观察到首次远端 CI 前，不能称它为已验证的实际名称，
不要添加尚未出现或拼写不同的必需检查。

仓库 **Settings → Rules → Rulesets → New branch ruleset**：

1. 名称 `protect-main`，Enforcement status 设为 **Active**，目标分支为 `main`，不设置常规 bypass。
2. 开启 **Require a pull request before merging**；单人维护 required approvals 设为 **0**，
   不强制无法满足的外部或 Code Owner 审批。
3. 开启 **Require status checks to pass**；选择首次 CI 实际出现的验证 check，来源为 GitHub Actions。
   建议同时启用 **Require branches to be up to date before merging**。
4. 开启 **Require conversation resolution before merging**、**Block force pushes**、
   **Restrict deletions**。
5. 保存后复查 Active、main 匹配范围及必需检查。设置未实际保存成功前，不宣称保护已生效。

若连接没有 Ruleset administration 能力，由仓库管理员执行以上步骤；不要绕过保护。
本仓库不包含自动修改 Ruleset、推送 main、打 Tag、创建 Release 或安装 ChatGPT 的代码。

## 新增或修改 Skill

1. 同时在两个平台建立同名入口；共用参考放 `shared/<name>`，平台差异放各自适配层。
2. 每个 GPT 入口引用 `references/platform-runtime.md`；构建时自动加入该文件。
3. 优先把平台差异写成独立参考，避免复制整份共用规则；确需覆盖时显式登记 `overrides.json`。
4. 修改 shared 前确认影响两边；只想改变 GPT 时不要直接修改 shared。
5. 运行全套校验与测试，检查独立包，再走 PR。升级当前 GPT 安装时匹配技能名称并保留原身份。
