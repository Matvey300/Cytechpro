#!/usr/bin/env python3
# file: vpn_users.py

import os, json, uuid, argparse, datetime, urllib.parse, sys, textwrap

# ====== НАСТРОЙКИ ПО УМОЛЧАНИЮ ======
BASE_DIR     = "/Users/Matvej1/AWS/Users"
USERS_JSON   = os.path.join(BASE_DIR, "users.json")
ACTIVITY_LOG = os.path.join(BASE_DIR, "activity.log")

DOMAIN = "matvey300.duckdns.org"
PORT   = 443
SNI    = DOMAIN
ALPN   = "http/1.1"  # у тебя так на сервере
# ====================================

def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def ensure_dirs():
    os.makedirs(BASE_DIR, exist_ok=True)
    if not os.path.exists(USERS_JSON):
        with open(USERS_JSON, "w") as f:
            json.dump({"users": []}, f, ensure_ascii=False, indent=2)

def load_db():
    ensure_dirs()
    with open(USERS_JSON, "r") as f:
        return json.load(f)

def save_db(db):
    with open(USERS_JSON, "w") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

def append_activity(line: str):
    with open(ACTIVITY_LOG, "a") as f:
        f.write(f"{now_iso()} {line}\n")

def sanitize_filename(name: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in name.strip())

def make_vless_link(u: str, name: str, host: str, port: int, sni: str, alpn: str) -> str:
    q = {
        "security": "tls",
        "encryption": "none",
        "type": "tcp",
        "sni": sni,
        "alpn": alpn
    }
    query = urllib.parse.urlencode(q, doseq=True)
    tag = urllib.parse.quote(name, safe="")
    return f"vless://{u}@{host}:{port}?{query}#{tag}"

# ---- совместимость со старой схемой (uuids: [...]) ----
def normalize_entry(entry):
    if "keys" in entry:
        return entry
    keys = []
    for u in entry.get("uuids", []):
        keys.append({"uuid": u, "status": "active", "issued_at": entry.get("issued_at", now_iso())})
    entry["keys"] = keys
    entry.pop("uuids", None)
    return entry

def add_user(name: str, acc_type: int, count: int, host: str, port: int, sni: str, alpn: str):
    db = load_db()
    keys = []
    for _ in range(count):
        u = str(uuid.uuid4())
        keys.append({"uuid": u, "status": "active", "issued_at": now_iso()})
    policy = (
        {"mode": "unlimited"} if acc_type == 1 else
        {"mode": "single_session"} if acc_type == 2 else
        {"mode": "per_device", "limit": count}
    )
    entry = {
        "name": name,
        "type": acc_type,
        "policy": policy,
        "keys": keys,
        "domain": host, "port": port, "sni": sni, "alpn": alpn,
        "issued_at": now_iso(),
        "status": "active",
    }
    # сохранить
    db["users"].append(entry)
    save_db(db)

    # ссылки в файл
    fname = f"{datetime.datetime.now().strftime('%Y-%m-%d')}_{sanitize_filename(name)}_links.txt"
    out_path = os.path.join(BASE_DIR, fname)
    with open(out_path, "w") as f:
        f.write(f"# {name} (type {acc_type}) {now_iso()}\n")
        for k in keys:
            f.write(make_vless_link(k["uuid"], name, host, port, sni, alpn) + "\n")

    append_activity(f"ISSUE name='{name}' type={acc_type} keys={len(keys)} file='{fname}'")
    return [k["uuid"] for k in keys], out_path

def list_active():
    db = load_db()
    out = []
    for e in db.get("users", []):
        e = normalize_entry(e)
        for k in e["keys"]:
            if k.get("status", "active") == "active":
                out.append((e["name"], k["uuid"], e.get("type"), e.get("policy", {})))
    return out

def revoke_by_uuid(u: str):
    db = load_db()
    found = False
    for e in db.get("users", []):
        e = normalize_entry(e)
        for k in e["keys"]:
            if k["uuid"] == u and k.get("status","active") == "active":
                k["status"] = "revoked"
                k["revoked_at"] = now_iso()
                found = True
                append_activity(f"REVOKE uuid={u} name='{e.get('name','')}'")
                break
    if found:
        save_db(db)
    return found

def revoke_by_name(name: str):
    db = load_db()
    cnt = 0
    for e in db.get("users", []):
        e = normalize_entry(e)
        if e.get("name","").strip().lower() == name.strip().lower():
            for k in e["keys"]:
                if k.get("status","active") == "active":
                    k["status"] = "revoked"
                    k["revoked_at"] = now_iso()
                    cnt += 1
            e["status"] = "revoked"
    if cnt > 0:
        save_db(db)
        append_activity(f"REVOKE_ALL name='{name}' keys={cnt}")
    return cnt

def export_active_uuid_list():
    act = list_active()
    uuids = [u for _, u, _, _ in act]
    txt_path = os.path.join(BASE_DIR, "active_uuids.txt")
    with open(txt_path, "w") as f:
        for u in uuids:
            f.write(u + "\n")
    # заодно JSON-вставка для Xray
    clients = [{"id": u} for u in uuids]
    json_snippet = json.dumps(clients, ensure_ascii=False, indent=2)
    append_activity(f"EXPORT_ACTIVE count={len(uuids)} file='active_uuids.txt'")
    return txt_path, json_snippet, len(uuids)

