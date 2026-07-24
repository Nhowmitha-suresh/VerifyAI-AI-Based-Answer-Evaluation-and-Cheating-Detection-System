"""
AI Proctoring Suite - Top Level Entrypoint
Imports and executes the modular proctoring package.
"""

import os
# Suppress C++ glog / absl protobuf graph logging before process imports
os.environ["GLOG_minloglevel"] = "3"
os.environ["GLOG_stderrthreshold"] = "3"
os.environ["GLOG_logtostderr"] = "0"
os.environ["GLOG_v"] = "0"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

from proctor.main import main

if __name__ == "__main__":
    main()
