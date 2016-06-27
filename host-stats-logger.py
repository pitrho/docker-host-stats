#!/usr/bin/env python
import cli.log
import logging
import sys
import psutil
import time
import requests
import json
from pythonjsonlogger import jsonlogger
import socket


# Downgrade logging level of requests library
logging.getLogger('requests').setLevel(logging.ERROR)

# Set up logging specifically for use in a Docker container such that we
# log everything to stdout
root = logging.getLogger()
root.setLevel(logging.DEBUG)
logHandler = logging.StreamHandler(sys.stdout)
logHandler.setLevel(logging.DEBUG)
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
root.addHandler(logHandler)


def to_gb(num_bytes):
    """ Turn bytes into GB and round to 2 decimal places.
    """
    return round(float(num_bytes) / 1000000000, 2)


def cadvisor_disk_average(host_stats, device, asbytes):
    """ Return the total/used/free/percent used for specified device.

        cAdvisor returns 60 seconds worth of data in 1s intervals. Roll this
        up into an average for each stat.
    """

    disk_usage = {
        'total': 0,
        'percent': 0,
        'used': 0,
        'free': 0,
        'status': 'OK'
    }

    capacity_total = 0
    usage_total = 0
    available_total = 0
    samples = 0
    for stat in host_stats['stats']:
        for mnt in stat['filesystem']:
            if mnt['device'] == device:
                capacity_total += mnt['capacity']
                usage_total += mnt['usage']
                available_total += mnt['available']

                samples += 1

    if samples > 0:
        disk_usage['total'] = capacity_total / samples
        disk_usage['used'] = usage_total / samples
        disk_usage['free'] = available_total / samples

        # Convert to GB if not asbytes
        if not asbytes:
            disk_usage['total'] = to_gb(disk_usage['total'])
            disk_usage['used'] = to_gb(disk_usage['used'])
            disk_usage['free'] = to_gb(disk_usage['free'])

        # Calc percent used
        disk_usage['percent'] = round(
            float(disk_usage['used']) / float(disk_usage['total']) * 100,
            2
        )

    else:
        disk_usage['status'] = "No samples for provided mount path ..."

    return disk_usage


@cli.log.CommandLineApp
def stats_logger(app):
    asbytes = app.params.asbytes  # Report as bytes? Defaults to false, i.e. GB

    # Create API URLs
    # Stats is for last 1 minute's worth of machine usage stats every second
    cadvisor_stats = "{0}/api/{1}/containers"\
                     .format(app.params.cadvisorurl, app.params.cadvisorapi)

    # Machine contains high level host statistics (static)
    cadvisor_machine = "{0}/api/{1}/machine"\
                       .format(app.params.cadvisorurl, app.params.cadvisorapi)

    rancher_host_meta = 'http://rancher-metadata/2015-12-19/self/host/{0}'

    cadvisor_active = True
    machine_stats = None
    host_stats = None

    # Run this once when container starts to establish whether cAdvisor
    # is available at start time (primarily just for more informative logs).
    # This is re-run every cycle.
    try:
        r = requests.get(cadvisor_machine)
        machine_stats = json.loads(r.content)
    except:
        cadvisor_active = False

    # Get meta details about current host. This is only available when running
    # using Rancher. In absence of Rancher, default to hostname from python
    # interpreter.
    if app.params.hostname == 'auto':
        try:
            host = rancher_host_meta.format("hostname")
            r = requests.get(host)
            host_name = r.content
        except:
            host_name = socket.gethostname()
    else:
        host_name = app.params.hostname

    logging.info("**********************************")
    logging.info("*** Host Stats Reporter Config ***")
    logging.info("**********************************")
    logging.info("Reporting Interval:  {0}s".format(app.params.frequency))
    logging.info("Report CPU:          {0}".format(app.params.cpu))
    logging.info("Report Per CPU:      {0}".format(not app.params.combinedcpu))
    logging.info("Report Memory:       {0}".format(app.params.memory))
    logging.info("Report Disk:         {0}".format(app.params.disk))
    logging.info("Reporting disk path: {0}".format(app.params.diskpaths))
    logging.info("Report Network:      {0}".format(app.params.network))
    logging.info("Report per NIC:      {0}".format(app.params.pernic))
    logging.info("Log Key:             {0}".format(app.params.key))
    logging.info("/proc Path:          {0}".format(app.params.procpath))
    logging.info("Report as GB:        {0}".format(not asbytes))
    logging.info("cAdvisor Base:       {0}".format(app.params.cadvisorurl))
    logging.info("cAdvisor API:        {0}".format(app.params.cadvisorapi))
    logging.info("cAdvisor Active:     {0}".format(cadvisor_active))
    logging.info("Host Name:           {0}".format(host_name))
    logging.info("**********************************")
    logging.info("")

    psutil.PROCFS_PATH = app.params.procpath  # Set path to /proc from host

    while True:
        log_msg = {}  # Will log as a dict string for downstream parsing.
        log_msg['hostname'] = host_name

        # Retrieve data from cAdvisor. Must re-try each cycle in case cAdvisor
        # goes down (or up). If down, this will attempt to get as much data
        # as possible using psutil.
        machine_stats = None
        host_stats = None
        try:
            r = requests.get(cadvisor_machine)
            machine_stats = json.loads(r.content)

            r = requests.get(cadvisor_stats)
            host_stats = json.loads(r.content)

            cadvisor_active = True
        except:
            cadvisor_active = False

        # Add CPU Utilization
        #
        if app.params.cpu:
            cpu_pct = psutil.cpu_percent(percpu=(not app.params.combinedcpu))
            if app.params.combinedcpu:
                cpu_pct = [cpu_pct]  # Return as list to remain consistent.
            log_msg['cpu'] = {
                'utilization_pct': cpu_pct,
                'status': 'OK'
            }

        # Add Memory Utilization
        #
        if app.params.memory:
            memory = psutil.virtual_memory()

            # We are not reporting any platform specific fields, such as
            # buffers / cahced / shared on Linux/BSD
            log_msg['memory'] = {
                'total': memory.total if asbytes else to_gb(memory.total),
                'available': memory.available if asbytes else to_gb(memory.available),
                'percent': memory.percent,
                'used': memory.used if asbytes else to_gb(memory.used),
                'free': memory.free if asbytes else to_gb(memory.free),
                'status': 'OK'
            }

        # Add Disk Utilization
        #
        if app.params.disk:

            def disk_usage_dict(mount):
                """ Return a dict for reported usage on a particular mount.
                """
                disk_usage = {}

                # We are not reporting any platform specific fields, such as
                # buffers / cahced / shared on Linux/BSD
                try:
                    if cadvisor_active:
                        disk_usage =\
                            cadvisor_disk_average(host_stats, mount, asbytes)
                    else:
                        disk = psutil.disk_usage(mount)

                        disk_usage['total'] =\
                            disk.total if asbytes else to_gb(disk.total)
                        disk_usage['percent'] = disk.percent
                        disk_usage['used'] =\
                            disk.used if asbytes else to_gb(disk.used)
                        disk_usage['free'] =\
                            disk.free if asbytes else to_gb(disk.free)
                        disk_usage['status'] = 'OK'

                except OSError:
                    disk_usage['status'] =\
                        "Provided mount path does not exist ..."

                return disk_usage

            disk_paths = app.params.diskpaths
            mounts = []  # Mount points to report upon

            # Create list of paths from CLI if user specified paths.
            if disk_paths != "default":
                paths = disk_paths.split(',')
                for path in paths:
                    mounts.append(path.strip())

            # Use cadvisor's list of disks if available
            elif machine_stats is not None:
                paths = machine_stats['filesystems']
                for path in paths:
                    mounts.append(path['device'])

            # Default to reporting '/'
            else:
                mounts.append('/')

            log_msg['disk'] = {}
            for mount in mounts:
                log_msg['disk'][mount] = disk_usage_dict(mount)

        # Add Network Utilization
        #
        if app.params.network:

            log_msg['network'] = {
                'interfaces': [],
                'status': "OK"
            }

            net_usage = psutil.net_io_counters(pernic=app.params.pernic)

            log_msg['network']['interfaces'] = {}

            # If `pernic` is False, then this is returned as a named tuple
            # instead of a dict. We turn this into a dict and create a
            # key `allnic`
            if type(net_usage) != dict:
                net_usage = {
                    'allnic': dict(net_usage._asdict())
                }
                log_msg['network']['interfaces'] = dict(net_usage)
            else:
                for interface, tup in net_usage.iteritems():
                    log_msg['network']['interfaces'][interface] =\
                        dict(tup._asdict())

        # Create report dict using provided root key.
        report = {
            app.params.key: log_msg
        }

        logging.info("Reporting stats using cAdvisor: {0}"
                     .format(cadvisor_active), extra=report)  # Log usage ...

        time.sleep(app.params.frequency)  # Sleep ...


