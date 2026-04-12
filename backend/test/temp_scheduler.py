
import argparse
import logging
import os
import sys
from pathlib import Path
from pprint import pformat

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from backend.agents.scheduling_agent import SchedulingAgent
agent = SchedulingAgent()
result = agent.run("Book a meeting tomorrow at 4:30 p.m.")
print(result["message"])