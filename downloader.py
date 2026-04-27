import sys
import time
from pathlib import Path

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    sys.exit("Install dulu:\n  pip install selenium webdriver-manager")

# ── Settings ──────────────────────────────────────────────────────────────────
LINKS_FILE        = "acefile_links.txt"
OUTPUT_DIR        = "./downloads"
DELAY_BETWEEN     = 2     # detik jeda antar link
WAIT_DOWNLOAD_SEC = 10    # detik cek apakah download mulai

# ── Helpers ───────────────────────────────────────────────────────────────────
def log(msg, level="INFO"):
    icon = {"INFO": "·", "OK": "✔", "WARN": "⚠", "ERR": "✘"}
    print(f"  {icon.get(level, '·')}  {msg}", flush=True)


def read_links(path: str) -> list[str]:
    links = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                links.append(line)
    return links


def get_crdownload_files(dest: Path) -> list[Path]:
    return list(dest.glob("*.crdownload")) + list(dest.glob("*.tmp"))
    
def get_done_files(dest: Path) -> set[Path]:
    return {
        f for f in dest.glob("*")
        if f.suffix not in (".crdownload", ".tmp") and f.is_file()
    }


# ── Browser ───────────────────────────────────────────────────────────────────
def make_driver(dest: Path) -> webdriver.Chrome:
    dest.mkdir(parents=True, exist_ok=True)
    opts = Options()
    
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("detach", True)
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_experimental_option("prefs", {
        "download.default_directory":                               str(dest.resolve()),
        "download.prompt_for_download":                             False,
        "download.directory_upgrade":                               True,
        "safebrowsing.enabled":                                     True,
        "profile.default_content_settings.popups":                  0,
        "profile.default_content_setting_values.automatic_downloads": 1,
    })
    # opts.add_argument("--headless=new")  # uncomment untuk tanpa jendela

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=opts
    )
    driver.execute_script(
        "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"
    )
    return driver


# ── Per-link flow ─────────────────────────────────────────────────────────────
def process_link(driver: webdriver.Chrome, url: str, dest: Path, index: int, total: int) -> bool:
    print(f"\n{'─'*55}")
    print(f"  [{index}/{total}]  {url}")
    print(f"{'─'*55}")

    main_tab = driver.current_window_handle

    # ── Step 1: Buka halaman acefile ─────────────────────────────────────────
    log("Membuka acefile.co …")
    driver.get(url)

    # ── Step 2: Klik Fast Download ────────────────────────────────────────────
    try:
        wait = WebDriverWait(driver, 15)
        fast_btn = wait.until(EC.element_to_be_clickable((
            By.XPATH,
            "//a[contains(translate(.,'DOWNLOAD','download'),'download')] | "
            "//button[contains(translate(.,'DOWNLOAD','download'),'download')]"
        )))
        log(f"Klik tombol: '{fast_btn.text.strip()}' …")
        fast_btn.click()
    except Exception as e:
        log(f"Tombol Fast Download tidak ditemukan: {e}", "ERR")
        return False


 
    # ── Step 3: Cari dan klik <input id="uc-download-link"> ──────────────────
    log("Mencari tombol 'Tetap download' (id=uc-download-link) …")
    try:
        tetap_btn = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.ID, "uc-download-link"))
        )
        log(f"Tombol ditemukan → klik …", "OK")
        tetap_btn.click()
    except Exception as e:
        log(f"Tombol tidak ditemukan: {e}", "ERR")
        # Tutup tab gdrive, kembali ke main
        try:
            driver.close()
        except Exception:
            pass
        driver.switch_to.window(main_tab)
        return False
 
    # ── Step 4: Cek apakah download dimulai (.crdownload muncul) ─────────────
    log(f"Mengecek proses download (maks {WAIT_DOWNLOAD_SEC}s) …")

    download_started = False

    for _ in range(WAIT_DOWNLOAD_SEC):
        crdownloads = get_crdownload_files(dest)

        if crdownloads:
            log("Download aktif → lanjut ke link berikutnya …", "OK")
            download_started = True
            break

        time.sleep(1)

    if not download_started:
        log("Download belum terdeteksi → tunggu 10 detik lagi …", "WARN")
        time.sleep(10)

        crdownloads = get_crdownload_files(dest)

        if crdownloads:
            log("Download akhirnya berjalan.", "OK")
            download_started = True
        else:
            log("Download tidak dimulai → tandai GAGAL.", "ERR")
            return False

    return True
 


#Mengunggu Download Selesai
# def wait_all_downloads(dest: Path):
#     log(f"Menunggu semua download selesai…", "WARN")
#     bars = {}

#     try:
#         while True:
#             in_progress = get_crdownload_files(dest)

#             if not in_progress:
#                 # tutup semua bar yang masih aktif
#                 for bar in bars.values():
#                     bar.close()
#                 log("Semua download selesai!", "OK")
#                 return True

#             active_names = set()

#             for f in in_progress:
#                 name = f.name
#                 active_names.add(name)

#                 try:
#                     current_size = f.stat().st_size
#                 except FileNotFoundError:
#                     continue
            

#     except KeyboardInterrupt:
#         for bar in bars.values():
#             bar.close()
#         log("Dihentikan oleh user. Download yang berjalan mungkin terpotong.", "WARN")
#         return False
 
# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    dest  = Path(OUTPUT_DIR)
    links = read_links(LINKS_FILE)
 
    if not links:
        sys.exit(f"Tidak ada link di {LINKS_FILE}")
 
    print(f"\n{'═'*55}")
    print(f"  AceFile → Google Drive Batch Downloader")
    print(f"  Links   : {len(links)}")
    print(f"  Output  : {dest.resolve()}")
    print(f"{'═'*55}")
 
    log("Membuka browser …")
    driver  = make_driver(dest)
    success = []
    failed  = []
 
    try:
        for i, url in enumerate(links, 1):
            ok = process_link(driver, url, dest, i, len(links))
 
            if ok:
                success.append(url)
            else:
                failed.append(url)
 
            if i < len(links):
                time.sleep(DELAY_BETWEEN)
 
        # Setelah semua link diproses, tunggu semua download selesai
        print(f"\n{'═'*55}")
        log(f"Semua link diproses. {len(success)} berhasil dimulai, {len(failed)} gagal.")
        log("Menunggu semua file selesai diunduh …")
        # wait_all_downloads(dest)
 
    except KeyboardInterrupt:
        print()
        log("Dihentikan oleh user. Download yang berjalan mungkin terpotong.", "WARN")
 
    finally:
        log("Menutup browser …")
        # driver.quit()
 
    # ── Ringkasan ─────────────────────────────────────────────────────────────
    done_files = get_done_files(dest)
    print(f"\n{'═'*55}")
    print(f"  Link berhasil diproses : {len(success)}")
    print(f"  Link gagal             : {len(failed)}")
    print(f"  File di folder output  : {len(done_files)}")
    print(f"{'═'*55}")
 
    if failed:
        fail_path = dest / "failed_links.txt"
        fail_path.write_text("\n".join(failed))
        log(f"Link gagal disimpan → {fail_path}", "WARN")
        for u in failed:
            print(f"    ✘  {u}")
 
 
if __name__ == "__main__":
    main()