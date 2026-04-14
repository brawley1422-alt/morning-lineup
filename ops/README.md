# ops — systemd user units for Morning Lineup

Runtime units that keep the daily pipeline running unattended.

## Evening edition watcher

`morning-lineup-evening.timer` fires at 18:00 local time each day and
triggers `morning-lineup-evening.service`, which runs `evening.py`. The
script polls the MLB Schedule API every 5 minutes, rebuilds each team's
page as its game reaches Final, and runs `deploy.py` once at the end.

### Install

```bash
mkdir -p ~/.config/systemd/user
cp ops/morning-lineup-evening.service ~/.config/systemd/user/
cp ops/morning-lineup-evening.timer ~/.config/systemd/user/

systemctl --user daemon-reload
systemctl --user enable --now morning-lineup-evening.timer
```

Make sure user-lingering is on so the timer keeps firing when you're
logged out:

```bash
sudo loginctl enable-linger "$USER"
```

### Inspect

```bash
# When does it fire next?
systemctl --user list-timers morning-lineup-evening.timer

# Last run status + logs
systemctl --user status morning-lineup-evening.service
tail -f ~/morning-lineup/data/evening.log
```

### Prerequisites

- `~/morning-lineup` checked out with `python3`, `build.py`, `deploy.py`,
  `evening.py` in place.
- `~/.secrets/morning-lineup.env` exporting `GITHUB_TOKEN` (`chmod 600`).
- System time zone set to `America/Chicago` so the 18:00 fire time is
  actually 6 PM CT. Verify with `timedatectl`.

### Manual dry run

```bash
python3 evening.py --dry-run          # all teams, no rebuild
python3 evening.py --team cubs        # single team (legacy behavior)
python3 evening.py --team cubs --dry-run
```
