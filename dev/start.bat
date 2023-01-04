@REM .\start.bat

wt -p "Windows Powershell" --title "MQTT Local Broker" powershell -noExit "mosquitto -v" ; ^
 nt -p "Windows Powershell" -d ./inventory_management_system --title "Order Processor" powershell -noExit "python .\order_processor.py reset" ; ^
 nt -p "Windows Powershell" -d ./inventory_management_system --title "Web Order Tracking" powershell -noExit "flask.exe --app order_tracking_web_server --debug run" ; ^
 nt -p "Windows Powershell" -d ./inventory_management_system --title "Fake Task Processor" powershell -noExit "python .\fake_task_processor.py" ; ^
 nt -p "Windows Powershell" -d ./inventory_management_system --title "Fake Order Creator" powershell -noExit "echo waiting...\;sleep 3\; python .\fake_order_sender.py" ; ^
 ft -t 1

@REM  fp -t 0 
echo Done