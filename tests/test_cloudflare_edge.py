import unittest
from runtime.cloudflare_edge import EdgeConfig, CloudflareEdge


class TestCloudflareEdge(unittest.TestCase):
    def test_disabled_without_creds(self):
        e = CloudflareEdge(EdgeConfig())
        self.assertFalse(e.cfg.enabled)
        ok, data = e.health()
        self.assertFalse(ok)

    def test_kv_get_no_config(self):
        e = CloudflareEdge(EdgeConfig())
        ok, data = e.kv_get("x")
        self.assertFalse(ok)

    def test_d1_rate_limit_string(self):
        # Ensure the graceful-degradation token exists in source logic.
        from runtime import cloudflare_edge as m
        self.assertIn("d1_rate_limited", open(m.__file__).read())


if __name__ == "__main__":
    unittest.main()
