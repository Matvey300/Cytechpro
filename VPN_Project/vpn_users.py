#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import shlex
import subprocess
import sys
import uuid as _uuid
from datetime import datetime, timezone
from pathlib import Path

# -----------------------------------------------------------------------------
# Константы окружения (подправь при необходимости)
# -----------------------------------------------------------------------------
EC2_HOST_DEFAULT = "ec2-user@3.28.239.151"
SSH_KEY_DEFAULT = str(Path.home() / "AWS" / "VPN_SERVER_UAE" / "VPN_SERVER_UAE_KEY.pem")
SERVER_DOMAIN = "matvey300.duckdns.org"

# Пути на EC2
REMOTE_LEDGER_DIR = "/var/log/xray/users"
REMOTE_LEDGER = f"{REMOTE_LEDGER_DIR}/ledger.tsv"
REMOTE_ACCESSLOG = "/var/log/xray/access.log"
REMOTE_CONFIG = "/usr/local/etc/xray/config.json"
REMOTE_XRAY = "/usr/local/bin/xray"
REMOTE_MAKE_LAND = "/usr/local/bin/make_vless_landing.sh"

# Локальная папка для выгрузок
LOCAL_USERS_DIR = str(Path.home() / "AWS" / "Users")

# Порт/тег inbounds на сервере — используем только 443, как ты просил
INBOUND_PORT = 443


# -----------------------------------------------------------------------------
# Утилиты
# -----------------------------------------------------------------------------
def die(msg, code=1):
    print(f"[ERR] {msg}", file=sys.stderr)
    sys.exit(code)


def info(msg):
    print(f"[OK] {msg}")


def warn(msg):
    print(f"[WARN] {msg}")


def run(cmd, check=True, capture=False, timeout=None):
    """Локальный запуск"""
    if capture:
        return subprocess.run(
            cmd,
            shell=True,
            check=check,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
        ).stdout
    else:
        subprocess.run(cmd, shell=True, check=check, timeout=timeout)
        return ""


def remote(ssh_host, ssh_key, command, capture=True, sudo=False, timeout=40):
    """Выполнить команду на EC2. Если sudo=True, префиксует sudo."""
    key_q = shlex.quote(ssh_key)
    host_q = shlex.quote(ssh_host)
    cmd_q = command if not sudo else f"sudo bash -lc {shlex.quote(command)}"
    full = (
        f"ssh -i {key_q} -o BatchMode=yes -o StrictHostKeyChecking=accept-new "
        f"{host_q} {shlex.quote(cmd_q)}"
    )
    return run(full, check=True, capture=capture, timeout=timeout)


def scp_from(ssh_host, ssh_key, remote_path, local_path, timeout=60):
    key_q = shlex.quote(ssh_key)
    host_q = shlex.quote(ssh_host)
    r_q = shlex.quote(remote_path)
    l_q = shlex.quote(local_path)
    cmd = (
        f"scp -i {key_q} -o BatchMode=yes -o StrictHostKeyChecking=accept-new {host_q}:{r_q} {l_q}"
    )
    run(cmd, check=True, capture=False, timeout=timeout)


def ensure_local_dir(p: str):
    Path(p).mkdir(parents=True, exist_ok=True)


def now_utc_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def gen_uuid():
    return str(_uuid.uuid4())


# -----------------------------------------------------------------------------
# Серверная подготовка: каталоги, файлы и права
# -----------------------------------------------------------------------------
def server_bootstrap(ssh_host, ssh_key):
    cmd = f"""
set -e
sudo install -d -m 0755 {shlex.quote(REMOTE_LEDGER_DIR)}
# Создать файл если отсутствует, не трогая права
sudo bash -lc 'test -f {shlex.quote(REMOTE_LEDGER)} || {{ echo -e "ts\\taction\\tname\\tuuid\\tlanding\\tsubscribe" > {shlex.quote(REMOTE_LEDGER)}; }}'
"""
    remote(ssh_host, ssh_key, cmd, capture=True)


