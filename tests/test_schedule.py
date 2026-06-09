from pathlib import Path

from shippost import schedule


def test_build_plist_contains_time_repo_and_args():
    out = schedule.build_plist(
        hour=18,
        minute=5,
        repo=Path("/r"),
        tone="punchy",
        open_x=True,
        program="/bin/shippost",
    )
    assert "<integer>18</integer>" in out
    assert "<integer>5</integer>" in out
    assert "/r" in out
    assert "com.shippost.remind" in out
    assert "remind" in out and "run" in out
    assert "--tone" in out and "punchy" in out
    assert "--open" in out
    assert "/bin/shippost" in out


def test_build_cron_line():
    line = schedule.build_cron_line(
        hour=9, minute=30, repo=Path("/r"), program="/bin/shippost"
    )
    assert line.startswith("30 9 * * *")
    assert "/bin/shippost remind run --repo /r" in line


def test_install_and_uninstall_launchd(monkeypatch, tmp_path):
    plist = tmp_path / "agent.plist"
    monkeypatch.setattr(schedule, "PLIST_PATH", plist)
    runs = []
    monkeypatch.setattr(
        schedule.subprocess, "run", lambda args, **kw: runs.append(args)
    )

    path = schedule.install_launchd("<plist/>")
    assert path == plist
    assert plist.read_text() == "<plist/>"
    assert any("load" in a for a in runs)
    assert schedule.launchd_status()["installed"] is True

    assert schedule.uninstall_launchd() is True
    assert not plist.exists()
    assert schedule.uninstall_launchd() is False
