#!flask/bin/python
from flask import Flask, jsonify, abort, request, make_response
import logging.config
import inspect
import os
import ssl
import ConfigParser
import argparse
from honeywell_thermostat.thermostat import Honeywell
'''
http://
curl -k "Content-Type: application/json" -X POST -d '{"thermostat":"living oom"}' http://localhost:5000/thermostat/on
https://
curl -i -k -H "Content-Type: application/json" -X POST -d '{"thermostat":"living room"}' https://localhost:5000/thermostat/off
'''
app = Flask(__name__)
ROOT = "/thermostat/"
thermostats = None
username = None
password = None


@app.errorhandler(404)
def not_found(error):
    logger = logging.getLogger(get_logger_name())
    logger.critical(error)
    return make_response(jsonify({'error': error}), 404)


def get_thermostat_info(req, get_values):
    try:
        thermostat_name = str(req.json['thermostat'])
        if get_values:
            amount = req.json.get('amount', 1)
            hold_time = req.json.get('hold_time', 1)
            return thermostats[thermostat_name], thermostat_name, amount, hold_time
        else:
            return thermostats[thermostat_name], thermostat_name
    except:
        abort(400, "bad request:" + str(req))


def get_current_temperature(status):
    return status['latestData']['uiData']["DispTemperature"]


@app.route(ROOT + 'status', methods=['POST'])
def status():
    logger = logging.getLogger(get_logger_name())
    logger.debug("starting")
    device_id, thermostat_name, amount, hold_time = get_thermostat_info(request, True)
    honeywell = Honeywell(username, password, device_id)
    honeywell.cooler(amount, hold_time)
    return jsonify(honeywell.get_status()), 201


@app.route(ROOT + 'current_temperature', methods=['POST'])
def current_temperature():
    device_id, thermostat_name = get_thermostat_info(request, False)
    honeywell = Honeywell(username, password, device_id)
    current_status = honeywell.get_status()
    current_temp = get_current_temperature(current_status)
    return jsonify({"current_temp":current_temp}), 201


@app.route(ROOT + 'set_cool', methods=['POST'])
def set_cool():
    device_id, thermostat_name, amount, hold_time = get_thermostat_info(request, True)
    honeywell = Honeywell(username, password, device_id)
    honeywell.set_cool(amount, hold_time)
    return jsonify(honeywell.get_status()), 201


@app.route(ROOT + 'set_heat', methods=['POST'])
def set_heat():
    device_id, thermostat_name, amount, hold_time = get_thermostat_info(request, True)
    honeywell = Honeywell(username, password, device_id)
    honeywell.set_heat(amount, hold_time)
    return jsonify(honeywell.get_status()), 201


@app.route(ROOT + 'cancel_hold', methods=['POST'])
def cancel_hold():
    device_id, thermostat_name = get_thermostat_info(request, False)
    honeywell = Honeywell(username, password, device_id)
    honeywell.cancel_hold()
    return jsonify(honeywell.get_status()), 201


@app.route(ROOT + 'cooler', methods=['POST'])
def cooler():
    logger = logging.getLogger(get_logger_name())
    logger.debug("starting")
    device_id, thermostat_name, amount, hold_time = get_thermostat_info(request, True)
    honeywell = Honeywell(username, password, device_id)
    honeywell.cooler(amount, hold_time)
    current_status = honeywell.get_status()
    current_temp = get_current_temperature(current_status)
    to_temp = current_temp - amount
    logger.debug("Changing temperature for '%s' from %3.2 to %3.2", thermostat_name, current_temp, to_temp)
    return jsonify(current_status), 201


@app.route(ROOT + 'warmer', methods=['POST'])
def warmer():
    logger = logging.getLogger(get_logger_name())
    logger.debug("starting")
    device_id, thermostat_name, amount, hold_time = get_thermostat_info(request, True)
    honeywell = Honeywell(username, password, device_id)
    honeywell.warmer(amount, hold_time)
    current_status = honeywell.get_status()
    current_temp = get_current_temperature(current_status)
    to_temp = current_temp + amount
    logger.debug("Changing temperature for '%s' from %3.2f to %3.2f", thermostat_name, current_temp, to_temp)
    return jsonify(current_status), 201


@app.route(ROOT + 'system_fan_on', methods=['POST'])
def system_fan_on():
    device_id, thermostat_name = get_thermostat_info(request, False)
    honeywell = Honeywell(username, password, device_id)
    honeywell.system_fan_on()
    return jsonify(honeywell.get_status()), 201


@app.route(ROOT + 'system_off', methods=['POST'])
def system_off():
    logger = logging.getLogger(get_logger_name())
    logger.debug("starting")
    device_id, thermostat_name = get_thermostat_info(request, False)
    logger.debug("turning %s off", thermostat_name)
    honeywell = Honeywell(username, password, device_id)
    honeywell.system_off()
    return jsonify(honeywell.get_status()), 201


@app.route(ROOT + 'system_auto', methods=['POST'])
def system_auto():
    logger = logging.getLogger(get_logger_name())
    logger.debug("starting")
    device_id, thermostat_name = get_thermostat_info(request, False)
    logger.debug("turning %s to auto", thermostat_name)
    honeywell = Honeywell(username, password, device_id)
    honeywell.system_auto()
    return jsonify(honeywell.get_status()), 201


def get_logger_name():
    stack = inspect.stack()
    file_name = os.path.basename(__file__).replace(".py", "")
    the_function = stack[1][3]
    try:
        if len(stack[1][0].f_locals) > 0:
            the_class = str(stack[1][0].f_locals["self"].__class__.__name__) + "."
        else:
            the_class = ""
    except:
        the_class = ""
    return file_name + "." + the_class + the_function


def main():
    global thermostats, username, password, app
    parser = argparse.ArgumentParser(description="listens on specified port for REST commands",
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--config-file",
                        required=True,
                        help="configuration file defining files within sections")
    args = parser.parse_args()
    if not os.path.isfile(args.config_file):
        raise RuntimeError("Specified configuration file '%s' does not exist!", args.config_file)
    config = ConfigParser.ConfigParser()
    config.read(args.config_file)
    log_file = config.get("server", "log_file")
    logging.config.fileConfig(log_file)
    logger = logging.getLogger(get_logger_name())
    username = config.get("honeywell", "username")
    password = config.get("honeywell", "password")
    certificate_password = config.get("security", "cert password")
    secure = config.getboolean("security", "ssh")
    server_name = config.get("server", "name")
    server_port = config.get("server", "port")
    server_debug = config.getboolean("server", "debug")
    thermostats = eval(config.get("system", "thermostats"))
    logger.debug("starting the test.  SSH is %s, thermostats are: %s", str(secure), str(thermostats))
    if secure:
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        context.load_cert_chain(certfile=os.path.join('keys', 'server.crt'),
                                keyfile=os.path.join('keys', 'server.key'), password=certificate_password)
    else:
        context = None
    app.config['SERVER_NAME'] = server_name + ":" + server_port
    app.config['DEBUG'] = server_debug
    app.run(debug=server_debug, ssl_context=context)

if __name__ == '__main__':
    main()
