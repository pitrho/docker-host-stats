# Docker Host Stats Reporter
Reports host usage information such as CPU, Memory, and Disk utilization.
Reports to stdout so user can ship this information with other logs to an
aggregator if desired.

## Usage
Only requirement is to mount the `/proc` directory in Read-Only mode inside the
container under `/prochost`. The default behavior will report CPU, Memory, and
Disk Utilization of `/` every 5 seconds.

    docker run -v=/proc:/prochost:ro pitrho/docker-host-stats

## Options
User can optionally pass flags to specify what system stats to report and
on what frequency.

* -c              : CPU Utilization (as percentage)
* --combinedcpu   : Report CPU as an average across cores instead of per-CPU basis.
* -m              : Memory Utilization
* -d              : Disk Utilization
* --diskpaths     : Specific disk paths to report as comma separated list. Defaults to all mounted partitions.
* -n              : Network Utilization
* -f              : Reporting frequency in seconds. Default: 5
* -k              : Optional key to use for printed dict. Default: 'host-stats'
* --procpath      : Path to mounted /proc directory. Defaults to /proc_host
* --asbytes       : Report usage in bytes. Defaults to reporting in GB (excludes Network).
* --pernic        : Report network usage per NIC. Defaults to False.

## Examples

Report only CPU and Memory every 10 seconds

    docker run -v=/proc:/prochost:ro pitrho/docker-host-stats -cm -f 10

Report CPU, Memory, and Disk Utilization with "FooBar " prefix (add a space
to the end of your prefix for proper formatting.)

    docker run -v=/proc:/prochost:ro pitrho/docker-host-stats -cmd -p "FooBar "
