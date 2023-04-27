@REM .\start.bat

wt -p "Windows Powershell" -d . --title "Order Processor" powershell -noExit "python -m inventory_management_system.order_processor reset" ; ^
nt -p "Windows Powershell" -d . --title "World Simulator" powershell -noExit "python -m world_sim" ; ^
nt -p "Windows Powershell" -d . --title "Robot Allocator" powershell -noExit "python -m robot_allocator" ; ^
nt -p "Windows Powershell" -d . --title "Web Order Tracking" powershell -noExit "flask --app inventory_management_system.order_tracking_web_server --debug run --host=0.0.0.0" ; ^
nt -p "Windows Powershell" -d . --title "Web World Visualizer" powershell -noExit "node env_visualizer" ; ^
nt -p "Windows Powershell" -d . --title "Fake Order Creator" powershell -noExit "echo waiting...\;sleep 3\; python -m inventory_management_system.fake_order_sender" ; ^
ft -t 1

@REM  fp -t 0 
echo Done