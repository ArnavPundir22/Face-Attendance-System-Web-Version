import gdown
import os

ids = [
    "1oXU1JobF3dOv13sB50QMvN93reg_NG8a",
    "1RaJJpwLiGPivHMwsKJYJwxtKkXr9-Fyd",
    "18HHoq2IP990EDSZz6s_dUVWnzuhWQtH4",
    "1zgiY0MWpEoydjsU2_M7MGOpXqoWohlbh",
    "1uMykMQpmcAmaHktCN_FOcV0JdyRG-qP4",
    "1rSg_vwiLxHGFRFvuB6RGcF70OLp31zWH",
    "1Ltc1q6pp9A1Zwg0QHbm_iRGtOGmtXH2B",
    "1-_amVpuAirxi5rnOBJTVp8mZRV2_vYPC",
    "1ebMFqPEStD5EKACiaF1rgOVAn3_9y6H1",
    "1doX0-mYNxFhCWI2L9KmLxxaUW6QEGAzl",
    "13izHVNbUeAlkLEuzvCcUTfeAdnSRU4jv",
    "1wvgQOmyOdqxZomjasfkoba-W6VXUsfAN",
    "1SGrzCCpbeqvtB0CcihFFQ2xyJ4z2Ev1n",
    "1neAQeJYPRfGpxW1HvPVF1JtMemEGS_G4",
    "1df9r071Ak1qFvja6Gd4WokTOxMWkojXV",
    "1YjO_D_TI4RcxnePkk1q4vYIEQWDE7enN",
    "1V0mqSpkzKLZsEssbtdKHliPvPwjrsVer",
    "1pVVltTi3iz7dF4qSUCXeAxKB0doqHztb",
    "1-Cbfha7xgxN3Um2tsFEMgljrLmLbPPUo",
    "1pmsXQqpfLdoA6p_QxifXwyW3k9XdSQDt",
    "13hHCazn1EVC4YuW0QMCn4coZ0BHWu_pp",
    "17mfbYCzaIVEue1zQSR1kp3JflnVjieKp",
    "1Gi4LbdAYoZKoRblRjx8CrtaifRLafCW2",
    "1lqD9PR6g5xxdUO6RtMrjqopFS6AYjdN2",
    "1wvWqVRCJeEF6A-IZ_K84oZSfH2OqgHIu"
]

os.makedirs("downloaded_files", exist_ok=True)
os.chdir("downloaded_files")

for file_id in ids:
    print(f"Downloading {file_id}...")
    try:
        gdown.download(id=file_id, quiet=False)
    except Exception as e:
        print(f"Failed to download {file_id}: {e}")

print("All downloads completed.")
