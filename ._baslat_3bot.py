import subprocess, os, sys, time

proje_kok = r'C:\Users\marko\Desktop\Reymen Proje\ReYMeN-Ajan'
profiller = {
    'pasa_38': ('default', r'C:\Users\marko\AppData\Local\hermes\profiles\default\.env'),
    'kiral38': ('kiral38', r'C:\Users\marko\AppData\Local\hermes\profiles\kiral38\.env'),
    'reymen':  ('reymen', r'C:\Users\marko\AppData\Local\hermes\profiles\reymen\.env'),
}

for ad, (profil, env_path) in profiller.items():
    token = ''
    for line in open(env_path).read().splitlines():
        line = line.strip()
        if 'TELEGRAM_BOT_TOKEN' in line and '//' not in line:
            token = line.split('=', 1)[1].strip()
            break
    env = os.environ.copy()
    env['TELEGRAM_BOT_TOKEN'] = token
    env['HERMES_PROFILE'] = profil
    env['HERMES_GATEWAY'] = 'ai'
    p = subprocess.Popen(
        [sys.executable, os.path.join(proje_kok, 'reymen', 'ag', 'telegram_bot.py')],
        env=env, cwd=proje_kok,
        stdout=open(os.path.join(proje_kok, '.ReYMeN', f'{ad}_bot.log'), 'w'),
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    print(f'{ad}: PID={p.pid}')
    time.sleep(2)
print('3 bot hazir')
