@echo off
TITLE Singularity Core - Installer
CLS
echo.
echo  =============================================
echo    SINGULARITY CORE - WINDOWS INSTALLER
echo  =============================================
echo.
echo  Iniciando despliegue de estructura y configuracion...
echo.

:: Llama al script de PowerShell saltándose las restricciones
PowerShell -NoProfile -ExecutionPolicy Bypass -Command "& './setup-windows.ps1'"

PAUSE
