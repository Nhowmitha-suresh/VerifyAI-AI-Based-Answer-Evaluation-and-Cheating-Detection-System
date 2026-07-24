"""
AI Proctoring & Anti-Cheat Suite Package
"""

import os
# Suppress C++ glog / absl protobuf graph logging at process start
os.environ["GLOG_minloglevel"] = "3"
os.environ["GLOG_stderrthreshold"] = "3"
os.environ["GLOG_logtostderr"] = "0"
os.environ["GLOG_v"] = "0"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

__version__ = "2.0.0"
__author__ = "Production AI Team"
