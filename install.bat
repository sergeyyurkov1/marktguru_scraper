@echo off

:start
cls

pip install --user virtualenv

python -m virtualenv venv

call .\venv\Scripts\activate

pip install -r requirements.txt

exit