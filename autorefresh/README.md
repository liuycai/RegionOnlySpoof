# Once-per-boot helper 1.2.0

From the repository root, install with `sudo /usr/bin/python3 -I autorefresh/setup.py install`, inspect with `/usr/bin/python3 -I autorefresh/setup.py status`, and remove with `sudo /usr/bin/python3 -I autorefresh/setup.py uninstall`.

Requires the bundled KEXT 1.0.2 completion marker. The helper subscribes before examining existing published services, then validates the completion marker and service instance. There is no region-value gate, fixed 20-second settle, or kmutil polling. On readiness it performs at most one SIGTERM/relaunch attempt per boot. This is process replacement, not an in-process soft reset; PID changes when a running daemon is rebuilt.

Read-only: `helper.py --wait-ready 2` observes readiness without signaling, posting notifications or writing state. `helper.py --check` additionally reads current region/PID/qualification.

Results: `eligible_after_refresh`, `refreshed_but_not_eligible`, `driver_not_ready_timeout`, `driver_changed_no_action`, `process_identity_not_verified`, `precondition_failed`, `action_failed`, `refresh_not_confirmed`. `lastInvocationOutcome=already_attempted_this_boot` is a safe same-boot skip. The job normally ends in `not running` with exit 0. Read [INSTALL.md](../INSTALL.md), [UNINSTALL.md](../UNINSTALL.md), [SECURITY.md](../SECURITY.md) and [VALIDATION.md](../VALIDATION.md) for details.
