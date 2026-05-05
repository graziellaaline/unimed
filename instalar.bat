@echo off
echo ============================================
echo  Instalacao - Auditoria Unimed
echo ============================================
cd /d "%~dp0"

echo Criando ambiente virtual...
python -m venv venv
if errorlevel 1 (
    echo ERRO: Python nao encontrado. Instale o Python 3.10+.
    pause
    exit /b 1
)

echo Instalando dependencias...
call venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt

echo.
echo ============================================
echo  Instalacao concluida!
echo  Execute iniciar.bat para abrir o sistema.
echo ============================================
pause
