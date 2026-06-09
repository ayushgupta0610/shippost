from shippost import notify


def test_macos_uses_osascript(monkeypatch):
    captured = {}
    monkeypatch.setattr(notify.sys, "platform", "darwin")
    monkeypatch.setattr(
        notify.subprocess, "run", lambda args, **kw: captured.setdefault("args", args)
    )
    notify.send_notification("shippost", "hi there")
    assert captured["args"][0] == "osascript"
    assert "hi there" in captured["args"][-1]
    assert "shippost" in captured["args"][-1]


def test_linux_uses_notify_send(monkeypatch):
    captured = {}
    monkeypatch.setattr(notify.sys, "platform", "linux")
    monkeypatch.setattr(
        notify.subprocess, "run", lambda args, **kw: captured.setdefault("args", args)
    )
    notify.send_notification("title", "body")
    assert captured["args"][0] == "notify-send"
    assert captured["args"][1:] == ["title", "body"]


def test_missing_binary_does_not_raise(monkeypatch):
    monkeypatch.setattr(notify.sys, "platform", "darwin")

    def boom(*a, **k):
        raise FileNotFoundError("osascript")

    monkeypatch.setattr(notify.subprocess, "run", boom)
    notify.send_notification("t", "m")  # must not raise


def test_other_platform_is_noop(monkeypatch):
    calls = {"n": 0}
    monkeypatch.setattr(notify.sys, "platform", "win32")
    monkeypatch.setattr(
        notify.subprocess, "run", lambda *a, **k: calls.__setitem__("n", calls["n"] + 1)
    )
    notify.send_notification("t", "m")
    assert calls["n"] == 0
