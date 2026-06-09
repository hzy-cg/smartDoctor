import psutil
for p in psutil.process_iter(['pid', 'name', 'cmdline', 'memory_info']):
    try:
        cmd = ' '.join(p.info.get('cmdline') or [])
        if 'uvicorn' in cmd:
            rss = p.info['memory_info'].rss / 1024 / 1024
            print(f"PID={p.info['pid']} RSS={rss:.0f}MB")
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
