import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
try:
    import numpy as np
except ImportError:
    print("camels ingest test skipped: numpy not installed")
    raise SystemExit(0)
import ingest_camels_sfrd as I

# the age of a flat LCDM universe with Om = 0.3 and h = 0.6711 today: 14.05 Gyr (977.792 / (100 h) Gyr = 14.57 Gyr times 2 / (3 sqrt(0.7)) asinh(sqrt(0.7 / 0.3)))
assert abs(I.time_of_a(1.0, 0.3) / 1e9 - 14.05) < 0.02, I.time_of_a(1.0, 0.3) / 1e9
# time is increasing in a and the matter-dominated limit goes as a^1.5
assert I.time_of_a(0.5, 0.3) < I.time_of_a(0.6, 0.3) and abs(I.time_of_a(0.02, 1.0 - 1e-9) / I.time_of_a(0.01, 1.0 - 1e-9) - 2 ** 1.5) < 0.01

# a log with a constant SFR of 100 Msun/yr (three columns before it carry other quantities), restarts that repeat times, and rows out of order
a = np.concatenate([np.linspace(0.1, 1.0, 4000), np.linspace(0.5, 0.6, 50)])  # the second block repeats times 0.5-0.6 (a restart)
rows = np.column_stack([a, np.zeros_like(a), np.full_like(a, 100.0), np.full_like(a, 100.0), np.zeros_like(a)])
txt = "\n".join(" ".join(f"{v:.8e}" for v in r) for r in rows).encode()
sfrd, formed = I.reduce_sfr(txt, 0.3, 2)
want = np.log10(100.0 / I.VOLUME)
assert all(abs(v - want) < 1e-3 for v in sfrd[:50] if v is not None), sfrd[:5]
# the total formed mass is 100 Msun/yr times the time from a = 0.1 to 1
assert abs(formed / (100.0 * (I.time_of_a(1.0, 0.3) - I.time_of_a(0.1, 0.3))) - 1.0) < 1e-3
# bins earlier than the first logged time are missing, not zero
assert sfrd[-1] is None and sfrd[-5] is None and sfrd[44] is not None and sfrd[46] is None  # z = 8.8-9.0 is logged, z = 9.2-9.4 is not
# a rate that doubles linearly in time: the bin value is the time average
t = I.time_of_a(a[:4000], 0.3)
rate = 10.0 + 90.0 * (t - t[0]) / (t[-1] - t[0])
rows2 = np.column_stack([a[:4000], np.zeros(4000), rate, rate, np.zeros(4000)])
txt2 = "\n".join(" ".join(f"{v:.8e}" for v in r) for r in rows2).encode()
sfrd2, _ = I.reduce_sfr(txt2, 0.3, 2)
k = 20  # the bin z = 4.0 to 4.2
a_hi, a_lo = 1 / 5.0, 1 / 5.2
tt = np.linspace(I.time_of_a(a_lo, 0.3), I.time_of_a(a_hi, 0.3), 4001)
exp_mean = np.mean(10.0 + 90.0 * (tt - t[0]) / (t[-1] - t[0]))
assert abs(sfrd2[k] - np.log10(exp_mean / I.VOLUME)) < 2e-3, (sfrd2[k], np.log10(exp_mean / I.VOLUME))
assert abs(I.VOLUME - (25 / 0.6711) ** 3) < 1e-6
print("camels ingest: OK")
