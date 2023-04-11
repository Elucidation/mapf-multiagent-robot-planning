@REM .\start.bat

wt -p "Windows Powershell" -d . --title "Order Processor" powershell -noExit "python -m inventory_management_system.order_processor reset" ; ^
nt -p "Windows Powershell" -d . --title "Web Order Tracking" powershell -noExit "flask --app inventory_management_system.order_tracking_web_server --debug run" ; ^
nt -p "Windows Powershell" -d . --title "Fake Task Processor" powershell -noExit "python -m inventory_management_system.fake_task_processor" ; ^
nt -p "Windows Powershell" -d . --title "Fake Order Creator" powershell -noExit "echo waiting...\;sleep 3\; python -m inventory_management_system.fake_order_sender" ; ^
ft -t 1

@REM  fp -t 0 
echo Done