# -----------------------------------------------------------------------------
# Добавление UUID в Xray config (inbound:443) и рестарт сервиса
# -----------------------------------------------------------------------------
def server_add_client(ssh_host, ssh_key, uuid, name):
    script = f"""
set -e
ts=$(date -u +%F-%H%M%S)
conf="{REMOTE_CONFIG}"
bak="/usr/local/etc/xray/config.json.bak.$ts"

sudo cp -a "$conf" "$bak"

# Добавим клиента в inbound с портом {INBOUND_PORT} (если такого id ещё нет)
sudo jq '
  (.inbounds[] | select(.protocol=="vless" and .port=={INBOUND_PORT}) | .settings.clients) as $c |
  if ($c | map(.id) | index("{uuid}") ) then
    .
  else
    (.inbounds[] | select(.protocol=="vless" and .port=={INBOUND_PORT}) | .settings.clients) += [{{"id":"{uuid}","email":{json.dumps(name)}}}]
  end
' "$conf" | sudo tee "$conf.new" >/dev/null

# Проверка синтаксиса
sudo {REMOTE_XRAY} run -test -config "$conf.new" >/dev/null

# Атомарная замена и рестарт
sudo mv "$conf.new" "$conf"
sudo systemctl restart xray
"""
    remote(ssh_host, ssh_key, script, capture=True)


# -----------------------------------------------------------------------------
# Публикация лендинга/подписки на EC2
# -----------------------------------------------------------------------------
def publish_landing(ssh_host, ssh_key, name, uuid):
    cmd = f"{REMOTE_MAKE_LAND} {shlex.quote(name)} {shlex.quote(uuid)}"
    out = remote(ssh_host, ssh_key, cmd, capture=True, sudo=True)
    # Ожидаем строки вида:
    # Landing:   https://.../get/XXXX
    # Subscribe: https://.../subs/XXXX.txt
    landing, subscribe = None, None
    for line in out.splitlines():
        line = line.strip()
        if line.lower().startswith("landing:"):
            landing = line.split(":", 1)[1].strip()
        elif line.lower().startswith("subscribe:"):
            subscribe = line.split(":", 1)[1].strip()
    if not landing or not subscribe:
        raise RuntimeError(f"Неожиданный вывод make_vless_landing.sh:\n{out}")
    return landing, subscribe


# -----------------------------------------------------------------------------
# Запись в серверный журнал
# -----------------------------------------------------------------------------
def server_log_issue(ssh_host, ssh_key, name, uuid, landing, subscribe):
    ts = now_utc_iso()
    line = f"{ts}\tISSUE\t{name}\t{uuid}\t{landing}\t{subscribe}\n"
    cmd = f"printf %s {shlex.quote(line)} >> {shlex.quote(REMOTE_LEDGER)}"
    remote(ssh_host, ssh_key, cmd, capture=False, sudo=True)


def server_log_revoke(ssh_host, ssh_key, name, uuid, note=""):
    ts = now_utc_iso()
    line = f"{ts}\tREVOKE\t{name}\t{uuid}\t{note}\t-\n"
    cmd = f"printf %s {shlex.quote(line)} >> {shlex.quote(REMOTE_LEDGER)}"
    remote(ssh_host, ssh_key, cmd, capture=False, sudo=True)


# -----------------------------------------------------------------------------
# Формирование «умной» ссылки (для вывода пользователю)
# -----------------------------------------------------------------------------
def smart_message(name, landing, subscribe, domain=SERVER_DOMAIN):
    return (
        f"""
Готово!
Имя: {name}

1) Универсальная ссылка (откроет V2Box/предложит установить):
   {landing}

2) Подписка (текст с vless:// для ручного импорта):
   {subscribe}

Требования клиента: V2Box (или совместимый), актуальная версия.
Сервер: {domain} (TLS 443)
"""
    ).strip()


# -----------------------------------------------------------------------------
# Выдача ключей
# -----------------------------------------------------------------------------
def cmd_issue(args):
    ssh_host = args.ssh_host
    ssh_key = args.ssh_key
    name = args.name.strip()

    if not Path(ssh_key).exists():
        die(f"SSH ключ не найден: {ssh_key}")

    server_bootstrap(ssh_host, ssh_key)

    uuids = []
    if args.type == 1:
        uuids = [gen_uuid()]
    elif args.type == 2:
        uuids = [gen_uuid()]
    elif args.type == 3:
        if args.count < 1:
            die("Для type=3 укажи --count N (N>=1)")
        uuids = [gen_uuid() for _ in range(args.count)]
    else:
        die("Неизвестный тип. 1=безлимит, 2=1 ключ, 3=N ключей")

    # На каждый UUID: добавить в Xray config, опубликовать лендинг, залогировать
    for i, uid in enumerate(uuids, 1):
        info(f"[{i}/{len(uuids)}] Добавляю клиента {uid} в Xray…")
        server_add_client(ssh_host, ssh_key, uid, name)

        info("Публикую лендинг/подписку…")
        landing, subscribe = publish_landing(ssh_host, ssh_key, name, uid)

        server_log_issue(ssh_host, ssh_key, name, uid, landing, subscribe)

        print(smart_message(name, landing, subscribe))
        print("-" * 80)


