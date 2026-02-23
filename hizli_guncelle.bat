@echo off
echo.
echo ============================================
echo   VERGiAI - Hizli Guncelleme
echo ============================================
echo.

echo [1/3] GitHub'dan cekilyor...
git pull https://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@github.com/webdedesign/vergiai.git main 2>nul
echo OK
echo.

echo [2/3] Yerel dosyalar kontrol...
git status
echo.

echo [3/3] GitHub'a gonderiliyor...
git push https://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@github.com/webdedesign/vergiai.git master:main
if errorlevel 1 (
    echo HATA! Push basarisiz!
    pause
    exit /b 1
)

echo.
echo ============================================
echo   BASARILI - GitHub guncellendi!
echo   Streamlit 1-2 dk sonra yenilenecek
echo ============================================
echo.
pause
