import argparse


def terminal_inputs():
    """Parse the terminal inputs and return the arguments"""

    parser = argparse.ArgumentParser(
        prog="keelson_connector_nmea",
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
        default="rutx/0",
        type=str,
        required=False
    )

    parser.add_argument(
        "--udp-port",
        type=int,
        required=False,
        default=8500,
        help="UDP port to listen to for incoming NMEA data",
    )

    parser.add_argument(
        "--publish",
        choices=["all", "raw", "GNGNS", "GPGGA", "GPGSA", "GPVTG", "GPRMC", "GPGSV", "ROT" ],
        type=str,
        required=False,
        action="append",
    )

    parser.add_argument(
        "-f", 
        "--frame-id", 
        type=str,
        default=None, 
        required=False
    )

    # Parse arguments and start doing our thing
    args = parser.parse_args()

    return args