# -----------------------------------------------------------------------------
# Отзыв
# -----------------------------------------------------------------------------
def cmd_revoke(args):
    ssh_host = args.ssh_host
    ssh_key = args.ssh_key
    name = args.name.strip()
    uuid = args.uuid.strip()
    note = args.note or ""

    if not Path(ssh_key).exists():
        die(f"SSH ключ не найден: {ssh_key}")

    # Прямо сейчас делаем «мягкий» ревок: пишем в журнал.
    # (Опционально можно удалить клиента из config.json и рестартануть xray —
    #  добавлю по запросу.)
    server_bootstrap(ssh_host, ssh_key)
    server_log_revoke(ssh_host, ssh_key, name, uuid, note)
    info(f"Ключ {uuid} помечен как REVOKE для {name}. (в {REMOTE_LEDGER})")


# -----------------------------------------------------------------------------
# Список активных (по журналу ISSUE-REVOKE)
# -----------------------------------------------------------------------------
def cmd_list(args):
    ssh_host = args.ssh_host
    ssh_key = args.ssh_key

    if not Path(ssh_key).exists():
        die(f"SSH ключ не найден: {ssh_key}")

    server_bootstrap(ssh_host, ssh_key)
    # Простейшее вычисление «активных»: ISSUE без последующего REVOKE
    awk = r"""awk -F'\t' '
    NR>1 {
      ts=$1; action=$2; name=$3; uid=$4;
      if (action=="ISSUE") { S[uid]=name; }
      else if (action=="REVOKE") { delete S[uid]; }
    }
    END { for (u in S) printf "%s\t%s\n", S[u], u; }'"""
    out = remote(
        ssh_host, ssh_key, f"cat {shlex.quote(REMOTE_LEDGER)} | {awk}", capture=True, sudo=True
    )
    if not out.strip():
        print("Активных ключей не найдено.")
        return
    print("Имя\tUUID")
    print(out, end="")


# -----------------------------------------------------------------------------
# Выгрузка журналов за последние 3 суток на Mac
# -----------------------------------------------------------------------------
def cmd_pull_logs(args):
    ssh_host = args.ssh_host
    ssh_key = args.ssh_key
    local_dir = args.local_dir

    ensure_local_dir(local_dir)

    if not Path(ssh_key).exists():
        die(f"SSH ключ не найден: {ssh_key}")

    server_bootstrap(ssh_host, ssh_key)

    # Точку отсчёта (последние 3 суток)
    out = remote(ssh_host, ssh_key, "date -u +%s", capture=True)
    now_epoch = int(out.strip())
    from_epoch = now_epoch - 3 * 24 * 3600

    # На сервере соберём tar.gz из ledger.tsv и последних строк access.log
    # Xray пишет даты вида: 2025/08/16 05:47:53 — распарсим в epoch через awk
    bundle_cmd = f"""
set -e
ts=$(date -u +%F-%H%M%S)
tmp="/tmp/xray_export_$ts"
mkdir -p "$tmp"
cp -a {shlex.quote(REMOTE_LEDGER)} "$tmp/ledger.tsv" || true

if [ -s {shlex.quote(REMOTE_ACCESSLOG)} ]; then
  awk -v since={from_epoch} '
    match($0, /([0-9]{{4}})\\/([0-9]{{2}})\\/([0-9]{{2}}) ([0-9]{{2}}):([0-9]{{2}}):([0-9]{{2}})/, m) {{
      # m1..m6: Y M D h m s
      cmd = sprintf("date -u -d \\"%s-%s-%s %s:%s:%s\\" +%%s", m[1],m[2],m[3],m[4],m[5],m[6]);
      cmd | getline epoch; close(cmd);
      if (epoch >= since) print $0;
    }}
  ' {shlex.quote(REMOTE_ACCESSLOG)} > "$tmp/access_last3d.log" || true
fi

tar -C "$tmp" -czf "/tmp/xray_logs_$ts.tgz" .
echo "/tmp/xray_logs_$ts.tgz"
"""
    remote_path = remote(ssh_host, ssh_key, bundle_cmd, capture=True, sudo=True).strip()
    if not remote_path:
        die("Не удалось сформировать архив логов на сервере")

    local_file = str(Path(local_dir) / Path(remote_path).name)
    scp_from(ssh_host, ssh_key, remote_path, local_file)
    info(f"Скачано: {local_file}")


