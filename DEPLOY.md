# Deployment Workflow

## Overview: Two remotes, one repo

This project pushes to **two separate remotes** from the same local git repo:

| Remote | Command | Purpose |
|--------|---------|---------|
| `origin` | `git push origin main` | GitHub — source code backup & history |
| `hf` | `git push hf main` | HuggingFace Spaces — triggers live rebuild & deploy |

**Typical workflow for every change:**
```bash
git add .
git commit -m "describe what you changed"
git push origin main   # save to GitHub
git push hf main       # deploy to HuggingFace
```

To verify remotes are configured correctly:
```bash
git remote -v
# Should show:
# origin  https://github.com/YOUR_USER/GoTranslate.git (fetch/push)
# hf      https://huggingface.co/spaces/codekmh/GoTranslate (fetch/push)
```

If `hf` remote is missing, add it:
```bash
git remote add hf https://huggingface.co/spaces/codekmh/GoTranslate
```

If `origin` remote is missing, add it:
```bash
git remote add origin https://github.com/YOUR_USER/GoTranslate.git
```

---

# Deploying to HuggingFace Spaces

Remote name: `hf`
Space URL: https://huggingface.co/spaces/codekmh/GoTranslate

---

## Every time you make changes and want to redeploy

```bash
git add .
git commit -m "describe what you changed"
git push hf main
```

HuggingFace will automatically rebuild the Docker image and redeploy.
Watch the build progress in the Spaces dashboard under **Logs**.

---

## If the push is rejected (force push)

```bash
git push hf main --force
```

---

## Important rules — read before pushing

### 1. Never edit README.md in Notepad or VS Code "Save As"
The README.md must stay **UTF-8**. Windows apps often save as UTF-16,
which HuggingFace rejects with: `README.md is not a text file`

If this happens, fix it with:
```bash
python3 -c "
content = open('README.md', encoding='utf-16').read()
open('README.md', 'w', encoding='utf-8', newline='\n').write(content)
"
git add README.md
git commit -m "fix: README encoding"
git push hf main --force
```

### 2. Large files must go through Git LFS
These are already configured in `.gitattributes`:
- `*.jpg`, `*.png`, `*.pdf` — images and PDFs
- `libraries/jamdict.db` — the dictionary database

If you add a new large file (>10 MB), track it before adding:
```bash
git lfs track "your_large_file.ext"
git add .gitattributes
git add your_large_file.ext
```

### 3. Don't commit __pycache__ or .pyc files
These are already in `.gitignore`. If they sneak in:
```bash
git rm -r --cached libraries/__pycache__
git rm -r --cached libraries/ocr/__pycache__
git rm -r --cached tests/__pycache__
git commit -m "remove pycache"
```

---

## If you add a new Python dependency

1. Add it to `requirements.txt`
2. Commit and push — HuggingFace will `pip install -r requirements.txt` during rebuild

---

## If you change the port or app settings

The HuggingFace Spaces config is in `README.md` (the YAML header):
```yaml
---
title: GoTranslate
emoji: 🈳
sdk: docker
app_port: 7860
---
```
The app must always listen on port **7860**.
This is set in `backend/app.py` via `config.py`.

---

## Build time warning

The first build after a Dockerfile change takes **15–30 minutes**
because it reinstalls PaddlePaddle, PyTorch, and re-downloads all OCR models.

Subsequent pushes that only change Python/frontend code are fast (~2 min)
because Docker caches the model layers.

To keep builds fast: avoid changing lines above the `COPY libraries/` line
in the Dockerfile unless absolutely necessary.

---

## Check if the Space is running

```bash
curl https://codekmh-gotranslate.hf.space/health
```

Should return: `{"status": "ok"}`
