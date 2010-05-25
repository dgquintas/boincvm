@echo off
REM Windows sucks
REM This .bat ought to be exec'd using an appropriate path
REM ie, the one pointing to wherever VBoxHeadless resides
if "%2" == "" goto error
@echo on
"DisableCmdWindow.vbs" %1 %2
@echo off
goto end

:error
echo Syntax: %0 VBoxPath VM

:end 
echo Done!
