from phs.tasks.service_daemon_reload import ServiceDaemonReload


def test_reloads_systemd(target):
    ServiceDaemonReload().execute(target)
    target.runner.run.assert_called_once_with(["systemctl", "daemon-reload"], root=True)
