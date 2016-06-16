#!/usr/bin/env python
import cli.log
import logging
import sys
import psutil
import time

# Set up logging specifically for use in a Docker container such that we
# log everything to stdout
root = logging.getLogger()
root.setLevel(logging.DEBUG)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter =\
    logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
root.addHandler(ch)


def to_gb(num_bytes):
    """ Turn bytes into GB and round to 2 decimal places.
    """
    return round(float(num_bytes) / 1000000000, 2)


@cli.log.CommandLineApp
def stats_logger(app):
    asbytes = app.params.asbytes

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
    logging.info("Log Prefix:          {0}".format(app.params.prefix))
    logging.info("/proc Path:          {0}".format(app.params.procpath))
    logging.info("Report as GB:        {0}".format(not asbytes))
    logging.info("**********************************")
    logging.info("")

    psutil.PROCFS_PATH = app.params.procpath  # Set path to /proc from host

    while True:
        log_msg = {}  # Will log as a dict string for downstream parsing.

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
            disk_paths = app.params.diskpaths
            mounts = []  # Mount points to report upon

            def disk_usage_dict(mount):
                """ Return a dict for reported usage on a particular mount.
                """
                disk_usage = {}

                # We are not reporting any platform specific fields, such as
                # buffers / cahced / shared on Linux/BSD
                try:
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

            # Default disk path is 'all', which means we need to discover
            # all disk partitions first.
            if disk_paths == 'all':
                partitions = psutil.disk_partitions(all=False)  # Only physical
                for partition in partitions:
                    mounts.append(partition.mountpoint)
            else:
                paths = disk_paths.split(',')
                for path in paths:
                    mounts.append(path.strip())

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

        # Create logging message, add prefix if provided.
        report = "{0}".format(log_msg)
        if app.params.prefix is not None or app.params.prefix != "":
            report = app.params.prefix + " " + report

        logging.info("{0}".format(report.strip()))  # Log usage ...
        time.sleep(app.params.frequency)  # Sleep ...


stats_logger.add_param(
    "-f",
    "--frequency",
    help="Update frequency for stats",
    default=5,
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
    help="Disk paths to report as comma separated list. Defaults to all mounted partitions",
    default='all',
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
    "-p",
    "--prefix",
    help="Optional prefix to logs.",
    default="",
    type=str
)
stats_logger.add_param(
    "--procpath",
    help="Path to mounted /proc directory. Defaults to /proc_host",
    default="/proc_host",
    type=str
)
stats_logger.add_param(
    "--asbytes",
    help="Report relevant usage in bytes instead of gigabytes.",
    action="store_true",
    default=False
)


if __name__ == "__main__":
    stats_logger.run()
