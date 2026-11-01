# Deploy

What runs on the Pi besides PiEEG Server: Tina's page on port 8080 and the welcome shown on every SSH login. Both are plain files, so the copy in this repository is the backup.

| File | Goes to | What it does |
|---|---|---|
| [`../page/`](../page) | `~/tina-eeg/` | the page: manual, spec sheet and live signal in one, served as static files |
| [`tina-page.service`](tina-page.service) | `/etc/systemd/system/` | serves `~/tina-eeg` on port 8080 with Python's built in web server |
| [`update-motd.d/05-welcome`](update-motd.d/05-welcome) | `/etc/update-motd.d/` | the SSH welcome: links, service status, the battery rules, a few commands |

On the Pi, from the repository root (the service file assumes the user `jure`; change `User` and the paths for another account):

```bash
mkdir -p ~/tina-eeg && cp -r page/index.html page/assets ~/tina-eeg/
sudo install -m 644 deploy/tina-page.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now tina-page

sudo install -m 755 deploy/update-motd.d/05-welcome /etc/update-motd.d/
sudo cp /etc/motd /etc/motd.debian && sudo truncate -s 0 /etc/motd   # Debian's default text, kept as a backup
```

Check: `curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8080/` prints `200`, and a new SSH login shows the welcome.

The page's six drawings are rendered by [`page/tools/page_figures.py`](../page/tools/page_figures.py) with the same renderer and parts as the figures in `docs/` (see [`docs/figures/README.md`](../docs/figures/README.md)). Run `python page/tools/page_figures.py` to rebuild them into `page/assets/svg`.
