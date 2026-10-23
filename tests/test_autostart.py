from nst.autostart import generate_systemd_unit, generate_sway_exec

def test_generate_systemd_unit():
    unit = generate_systemd_unit("/home/user/.local/bin/nst", "/home/user/.config/nst/config.toml")
    assert "ExecStart=" in unit
    assert "WantedBy=sway-session.target" in unit
    assert "ExecStartPre=" in unit
    assert "swaymsg -t get_outputs" in unit
    assert "PartOf=sway-session.target" in unit
    assert "Restart=always" in unit
    assert "StartLimitIntervalSec=0" in unit
    assert "TimeoutStartSec=90" in unit

def test_generate_sway_exec():
    exec_line = generate_sway_exec("/home/user/.local/bin/nst")
    assert "swaymsg -t get_outputs" in exec_line
    assert "/home/user/.local/bin/nst" in exec_line
