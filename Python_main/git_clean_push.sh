#!/bin/bash

# Очистка от файлов .DS_Store
echo "Удаляю .DS_Store из индекса..."
git rm -r --cached .DS_Store 2>/dev/null
git rm -r --cached */.DS_Store 2>/dev/null
git rm -r --cached */*/.DS_Store 2>/dev/null

# Добавление .DS_Store в .gitignore, если еще нет
if ! grep -q ".DS_Store" .gitignore 2>/dev/null; then
  echo ".DS_Store" >> .gitignore
  echo "Добавил .DS_Store в .gitignore"
fi

# Добавляем все изменения
git add .

# Создаем коммит с текущей датой и временем
commit_message="Auto commit on $(date '+%Y-%m-%d %H:%M:%S')"
git commit -m "$commit_message"

# Отправляем изменения на удаленный репозиторий
git push origin main

echo "Все изменения добавлены, закоммичены и отправлены."