def help_text():
    return textwrap.dedent("""
    Типы ключей:
      1 — Безлимитный ключ (одно UUID, не ограничиваем устройства на уровне учёта)
      2 — Один ключ = одна активная сессия (ограничение будем реализовывать серверной политикой)
      3 — N ключей, каждый предназначен для одного устройства (–n N)

    Замечание: revoke помечает ключи как 'revoked' в учётной базе и логах.
    Чтобы это вступило в силу на сервере Xray, нужно обновить список клиентских UUID (см. 'Export active UUIDs').
    """)

def menu():
    while True:
        print("\n=== VPN Users Menu ===")
        print("1) Issue keys")
        print("2) List active keys")
        print("3) Revoke key by UUID")
        print("4) Revoke ALL keys by Name")
        print("5) Export active UUIDs (file + JSON snippet)")
        print("h) Help on types")
        print("q) Quit")
        choice = input("Select: ").strip().lower()
        if choice == "1":
            name = input("User name: ").strip()
            t = int(input("Type (1/2/3): ").strip())
            n = 1
            if t == 3:
                n = int(input("How many keys (N): ").strip())
            uuids, path = add_user(name, t, n, DOMAIN, PORT, SNI, ALPN)
            print(f"Issued {len(uuids)} key(s). Links saved: {path}")
        elif choice == "2":
            items = list_active()
            if not items:
                print("No active keys.")
            else:
                for i,(name,u,t,policy) in enumerate(items,1):
                    print(f"{i:3d}. {name:30s}  UUID={u}  type={t} policy={policy}")
                print(f"Total: {len(items)}")
        elif choice == "3":
            u = input("UUID to revoke: ").strip()
            ok = revoke_by_uuid(u)
            print("Revoked." if ok else "Not found or already revoked.")
        elif choice == "4":
            name = input("Exact name to revoke all: ").strip()
            cnt = revoke_by_name(name)
            print(f"Revoked keys: {cnt}")
        elif choice == "5":
            p, snippet, n = export_active_uuid_list()
            print(f"Written: {p} (count={n})")
            print("\nJSON for xray `settings.clients`:\n", snippet)
        elif choice == "h":
            print(help_text())
        elif choice == "q":
            return
        else:
            print("Unknown option.")

def cli():
    ap = argparse.ArgumentParser(description="Управление VLESS-ключами (выдача/список/revoke/экспорт).",
                                 epilog="Без параметров запускается интерактивное меню.")
    sub = ap.add_subparsers(dest="cmd")

    a_issue = sub.add_parser("issue", help="Выдать ключ(и)")
    a_issue.add_argument("name")
    a_issue.add_argument("type", type=int, choices=[1,2,3])
    a_issue.add_argument("-n","--num", type=int, default=1, help="Количество ключей для типа 3")
    a_issue.add_argument("--host", default=DOMAIN)
    a_issue.add_argument("--port", type=int, default=PORT)
    a_issue.add_argument("--sni",  default=SNI)
    a_issue.add_argument("--alpn", default=ALPN)

    sub.add_parser("list", help="Показать активные ключи")

    a_rev_u = sub.add_parser("revoke-uuid", help="Отозвать по UUID")
    a_rev_u.add_argument("uuid")

    a_rev_n = sub.add_parser("revoke-name", help="Отозвать все ключи по имени")
    a_rev_n.add_argument("name")

    sub.add_parser("export-active", help="Сохранить active UUIDs в файл и напечатать JSON")

    sub.add_parser("help-types", help="Справка по типам")

    args = ap.parse_args()
    if not args.cmd:
        menu(); return

    if args.cmd == "issue":
        uuids, path = add_user(args.name, args.type, (args.num if args.type==3 else 1),
                               args.host, args.port, args.sni, args.alpn)
        print("\n=== LINKS ===")
        for u in uuids:
            print(make_vless_link(u, args.name, args.host, args.port, args.sni, args.alpn))
        print(f"\nSaved: {path}\nDB: {USERS_JSON}\nLog: {ACTIVITY_LOG}")
    elif args.cmd == "list":
        items = list_active()
        if not items:
            print("No active keys."); return
        for i,(name,u,t,policy) in enumerate(items,1):
            print(f"{i:3d}. {name:30s}  UUID={u}  type={t} policy={policy}")
        print(f"Total: {len(items)}")
    elif args.cmd == "revoke-uuid":
        print("Revoked." if revoke_by_uuid(args.uuid) else "Not found or already revoked.")
    elif args.cmd == "revoke-name":
        cnt = revoke_by_name(args.name)
        print(f"Revoked keys: {cnt}")
    elif args.cmd == "export-active":
        p, snippet, n = export_active_uuid_list()
        print(f"Written: {p} (count={n})")
        print("\nJSON for xray `settings.clients`:\n", snippet)
    elif args.cmd == "help-types":
        print(help_text())

if __name__ == "__main__":
    cli()