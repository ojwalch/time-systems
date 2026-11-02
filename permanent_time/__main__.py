"""python -m permanent_time  ->  output/ (the charts, their data files and the checks)"""
from . import checks, daylight

daylight.main()
checks.main()
