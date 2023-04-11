@REM .\start.bat

wt -p "Windows Powershell" -d . --title "Order Processor" powershell -noExit "python -m inventory_management_system.order_processor reset" ; sleep 1; ^
nt -p "Windows Powershell" -d . --title "World Simulator" powershell -noExit "python -m world_sim" ; sleep 1; ^
nt -p "Windows Powershell" -d . --title "Robot Allocator" powershell -noExit "python -m robot_allocator" ; sleep 1; ^
nt -p "Windows Powershell" -d . --title "Web Order Tracking" powershell -noExit "flask --app inventory_management_system.order_tracking_web_server --debug run" ; sleep 1; ^
nt -p "Windows Powershell" -d . --title "Web World Visualizer" powershell -noExit "node env_visualizer" ; sleep 1; ^
nt -p "Windows Powershell" -d . --title "Fake Order Creator" powershell -noExit "echo waiting...\;sleep 3\; python -m inventory_management_system.fake_order_sender" ; sleep 1; ^
ft -t 1

@REM  fp -t 0 
echo Done