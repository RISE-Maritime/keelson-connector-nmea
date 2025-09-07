import argparse


def terminal_inputs():
    """Parse the terminal inputs and return the arguments"""

    parser = argparse.ArgumentParser(
        prog="keelson_connector_anavs",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-l",
        "--log-level",
        type=int,
        default=30,
        help="Log level 10=DEBUG, 20=INFO, 30=WARN, 40=ERROR, 50=CRITICAL 0=NOTSET",
    )
    parser.add_argument(
        "--connect",
        action="append",
        type=str,
        help="Endpoints to connect to, in case multicast is not working.",
    )
    parser.add_argument(
        "-r",
        "--realm",
        default="rise",
        type=str,
        help="Unique id for a domain/realm to connect ex. rise",
    )
    parser.add_argument(
        "-e",
        "--entity-id",
        type=str,
        help="Entity being a unique id representing an entity within the realm ex, landkrabba",
    )

    parser.add_argument(
        "-s",
        "--source-id",
        default="anavs/0",
        type=str,
        required=False
    )

    parser.add_argument(
        "--anavs-host",
        type=str,
        required=False,
        default="192.168.1.124",
        help="ANavS device IP address",
    )

    parser.add_argument(
        "--anavs-port",
        type=int,
        required=False,
        default=6001,
        help="ANavS device port for binary protocol",
    )

    parser.add_argument(
        "--publish",
        choices=["all", "raw", "location_fix", "ecef_position", "velocity", "acceleration", "attitude", "utc_time", "gps_timing", "result_code", "satellites_used", "accuracy", "timing", "status"],
        type=str,
        required=False,
        action="append",
        default=["all"],
        help="Data types to publish (default: all)"
    )

    parser.add_argument(
        "-f", 
        "--frame-id", 
        type=str,
        default=None, 
        required=False
    )

    parser.add_argument(
        "--input-mode",
        choices=["tcp", "stdin"],
        type=str,
        default="tcp",
        help="Input mode: tcp (connect to ANavS device) or stdin (read from stdin)"
    )

    # Parse arguments and start doing our thing
    args = parser.parse_args()

    return args
