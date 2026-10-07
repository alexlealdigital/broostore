@echo off
setlocal enabledelayedexpansion
title Push para o GitHub
cd /d "%~dp0"

rem =========================================================================
rem push-github.bat - sobe as alteracoes locais para o GitHub com dois cliques
rem
rem Coloque este arquivo DENTRO da pasta do projeto e de dois cliques.
rem O script resolve sozinho (perguntando quando precisar):
rem   - pasta que ainda nao e repositorio git (faz git init)
rem   - repositorio sem "origin" (pergunta a URL do GitHub)
rem   - nome/e-mail do git nao configurados
rem   - projeto Unity sem .gitignore (evita subir a pasta Library)
rem   - branch que ainda nao existe no GitHub (primeiro envio)
rem   - historicos diferentes (repo criado no GitHub com README)
rem =========================================================================

echo ============================================================
echo  Pasta: %cd%
echo ============================================================
echo.

where git >nul 2>nul
if errorlevel 1 goto :sem_git

git rev-parse --is-inside-work-tree >nul 2>nul
if errorlevel 1 goto :sem_repo
goto :repo_ok

:sem_git
echo [ERRO] Git nao encontrado. Instale o Git para Windows:
echo        https://git-scm.com/download/win
goto :fim_erro

:sem_repo
echo Esta pasta ainda nao e um repositorio git.
set "RESP="
set /p "RESP=Iniciar um repositorio git aqui agora? [S/N]: "
if /i not "!RESP!"=="S" goto :fim_erro
git init
if errorlevel 1 goto :fim_erro
git branch -M main

:repo_ok

rem ---------- remoto "origin" ----------
git remote get-url origin >nul 2>nul
if not errorlevel 1 goto :remote_ok
echo Nenhum repositorio remoto "origin" configurado.
set "URL="
set /p "URL=Cole a URL do repositorio no GitHub, ex. https://github.com/usuario/repo.git : "
if "!URL!"=="" goto :fim_erro
git remote add origin "!URL!"
if errorlevel 1 goto :fim_erro

:remote_ok
for /f "delims=" %%u in ('git remote get-url origin') do set "REMOTE_URL=%%u"
echo.
echo ************************************************************
echo  DESTINO ATUAL no GitHub:
echo    !REMOTE_URL!
echo ************************************************************
set "TROCAR="
set /p "TROCAR=Enviar para ESTE repositorio? [S = sim / T = trocar]: "
if /i not "!TROCAR!"=="T" goto :remote_confirmado
set "URL="
set /p "URL=Cole a URL do repositorio certo, ex. https://github.com/usuario/broostore.git : "
if "!URL!"=="" goto :fim_erro
git remote set-url origin "!URL!"
if errorlevel 1 goto :fim_erro
for /f "delims=" %%u in ('git remote get-url origin') do set "REMOTE_URL=%%u"
echo Destino alterado para: !REMOTE_URL!
:remote_confirmado
echo Remoto : !REMOTE_URL!

rem ---------- identidade do git ----------
set "GIT_NAME="
for /f "delims=" %%n in ('git config user.name 2^>nul') do set "GIT_NAME=%%n"
if defined GIT_NAME goto :nome_ok
set /p "GIT_NAME=Seu nome para assinar os commits: "
if "!GIT_NAME!"=="" goto :fim_erro
git config user.name "!GIT_NAME!"
:nome_ok

set "GIT_MAIL="
for /f "delims=" %%e in ('git config user.email 2^>nul') do set "GIT_MAIL=%%e"
if defined GIT_MAIL goto :mail_ok
set /p "GIT_MAIL=Seu e-mail do GitHub: "
if "!GIT_MAIL!"=="" goto :fim_erro
git config user.email "!GIT_MAIL!"
:mail_ok

rem ---------- branch atual ----------
set "BRANCH="
for /f "delims=" %%b in ('git symbolic-ref --short HEAD 2^>nul') do set "BRANCH=%%b"
if not defined BRANCH set "BRANCH=main"
echo Branch : !BRANCH!
echo.

rem ---------- projeto Unity sem .gitignore ----------
if not exist "Assets\" goto :gi_ok
if not exist "ProjectSettings\" goto :gi_ok
if exist ".gitignore" goto :gi_ok
echo [AVISO] Projeto Unity sem .gitignore: o git tentaria subir a pasta
echo         Library inteira ^(gigabytes^) e o GitHub rejeita arquivos
echo         maiores que 100 MB.
set "RESP="
set /p "RESP=Criar um .gitignore padrao de Unity agora? [S/N]: "
if /i not "!RESP!"=="S" goto :gi_ok
(
echo [Ll]ibrary/
echo [Tt]emp/
echo [Oo]bj/
echo [Bb]uild/
echo [Bb]uilds/
echo [Ll]ogs/
echo [Uu]ser[Ss]ettings/
echo [Mm]emoryCaptures/
echo .vs/
echo .vscode/
echo .idea/
echo *.csproj
echo *.sln
echo *.suo
echo *.user
echo *.pidb
echo *.pdb
echo *.mdb
echo *.apk
echo *.aab
echo sysinfo.txt
) > ".gitignore"
echo .gitignore criado.
echo.
:gi_ok

