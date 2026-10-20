"""Between suites: delete throwaway e2e-* users and reset the rate-limit counters this suite itself drives up
(sign-in for demo / admin, and the per-address sign-up / reset counters), so the suites can be re-run back to back."""
import api_e2e as h

patterns = [f"rl:signin:*:{h.DEMO[0]}", f"rl:signin:*:{h.ADMIN[0]}", "rl:signup:127.0.0.1", "rl:forgot:127.0.0.1",
            "rl:signup-email:e2e-*", "rl:signup-resend:e2e-*", "rl:forgot-email:e2e-*", "rl:reset:*", "rl:signup-verify-ip:*",
            "rl:signup-resend-ip:*"]
for pattern in patterns:
    for k in h.r.scan_iter(pattern):
        h.r.delete(k)
h.cleanup()
