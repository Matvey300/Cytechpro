import os
import subprocess


def run_git_command(command):
    """Запуск git-команды и возврат результата."""
    try:
        result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
        return result.decode("utf-8").strip()
    except subprocess.CalledProcessError as e:
        return f"Ошибка: {e.output.decode('utf-8').strip()}"


def check_git_status():
    print("=== Проверка состояния Git-репозитория ===\n")

    # 1. Проверка, является ли директория git-репозиторием
    if not os.path.isdir(".git"):
        print("Текущая папка не является git-репозиторием.")
        return

    # 2. Текущая ветка
    branch = run_git_command("git rev-parse --abbrev-ref HEAD")
    print(f"Текущая ветка: {branch}")

    # 3. Удалённые репозитории
    remotes = run_git_command("git remote -v")
    print("\nУдалённые репозитории:")
    print(remotes if remotes else "Нет настроенных remote.")

    # 4. Изменения в рабочей директории
    status = run_git_command("git status -s")
    if status:
        print("\nЕсть несохранённые изменения:\n")
        print(status)
        print("\nРекомендуемые команды:")
        print("  git add .")
        print('  git commit -m "Ваш комментарий"')
        print(f"  git push origin {branch}")
    else:
        print("\nНет несохранённых изменений.")

    # 5. Проверка доступности pull
    print("\nПроверка синхронизации с удалённым репозиторием...")
    ahead = run_git_command("git rev-list --count HEAD ^origin/" + branch)
    behind = run_git_command("git rev-list --count origin/" + branch + " ^HEAD")

    if ahead.isdigit() and behind.isdigit():
        print(f"  Локальных коммитов, не отправленных в remote: {ahead}")
        print(f"  Коммитов на remote, не загруженных локально: {behind}")
        if ahead != "0":
            print(f"  → Нужно выполнить: git push origin {branch}")
        if behind != "0":
            print(f"  → Нужно выполнить: git pull origin {branch}")
    else:
        print("  Не удалось проверить синхронизацию с remote.")


if __name__ == "__main__":
    check_git_status()
