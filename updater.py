import glob
import logging
import os
import shutil
import subprocess
import sys
import threading
import time
import traceback

from .config import settings

LOG = logging.getLogger("ixope.updater")


class Updater:
    """Simple Git-based OTA updater with rollback support."""

    def __init__(self):
        # The git checkout is the CODE folder (REPO_ROOT), never the writable
        # data dir (BASE_PATH). Keeping them separate means `git reset --hard`
        # during an update can't touch captured images / videos / config.
        self.repo_dir = settings.REPO_ROOT
        self.remote = settings.GIT_REMOTE
        self.branch = settings.GIT_BRANCH
        self.interval = settings.UPDATE_CHECK_INTERVAL_MINUTES * 60
        self.rollback_enabled = settings.ROLLBACK_ON_FAILURE
        self._thread = threading.Thread(target=self._run, daemon=True, name="Updater")
        self._stop_requested = threading.Event()

    def start(self):
        if not self._thread.is_alive():
            LOG.info("Starting OTA updater thread")
            self._thread.start()

    def stop(self):
        self._stop_requested.set()
        if self._thread.is_alive():
            self._thread.join(timeout=5)

    def _run(self):
        while not self._stop_requested.is_set():
            try:
                self.check_for_update()
            except Exception:
                LOG.warning("OTA updater failed", exc_info=True)
            self._stop_requested.wait(self.interval)

    def check_for_update(self):
        if not os.path.isdir(os.path.join(self.repo_dir, ".git")):
            LOG.warning("OTA updater disabled: not a git repository")
            return

        current_rev = self._git("rev-parse", "HEAD")
        LOG.info("Checking for updates from %s/%s", self.remote, self.branch)

        try:
            self._git("fetch", self.remote, self.branch, "--depth=1")
        except subprocess.CalledProcessError as exc:
            LOG.warning("Git fetch failed: %s", exc)
            return

        try:
            target_rev = self._git("rev-parse", f"{self.remote}/{self.branch}")
        except subprocess.CalledProcessError:
            LOG.warning("Unable to resolve remote branch %s/%s", self.remote, self.branch)
            return

        if target_rev == current_rev:
            LOG.info("No new update available")
            return

        LOG.info("Update available: %s -> %s", current_rev[:8], target_rev[:8])
        if self._apply_update(current_rev, target_rev):
            LOG.info("Update applied successfully")
            if settings.AUTO_RESTART_ON_UPDATE:
                self._restart_service()
        elif self.rollback_enabled:
            self._rollback(current_rev)

    def _apply_update(self, old_rev, target_rev):
        try:
            self._git("reset", "--hard", target_rev)
            self._install_requirements()
            self._health_check()
            return True
        except Exception as exc:
            LOG.error("Failed to apply update: %s", exc)
            LOG.debug(traceback.format_exc())
            return False

    def _rollback(self, old_rev):
        LOG.warning("Rolling back to previous commit %s", old_rev[:8])
        try:
            self._git("reset", "--hard", old_rev)
            self._install_requirements()
            LOG.info("Rollback complete")
        except Exception as exc:
            LOG.error("Rollback failed: %s", exc)
            LOG.debug(traceback.format_exc())

    def _install_requirements(self):
        requirements = os.path.join(self.repo_dir, "requirements.txt")
        if not os.path.isfile(requirements):
            LOG.warning("No requirements.txt found, skipping dependency install")
            return

        LOG.info("Installing requirements from %s", requirements)
        self._run_command([sys.executable, "-m", "pip", "install", "-r", requirements], cwd=self.repo_dir)

    def _health_check(self):
        LOG.info("Running repo health check")
        python = sys.executable
        for path in glob.glob(os.path.join(self.repo_dir, "**", "*.py"), recursive=True):
            self._run_command([python, "-m", "py_compile", path], cwd=self.repo_dir)

    def _git(self, *args):
        return self._run_command(["git", *args], cwd=self.repo_dir).strip()

    def _run_command(self, command, cwd=None):
        LOG.debug("Running command: %s", " ".join(command))
        result = subprocess.run(
            command,
            cwd=cwd or self.repo_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        if result.stderr:
            LOG.debug("Command stderr: %s", result.stderr.strip())
        return result.stdout

    def _restart_service(self):
        service = getattr(settings, "SYSTEMD_SERVICE_NAME", None)
        if not service:
            LOG.warning("AUTO_RESTART_ON_UPDATE is enabled but no SYSTEMD_SERVICE_NAME is configured")
            return

        systemctl_path = shutil.which("systemctl")
        if not systemctl_path:
            LOG.warning("systemctl not found; cannot restart %s", service)
            return

        try:
            LOG.info("Restarting service %s after update", service)
            subprocess.run([systemctl_path, "restart", service], check=True)
            LOG.info("Service %s restarted successfully", service)
        except subprocess.CalledProcessError as exc:
            LOG.error("Failed to restart %s: %s", service, exc)
            LOG.debug(traceback.format_exc())


def create_and_start_updater():
    updater = Updater()
    updater.start()
    return updater
