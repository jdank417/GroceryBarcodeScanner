import sys
import os

def is_venv():
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        return True
    if 'VIRTUAL_ENV' in os.environ:
        return True
    return False

if is_venv():
    print("Virtual environment is active.")
else:
    print("Virtual environment is not active.")