@echo off
REM ============================================================
REM  Сборка десктопного приложения HR Portal в hr_portal.exe
REM  Требуется: Windows, Python 3.10+ (с галочкой "Add to PATH")
REM ============================================================

echo [1/3] Установка зависимостей...
python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto :error

echo [2/3] Сборка exe (one-file, без окна консоли)...
python -m PyInstaller ^
  --noconfirm --clean --onefile --windowed ^
  --name hr_portal ^
  --collect-submodules openpyxl ^
  hr_portal.py
if errorlevel 1 goto :error

echo [3/3] Готово!
echo   Файл: %CD%\dist\hr_portal.exe
echo   Запускайте его двойным кликом — база данных создастся автоматически.
pause
exit /b 0

:error
echo ОШИБКА сборки. Проверьте, что установлен Python и PyInstaller.
pause
exit /b 1
