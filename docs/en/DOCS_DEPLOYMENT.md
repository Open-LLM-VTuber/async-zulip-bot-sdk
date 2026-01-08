# 📖 MkDocs Documentation Deployment

Quick guide for deploying the documentation.

## Local Preview

```bash
# Install dependencies
uv pip install -r requirements-docs.txt

# Start dev server
mkdocs serve
```

Visit:
- Chinese: http://127.0.0.1:8000/zh/
- English: http://127.0.0.1:8000/en/

## GitHub Pages Deployment

### Setup

1. Go to repository **Settings** > **Pages**
2. Set **Source** to "GitHub Actions"
3. That's it! The workflow will auto-deploy on push to main branch

### Trigger Deployment

Documentation is automatically deployed when you:
- Push to `main` branch
- Modify files in `docs/` directory
- Modify `mkdocs.yml`

Or manually trigger:
- Go to **Actions** tab
- Select "Deploy MkDocs" workflow
- Click "Run workflow"

### View Documentation

After deployment succeeds, visit:
- Chinese: `https://your-username.github.io/async-zulip-bot-sdk/zh/`
- English: `https://your-username.github.io/async-zulip-bot-sdk/en/`

## Configuration

Update these fields in `mkdocs.yml`:

```yaml
site_url: https://your-username.github.io/async-zulip-bot-sdk/
repo_url: https://github.com/your-username/async-zulip-bot-sdk
```

Replace `your-username` with your GitHub username.

## Adding Documentation

### Chinese (Default)

1. Create `.md` file in `docs/` directory
2. Add entry in `mkdocs.yml` nav section

### English

1. Create corresponding `.md` file in `docs/en/` directory
2. Filename must match Chinese version
3. Add translation in `nav_translations` section

## Structure

```
docs/
├── README.md          # Chinese home
├── quickstart.md      # Chinese quick start
├── *.md               # Other Chinese docs
└── en/                # English versions
    ├── README.md
    ├── quickstart.md
    └── *.md
```

## Features

- ✅ Dark/Light mode toggle
- ✅ Code highlighting and copy
- ✅ Bilingual search (Chinese & English)
- ✅ Navigation and sidebar
- ✅ Responsive design
- ✅ Emoji support

## Troubleshooting

### Plugin installation fails

```bash
pip install --upgrade pip
pip install -r requirements-docs.txt
```

### GitHub Pages not showing

1. Check Settings > Pages is enabled
2. Verify workflow ran successfully
3. Wait a few minutes for GitHub Pages to update

### Chinese characters garbled

Ensure all `.md` files are saved with UTF-8 encoding.

---

For more details, see [DOCS_DEPLOYMENT.md](DOCS_DEPLOYMENT.md)
