# 📚 文档部署说明

本项目使用 MkDocs Material 和 GitHub Actions 自动构建和部署双语文档。

## 本地预览

### 安装依赖

```bash
uv pip install -r requirements-docs.txt
```

### 启动开发服务器

```bash
mkdocs serve
```

访问 http://127.0.0.1:8000 查看文档

### 构建文档

```bash
mkdocs build
```

生成的静态文件在 `site/` 目录

## 文档结构

```
docs/
├── README.md              # 中文首页
├── quickstart.md          # 中文快速开始
├── core.md                # 中文核心组件
├── async_client.md        # 中文 AsyncClient 文档
├── base_bot.md            # 中文 BaseBot 文档
├── bot_runner.md          # 中文 BotRunner 文档
├── commands.md            # 中文命令系统文档
├── models.md              # 中文数据模型文档
├── config.md              # 中文配置文档
├── logging.md             # 中文日志文档
└── en/                    # 英文版本
    ├── README.md
    ├── quickstart.md
    └── ...                # 其他英文文档
```

## GitHub Actions 自动部署

### 配置步骤

1. **启用 GitHub Pages**
   - 进入仓库 Settings > Pages
   - Source 选择 "GitHub Actions"

2. **推送代码触发部署**
   
   当以下条件满足时自动触发部署：
   - Push 到 main 分支
   - 修改了 `docs/` 目录下的文件
   - 修改了 `mkdocs.yml` 配置文件

3. **查看部署状态**
   
   在仓库的 Actions 标签页查看工作流运行状态

4. **访问文档**
   
   部署成功后，访问：
   - 中文：`https://your-username.github.io/async-zulip-bot-sdk/zh/`
   - 英文：`https://your-username.github.io/async-zulip-bot-sdk/en/`

### 更新配置

修改 `mkdocs.yml` 中的以下字段：

```yaml
site_url: https://your-username.github.io/async-zulip-bot-sdk/
repo_url: https://github.com/your-username/async-zulip-bot-sdk
```

将 `your-username` 替换为你的 GitHub 用户名。

## 添加新文档

### 中文文档

1. 在 `docs/` 目录创建新的 `.md` 文件
2. 在 `mkdocs.yml` 的 `nav` 部分添加条目

### 英文文档

1. 在 `docs/en/` 目录创建对应的 `.md` 文件
2. 文件名需要与中文版本一致（如 `README.md`, `quickstart.md`）
3. 在 `mkdocs.yml` 的 `nav_translations` 添加翻译

## 文档主题配置

当前使用 Material for MkDocs 主题，支持：

- ✅ 深色/浅色模式切换
- ✅ 代码高亮和复制
- ✅ 搜索功能（中英文）
- ✅ 导航栏和侧边栏
- ✅ 响应式设计
- ✅ Emoji 支持

## 本地开发技巧

### 实时预览

```bash
# 监听文件变化，自动刷新
mkdocs serve --dev-addr 0.0.0.0:8000
```

### 严格模式

```bash
# 遇到警告即失败
mkdocs build --strict
```

### 清理缓存

```bash
# 删除构建产物
rm -rf site/
```

## 故障排除

### 插件安装失败

```bash
pip install --upgrade pip
pip install -r requirements-docs.txt
```

### GitHub Pages 未显示

1. 检查 Settings > Pages 是否启用
2. 确认 workflow 运行成功
3. 等待几分钟让 GitHub Pages 更新

### 中文显示乱码

确保所有 `.md` 文件使用 UTF-8 编码保存。

## 贡献文档

欢迎贡献文档！请：

1. Fork 仓库
2. 创建新分支
3. 添加/修改文档
4. 提交 Pull Request

文档应该：
- 清晰易懂
- 包含代码示例
- 中英文对照（如果可能）
- 遵循现有格式
