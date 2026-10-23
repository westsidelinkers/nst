from nst.measurement.t0_passive import parse_iw_link, parse_ping_output, parse_iw_station_dump


def test_parse_iw_link():
    output = """Connected to a4:81:7a:2e:1e:ad (on wlp2s0)
\tSSID: RYAN 5G
\tfreq: 5220.0
\tRX: 3136115294 bytes (3994752 packets)
\tTX: 1912424200 bytes (2342866 packets)
\tsignal: -70 dBm
\trx bitrate: 87.8 MBit/s VHT-MCS 2 80MHz VHT-NSS 1
\ttx bitrate: 175.5 MBit/s VHT-MCS 4 80MHz VHT-NSS 1
\tbss flags: short-slot-time
\tdtim period: 1
\tbeacon int: 100
"""
    result = parse_iw_link(output)
    assert result["ssid"] == "RYAN 5G"
    assert result["signal_dbm"] == -70
    assert result["rx_bitrate_mbps"] == 87.8
    assert result["tx_bitrate_mbps"] == 175.5
    assert result["freq_mhz"] == 5220.0


def test_parse_ping_output():
    output = """PING 1.1.1.1 (1.1.1.1) 56(84) bytes of data.
64 bytes from 1.1.1.1: icmp_seq=1 ttl=58 time=10.8 ms
64 bytes from 1.1.1.1: icmp_seq=2 ttl=58 time=12.0 ms
64 bytes from 1.1.1.1: icmp_seq=3 ttl=58 time=10.7 ms
--- 1.1.1.1 ping statistics ---
3 packets transmitted, 3 received, 0% packet loss, time 2003ms
rtt min/avg/max/mdev = 10.700/11.167/12.000/0.569 ms
"""
    result = parse_ping_output(output)
    assert result["avg_ms"] == 11.167
    assert result["max_ms"] == 12.0
    assert result["mdev_ms"] == 0.569
    assert result["loss_pct"] == 0.0
    assert result["received"] == 3
    assert result["transmitted"] == 3


def test_parse_iw_station_dump():
    output = """Station a4:81:7a:2e:1e:ad (on wlp2s0)
\tauthorized: yes
\tinactive time: 108 ms
\trx bytes: 3136115294   rx packets: 3994752
\ttx bytes: 1912424200   tx packets: 2342866
\ttx retries: 0          tx failed: 0        beacon loss: 0
\tbeacon rx: 366569
\trx drop misc: 1205
\tsignal:      -70 [-70] dBm
\tsignal avg:  -70 [-70] dBm
\ttx bitrate: 175.5 MBit/s VHT-MCS 4 80MHz VHT-NSS 1
\ttx duration: 0 us
\trx bitrate: 87.8 MBit/s VHT-MCS 2 80MHz VHT-NSS 1
"""
    result = parse_iw_station_dump(output)
    assert result["tx_retries"] == 0
    assert result["tx_failed"] == 0
    assert result["beacon_loss"] == 0
    assert result["rx_drop_misc"] == 1205
    assert result["signal_dbm"] == -70
    assert result["signal_avg_dbm"] == -70