@echo off

set "AUTOMACAO_OC_ROOT=C:\ARQUIVOS REDE\AUTOMACAO OC"
set "AUTOMACAO_OC_READY_CHECK_INTERVAL_SECONDS=1.5"
set "AUTOMACAO_OC_READY_STABLE_CHECKS=2"

cd /d C:\Projetos\silo-automacao

set "PYTHONPATH=C:\Projetos\silo-automacao\src"

echo =============================== >> "C:\ARQUIVOS REDE\AUTOMACAO OC\logs\agendador_execucao.log"
echo Execucao iniciada em %date% %time% >> "C:\ARQUIVOS REDE\AUTOMACAO OC\logs\agendador_execucao.log"

call C:\Projetos\silo-automacao\.venv\Scripts\python.exe -m auto_processar_pasta >> "C:\ARQUIVOS REDE\AUTOMACAO OC\logs\agendador_execucao.log" 2>&1

echo Execucao finalizada em %date% %time% >> "C:\ARQUIVOS REDE\AUTOMACAO OC\logs\agendador_execucao.log"
echo =============================== >> "C:\ARQUIVOS REDE\AUTOMACAO OC\logs\agendador_execucao.log"