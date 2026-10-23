# 手绘海报

唯一必需输入：一张照片。

触发词：手绘、极简手绘、手绘图、手绘海报。
专用入口或明确调用后只上传图片即可执行；普通聊天单独上传图片不自动触发。

默认输出：1536 × 2048 PNG，上半原照片、下半极简手绘，各占 50%，无文字。

目录：
- SKILL.md：触发条件、默认流程与验收规则。
- references/image-prompt.md：插图生成及背景扩展模板。
- scripts/compose_poster.py：确定性拼接，禁止拉伸和隐式裁切。
- requirements.txt：拼接脚本依赖。

将本目录交给支持 SKILL.md 的宿主加载；宿主平台的实际注册方式取决于其接口。
本文件包未注册到宿主，不包含图像生成模型。宿主需提供参考图生成能力，
需要扩展背景时还需保护原图区域的编辑能力。

在配置了 Pillow 的 Python 环境中运行：

```bash
python scripts/compose_poster.py --photo photo-panel.png --illustration illustration-panel.png --output hand-drawn-poster.png
```

两个分区须为 3:2。若原图不宜裁切或扩展，可用 `--photo-fit contain` 等比留边。
脚本保证尺寸与分栏比例；主体保真、插图留白与风格仍需图像对照验收。