rem ---------- ha alteracoes? ----------
set "TMPSTAT=%TEMP%\_gitstat_%RANDOM%.txt"
git status --porcelain > "!TMPSTAT!"
set "HAS=0"
for %%F in ("!TMPSTAT!") do if %%~zF GTR 0 set "HAS=1"
del "!TMPSTAT!" >nul 2>nul

echo --- O que sera enviado ---------------------------------------
git status --short
echo --------------------------------------------------------------
echo.

if "!HAS!"=="0" goto :sem_mudancas

git add -A
if errorlevel 1 goto :erro_add

set "MSG="
set /p "MSG=Mensagem do commit [Enter = automatica]: "
if not "!MSG!"=="" goto :commitar
set "STAMP="
for /f "delims=" %%d in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HH-mm" 2^>nul') do set "STAMP=%%d"
if not defined STAMP set "STAMP=%date% %time:~0,5%"
set "MSG=Atualizacao !STAMP!"

:commitar
git commit -m "!MSG!"
if errorlevel 1 goto :erro_commit
goto :tentar_push

:sem_mudancas
echo Nenhuma alteracao nova para commitar. Vou so conferir se ha commits
echo locais ainda nao enviados.
echo.

rem ---------- sincronizar e enviar ----------
:tentar_push
echo --- Verificando o GitHub ---------------------------------------
git ls-remote --exit-code --heads origin !BRANCH! >nul
set "LSR=!errorlevel!"
if "!LSR!"=="2" goto :primeiro_envio
if not "!LSR!"=="0" goto :erro_acesso

echo --- Sincronizando com o GitHub antes de enviar ---------------
git pull --rebase origin !BRANCH!
if errorlevel 1 goto :erro_pull

:push
echo.
echo --- Enviando para o GitHub -------------------------------------
git push -u origin !BRANCH!
if errorlevel 1 goto :erro_push
goto :ok

:primeiro_envio
echo O branch !BRANCH! ainda nao existe no GitHub: sera criado no primeiro envio.
goto :push

rem ---------- erros ----------
:erro_acesso
echo.
echo [ERRO] Nao consegui acessar o repositorio no GitHub. Verifique:
echo   - internet
echo   - se a URL do remoto esta certa: !REMOTE_URL!
echo   - se voce tem permissao no repositorio e esta logado no GitHub
echo     ^(o Git abre uma janela de login do GitHub quando precisa^)
goto :fim_erro

:erro_add
echo.
echo [ERRO] "git add" falhou. Veja a mensagem acima.
goto :fim_erro

:erro_commit
echo.
echo [ERRO] "git commit" falhou. Veja a mensagem acima.
goto :fim_erro

:erro_pull
echo.
echo [ERRO] Nao foi possivel sincronizar com o GitHub: conflito ou
echo        historicos diferentes ^(comum quando o repo foi criado no
echo        GitHub com README e a pasta local foi iniciada separada^).
git rebase --abort >nul 2>nul
echo.
echo   1 = Mesclar os historicos e tentar de novo ^(recomendado^)
echo   2 = Cancelar e resolver manualmente
set "OPC="
set /p "OPC=Escolha [1/2]: "
if not "!OPC!"=="1" goto :fim_erro
git pull origin !BRANCH! --allow-unrelated-histories --no-rebase --no-edit
if errorlevel 1 goto :erro_merge
goto :push

:erro_merge
echo.
echo [ERRO] A mescla gerou conflitos. Abra os arquivos listados acima por
echo        "both added" ou "both modified", escolha qual versao manter,
echo        depois rode: git add -A ^& git commit -m "merge"
echo        e de dois cliques neste script de novo.
goto :fim_erro

:erro_push
echo.
echo [ERRO] "git push" falhou. Causas comuns:
echo   - rejected / non-fast-forward: o GitHub tem commits que voce nao tem
echo     ^(rode o script de novo para sincronizar^)
echo   - GH001 / arquivo maior que 100 MB: remova o arquivo grande ou
echo     coloque-o no .gitignore e refaca o commit
echo   - permission denied / 403: sem permissao ou login expirado
goto :fim_erro

:fim_erro
echo.
pause
exit /b 1

:ok
echo.
echo ============================================================
echo  Feito! Alteracoes enviadas para o branch "!BRANCH!" no GitHub.
echo ============================================================
echo.
pause
exit /b 0
