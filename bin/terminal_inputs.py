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
        choices=["all", "raw", "GNGNS", "GPGGA", "GNGGA", "GPGSA", "GNGSA", "GPVTG", "GNVTG", "GPRMC", "GNRMC", "GPGSV", "ROT", "GPROT", "GNROT", "GNGST", "GNZDA", "GNTHS", "PASHR" ],
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


def terminal_inputs_bidirectional():
    """Parse terminal inputs for bidirectional NMEA connector and return the arguments"""

    parser = argparse.ArgumentParser(
        prog="keelson_connector_nmea_bidirectional",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Bidirectional Keelson NMEA Connector - converts between NMEA and Keelson messages"
    )
    
    # Basic configuration
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
        required=True,
        help="Entity being a unique id representing an entity within the realm ex, landkrabba",
    )
    parser.add_argument(
        "-s",
        "--source-id",
        default="rutx/0",
        type=str,
        required=False,
        help="Source identifier for NMEA input messages"
    )

    # Input configuration (for NMEA -> Keelson)
    parser.add_argument(
        "--publish",
        choices=["all", "raw", "GNGNS", "GPGGA", "GNGGA", "GPGSA", "GNGSA", "GPVTG", "GNVTG", 
                "GPRMC", "GNRMC", "GPGSV", "ROT", "GPROT", "GNROT", "GNGST", "GNZDA", "GNTHS", "PASHR"],
        type=str,
        required=False,
        action="append",
        help="NMEA message types to publish as Keelson messages"
    )
    
    # Output configuration (for Keelson -> NMEA)
    parser.add_argument(
        "--output-only",
        action="store_true",
        help="Run in output-only mode (no NMEA input processing)"
    )
    
    parser.add_argument(
        "--output-udp",
        action="append",
        type=str,
        help="UDP output destination in format host:port (can be specified multiple times)"
    )
    
    parser.add_argument(
        "--output-tcp",
        action="append", 
        type=str,
        help="TCP output destination in format host:port (can be specified multiple times)"
    )
    
    parser.add_argument(
        "--output-serial",
        action="append",
        type=str,
        help="Serial output in format device[:baudrate] (can be specified multiple times)"
    )
    
    parser.add_argument(
        "--output-multicast",
        action="append",
        type=str,
        help="Multicast output in format group:port (can be specified multiple times)"
    )
    
    parser.add_argument(
        "--output-socat",
        action="append",
        type=str,
        help="SOCAT command for custom output (can be specified multiple times)"
    )
    
    parser.add_argument(
        "--nmea-sentences",
        action="append",
        type=str,
        help="NMEA sentences to generate from Keelson messages (comma-separated), choices: GGA,RMC,VTG,ROT,HDT,PASHR,ZDA"
    )
    
    parser.add_argument(
        "--nmea-rate-hz",
        type=float,
        default=1.0,
        help="Rate in Hz to generate NMEA sentences"
    )
    
    parser.add_argument(
        "--nmea-talker-id",
        type=str,
        default="GP",
        help="NMEA talker ID (GP, GN, etc.)"
    )
    
    parser.add_argument(
        "--subscribe-sources",
        action="append",
        type=str,
        help="Source patterns to subscribe to for Keelson messages (default: source-id/**)"
    )

    # Legacy arguments for compatibility
    parser.add_argument(
        "--udp-port",
        type=int,
        required=False,
        default=8500,
        help="UDP port to listen to for incoming NMEA data (legacy)",
    )

    parser.add_argument(
        "-f", 
        "--frame-id", 
        type=str,
        default=None, 
        required=False
    )

    # Parse arguments
    args = parser.parse_args()
    
    # Set default publish list if not specified and not output-only
    if not args.output_only and not args.publish:
        args.publish = ["all"]
    
    # Validate that at least one mode is specified
    has_input = not args.output_only
    has_output = any([
        args.output_udp, args.output_tcp, args.output_serial, 
        args.output_multicast, args.output_socat, args.nmea_sentences
    ])
    
    if not has_input and not has_output:
        parser.error("Must specify either input processing or output configuration")

    return args
