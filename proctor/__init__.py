"""
AI Proctoring & Anti-Cheat Suite Package
"""

import os
import sys
import ctypes

# Fix MediaPipe C++ Protobuf text format parsing crash on Windows when Python is installed in C:\Users\...
try:
    import mediapipe as mp
    import mediapipe.python.solution_base as _sb
    import mediapipe.python._framework_bindings.calculator_graph as _cg

    def _get_short(path: str) -> str:
        if not path:
            return path
        norm = os.path.normpath(os.path.abspath(path))
        if os.path.exists(norm) and sys.platform == "win32":
            buf = ctypes.create_unicode_buffer(500)
            if ctypes.windll.kernel32.GetShortPathNameW(norm, buf, 500) > 0 and buf.value:
                return buf.value
        return norm

    _orig_sb_init = _sb.SolutionBase.__init__

    def _patched_sb_init(
        self,
        binary_graph_path=None,
        graph_config=None,
        calculator_params=None,
        graph_options=None,
        side_inputs=None,
        outputs=None,
        stream_type_hints=None,
    ):
        if binary_graph_path:
            root_path = os.sep.join(os.path.abspath(_sb.__file__).split(os.sep)[:-3])
            full_path = _get_short(os.path.join(root_path, binary_graph_path))
            _sb.resource_util.set_resource_dir(_get_short(root_path))
            validated_graph = _sb.validated_graph_config.ValidatedGraphConfig()
            validated_graph.initialize(binary_graph_path=full_path)
            canonical_graph_config_proto = self._initialize_graph_interface(
                validated_graph, side_inputs, outputs, stream_type_hints
            )
            if calculator_params:
                self._modify_calculator_options(
                    canonical_graph_config_proto, calculator_params
                )
            if graph_options:
                self._set_extension(
                    canonical_graph_config_proto.graph_options, graph_options
                )
            self._graph = _cg.CalculatorGraph(validated_graph_config=validated_graph)
            self._simulated_timestamp = 0
            self._graph_outputs = {}

            def callback(stream_name, output_packet):
                self._graph_outputs[stream_name] = output_packet

            for stream_name in self._output_stream_type_info.keys():
                self._graph.observe_output_stream(stream_name, callback, True)

            self._input_side_packets = {
                name: self._make_packet(self._side_input_type_info[name], data)
                for name, data in (side_inputs or {}).items()
            }
            self._graph.start_run(self._input_side_packets)
        else:
            _orig_sb_init(
                self,
                binary_graph_path=binary_graph_path,
                graph_config=graph_config,
                calculator_params=calculator_params,
                graph_options=graph_options,
                side_inputs=side_inputs,
                outputs=outputs,
                stream_type_hints=stream_type_hints,
            )

    _sb.SolutionBase.__init__ = _patched_sb_init

except Exception:
    pass

__version__ = "2.0.0"
__author__ = "Production AI Team"