stats_logger.add_param(
    "-f",
    "--frequency",
    help="Update frequency for stats",
    default=60,
    type=int
)
stats_logger.add_param(
    "-c",
    "--cpu",
    required=False,
    help="Report CPU Utilization",
    action="store_true",
    default=False
)
stats_logger.add_param(
    "--combinedcpu",
    required=False,
    help="Report CPU as an average across cores instead of per-CPU basis.",
    action="store_true",
    default=False
)
stats_logger.add_param(
    "-m",
    "--memory",
    help="Report Memory",
    action="store_true",
    default=False
)
stats_logger.add_param(
    "-d",
    "--disk",
    help="Report Disk",
    action="store_true",
    default=False
)
stats_logger.add_param(
    "--diskpaths",
    help="Specific disk paths to report as comma separated list. "
         "Defaults to listing all disks from cAdvisor. "
         "If cAdvisor not reachable, defaults to '/'. "
         "based on results from psutil. "
         "Note: this results in invalid results for non-root disks depending "
         "on what is mounted internally to this container. Recommended use "
         "is to rely on cAdvisor.",
    default='default',
    type=str
)
stats_logger.add_param(
    "-n",
    "--network",
    help="Report Network",
    action="store_true",
    default=False
)
stats_logger.add_param(
    "--pernic",
    help="Report Network Utilization per NIC. Defaults to False.",
    action="store_true",
    default=False
)
stats_logger.add_param(
    "-k",
    "--key",
    help="Optional key to use for printed dict.",
    default="host-stats",
    type=str
)
stats_logger.add_param(
    "--procpath",
    help="Path to mounted /proc directory. Defaults to /proc_host",
    default="/proc_host",
    type=str
)
stats_logger.add_param(
    "--cadvisorurl",
    help="Base url for Cadvisor. Defaults to http://localhost:8080. Include port.",
    default="http://localhost:8080",
    type=str
)
stats_logger.add_param(
    "--cadvisorapi",
    help="API Version to use. Defaults to v1.3.",
    default="v1.3",
    type=str
)
stats_logger.add_param(
    "--asbytes",
    help="Report relevant usage in bytes instead of gigabytes.",
    action="store_true",
    default=False
)
stats_logger.add_param(
    "--hostname",
    help="Specify a hostname to report. Defaults to using Rancher metadata if available or hostname from python interpreter if not.",
    default="auto",
    type=str
)


if __name__ == "__main__":
    stats_logger.run()
