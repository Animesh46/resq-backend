import os
from modules import gemini

print('GEMINI_MODEL', gemini.GEMINI_MODEL)
print('cooldown until', getattr(gemini, '_quota_exhausted_until', None))
try:
    gemini._call_model('test prompt')
except Exception as e:
    print('caught', e)
