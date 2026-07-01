import subprocess, os, sys, time

proje_kok = r'C:\Users\marko\Desktop\Reymen Proje\ReYMeN-Ajan'
profiller = {
    'kiral38': ('kiral38', r'C:\Users\marko\AppData\Local\hermes\profiles\kiral38\.env'),
    'reymen':  ('reymen', r'C:\Users\marko\AppData\Local\hermes\profiles\reymen\.env'),
}

for ad, (profil, env_path) in profiller.items():
    token = ''
    for line in open(env_path).read().splitlines():
        line = line.strip()
        if line.startswith('TELEGRAM_BOT_TOKEN='):
            token = line.split('=', 1)[1].strip()
            break
    env = os.environ.copy()
    env['TELEGRAM_BOT_TOKEN'] = token
    env['HERMES_PROFILE'] = profil
    env['HERMES_GATEWAY'] = 'ai'
    script = os.path.join(proje_kok, 'reymen', 'ag', 'telegram_bot.py')
    log_file = os.path.join(proje_kok, '.ReYMeN', f'{ad}_bot.log')
    p = subprocess.Popen(
        [sys.executable, script],
        env=env, cwd=proje_kok,
        stdout=open(log_file, 'w'),
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    print(f'{ad} (profil={profil}): PID={p.pid}')
    time.sleep(2)

print('3 bot aktif')
