from nst.measurement.t1_probe import compute_probe_result, ProbeResult

def test_compute_probe_result_from_curl_output():
    # Simulated curl -w output for one connection
    conn_data = [
        {"size_download": 5000000, "time_total": 1.0, "time_starttransfer": 0.2, "http_code": 200, "time_namelookup": 0.004, "time_connect": 0.021, "time_appconnect": 0.064},
        {"size_download": 5000000, "time_total": 1.1, "time_starttransfer": 0.25, "http_code": 200, "time_namelookup": 0.004, "time_connect": 0.021, "time_appconnect": 0.064},
    ]
    result = compute_probe_result("cacheFly", conn_data, 5.0)
    assert result.host == "cacheFly"
    assert result.success is True
    assert result.down_mbps > 0
    assert result.bytes_consumed == 10000000

def test_compute_probe_result_failure():
    conn_data = [{"size_download": 0, "time_total": 0, "time_starttransfer": 0, "http_code": 429, "time_namelookup": 0, "time_connect": 0, "time_appconnect": 0}]
    result = compute_probe_result("cloudflare", conn_data, 5.0)
    assert result.success is False
    assert result.error is not None

def test_compute_probe_result_empty():
    result = compute_probe_result("cacheFly", [], 5.0)
    assert result.success is False
