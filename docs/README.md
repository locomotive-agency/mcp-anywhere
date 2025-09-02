# MCP Anywhere Documentation

This directory contains the documentation website for MCP Anywhere, built with [MkDocs Material](https://squidfunk.github.io/mkdocs-material/).

## 📝 Updating the Documentation

### Local Development

1. **Install dependencies:**
   ```bash
   pip install -r docs/requirements.txt
   ```

2. **Start the development server:**
   ```bash
   mkdocs serve
   ```
   The docs will be available at http://localhost:8000 with hot reloading.

3. **Edit content:**
   - Main pages are in `docs/` directory as Markdown files
   - Navigation is configured in `mkdocs.yml`
   - Assets (images, etc.) go in `docs/assets/`

### File Structure

```
docs/
├── README.md              # This file
├── requirements.txt       # Python dependencies
├── mkdocs.yml            # MkDocs configuration
├── index.md              # Homepage
├── getting-started.md    # Getting Started guide
├── deployment.md         # Deployment guide
└── assets/
    └── images/           # Screenshots and logos
```

## 🚀 Deploying Documentation Updates

### Automatic Deployment

The documentation automatically deploys when you push to the `main` branch:

1. **Make your changes** to the documentation files
2. **Commit and push:**
   ```bash
   git add .
   git commit -m "docs: update documentation"
   git push origin main
   ```
3. **GitHub Actions** will automatically build and deploy to GitHub Pages
4. **Live site** updates at https://mcpanywhere.com within 2-5 minutes

### Manual Deployment

If needed, you can manually deploy:

```bash
mkdocs gh-deploy --force
```

This builds the docs and pushes to the `gh-pages` branch.

## 📖 GitHub Pages Tips

### Initial Setup

If GitHub Pages isn't configured yet:

1. Go to **Settings → Pages** in the GitHub repository
2. Set **Source** to "Deploy from a branch"  
3. Select **Branch**: `gh-pages`
4. Select **Folder**: `/ (root)`
5. Click **Save**

### Custom Domain Setup

For https://mcpanywhere.com:

1. **Add DNS records** with your domain provider:
   ```
   A     @    185.199.108.153
   A     @    185.199.109.153  
   A     @    185.199.110.153
   A     @    185.199.111.153
   CNAME www  locomotive-agency.github.io
   ```

2. **Configure in GitHub:**
   - Go to Settings → Pages
   - Add `mcpanywhere.com` in the Custom domain field
   - Enable "Enforce HTTPS" once DNS propagates

### Troubleshooting

**Build fails?**
- Check the Actions tab for error details
- Common issues: missing requirements, broken links, invalid YAML

**Changes not showing?**
- GitHub Pages can take 5-10 minutes to update
- Check if the gh-pages branch was updated
- Clear browser cache

**404 errors?**
- Verify the gh-pages branch exists and has content
- Check that Pages is configured to use the gh-pages branch
- Ensure DNS is properly configured for custom domains

## 🎨 Theme Customization

The site uses MkDocs Material with:
- **Primary color**: Custom mint green (`#00D4AA`)
- **Logo**: `docs/assets/images/logo.png`
- **Favicon**: `docs/assets/images/favicon.ico`
- **Features**: Navigation tabs, search, dark/light mode

To modify the theme, edit the `theme` section in `mkdocs.yml`.

## 📚 MkDocs Resources

- [MkDocs Material Documentation](https://squidfunk.github.io/mkdocs-material/)
- [Markdown Syntax Guide](https://www.markdownguide.org/basic-syntax/)
- [Material Design Icons](https://materialdesignicons.com/)