# -----------------------------------------------------------------------------
# «Меню» (интерактивное) — запросит параметры и вызовет нужные команды
# -----------------------------------------------------------------------------
def cmd_menu(args):
    print("=== VPN Users Menu ===")
    ssh_host = input(f"SSH host [{EC2_HOST_DEFAULT}]: ").strip() or EC2_HOST_DEFAULT
    ssh_key = input(f"SSH key  [{SSH_KEY_DEFAULT}]: ").strip() or SSH_KEY_DEFAULT

    while True:
        print(
            """
1) Выдать ключ(и)
2) Отозвать ключ
3) Список активных ключей
4) Забрать журналы за 3 дня (на этот Mac)
5) Выход
        """
        )
        choice = input("Выбор: ").strip()
        if choice == "1":
            name = input("Имя пользователя (например: Liudmila Bogdanova): ").strip()
            print("Тип: 1=безлимит, 2=1 ключ, 3=N ключей")
            t = int(input("Тип: ").strip())
            count = 1
            if t == 3:
                count = int(input("N: ").strip())
            cmd_issue(
                argparse.Namespace(
                    ssh_host=ssh_host, ssh_key=ssh_key, name=name, type=t, count=count
                )
            )
        elif choice == "2":
            name = input("Имя: ").strip()
            uid = input("UUID: ").strip()
            note = input("Примечание (необяз.): ").strip()
            cmd_revoke(
                argparse.Namespace(
                    ssh_host=ssh_host, ssh_key=ssh_key, name=name, uuid=uid, note=note
                )
            )
        elif choice == "3":
            cmd_list(argparse.Namespace(ssh_host=ssh_host, ssh_key=ssh_key))
        elif choice == "4":
            local_dir = input(f"Локальная папка [{LOCAL_USERS_DIR}]: ").strip() or LOCAL_USERS_DIR
            cmd_pull_logs(
                argparse.Namespace(ssh_host=ssh_host, ssh_key=ssh_key, local_dir=local_dir)
            )
        elif choice == "5":
            print("Пока!")
            return
        else:
            print("Не понял выбор.")


# -----------------------------------------------------------------------------
# Аргументы CLI
# -----------------------------------------------------------------------------
def build_parser():
    p = argparse.ArgumentParser(
        description="Управление пользователями VLESS/TLS (Xray @ EC2) с публикацией «умных ссылок» и журналированием."
    )
    p.add_argument("--ssh-host", default=EC2_HOST_DEFAULT, help="SSH хост, например ec2-user@IP")
    p.add_argument("--ssh-key", default=SSH_KEY_DEFAULT, help="Путь к приватному ключу для SSH")
    sub = p.add_subparsers(dest="cmd", required=True)

    # issue
    sp = sub.add_parser("issue", help="Выдать ключ(и)")
    sp.add_argument("--name", required=True, help="Имя пользователя (например: Liudmila Bogdanova)")
    sp.add_argument(
        "--type",
        type=int,
        required=True,
        choices=[1, 2, 3],
        help="1=безлимит, 2=1 ключ, 3=N ключей",
    )
    sp.add_argument("--count", type=int, default=1, help="Для type=3 — количество ключей")
    sp.set_defaults(func=cmd_issue)

    # revoke
    sp = sub.add_parser("revoke", help="Отозвать ключ (мягкий ревок — запись в журнал)")
    sp.add_argument("--name", required=True)
    sp.add_argument("--uuid", required=True)
    sp.add_argument("--note", default="", help="Причина/пометка")
    sp.set_defaults(func=cmd_revoke)

    # list
    sp = sub.add_parser("list", help="Показать активные ключи (по журналу)")
    sp.set_defaults(func=cmd_list)

    # pull-logs
    sp = sub.add_parser("pull-logs", help="Скачать журнал выдач и access.log за 3 дня (на Mac)")
    sp.add_argument("--local-dir", default=LOCAL_USERS_DIR, help="Куда сохранить архив")
    sp.set_defaults(func=cmd_pull_logs)

    # menu
    sp = sub.add_parser("menu", help="Интерактивное меню")
    sp.set_defaults(func=cmd_menu)

    return p


# -----------------------------------------------------------------------------
def main():
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except subprocess.CalledProcessError as e:
        out = e.stdout if hasattr(e, "stdout") and e.stdout else str(e)
        die(f"Команда завершилась с ошибкой.\n{out}")
    except Exception as e:
        die(str(e))


if __name__ == "__main__":
    main()
