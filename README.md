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
* --diskpaths     : Specific disk paths to report as comma separated list.
                    Defaults to listing all disks from cAdvisor.
                    If cAdvisor is not reachable, defaults to reporting '/'
                    based on results from psutil.
                    Note: this results in invalid results for non-root disks
                    when this is run inside a docker container. Recommended use
                    is to rely on cAdvisor in this case.
* -n              : Network Utilization
* -f              : Reporting frequency in seconds. Default: 60 seconds
* -k              : Optional key to use for printed dict. Default: 'host-stats'
* --cadvisorurl   : Base url for Cadvisor. Defaults to http://cadvisor:8080. Include port.
* --cadvisorapi   : API Version to use. Defaults to v1.3.
* --procpath      : Path to mounted /proc directory. Defaults to /proc_host
* --asbytes       : Report usage in bytes. Defaults to reporting in GB (excludes Network).
* --pernic        : Report network usage per NIC. Defaults to False.
* --hostname      : Specify a hostname to report. Defaults to using Rancher
                    metadata if available or hostname from python interpreter if not.

## Examples

Report only CPU and Memory every 10 seconds

    docker run -v=/proc:/prochost:ro pitrho/docker-host-stats -cm -f 10

Report CPU, Memory, and Disk Utilization with "FooBar " prefix (add a space
to the end of your prefix for proper formatting.)

    docker run -v=/proc:/prochost:ro pitrho/docker-host-stats -cmd -p "FooBar "

## Use with cAdvisor

It is recommended to run this alongside cAdvisor in order to have accurate
disk usage reporting when more than one mount exists. The provided
`docker-compose.yml` shows a sample configuration.

This will work in the absense of cAdvisor and fall back to using psutil based
on the mounted /proc directory of your host. This works except for one known
case: disk usage for mounted partitions other than /.

Note:
* We are binding to the host machine on port 9090, not 8080. This is to avoid
port conflict when using Rancher.
* Be aware that cAdvisor currently does not have a way to disable the web
interface. Therefore, ensure you do not have port 9090 (or whatever port you
decide to bind to the host) accessible publicly unless you really want to.
    * For example, only expose that port over your private subnet so public
    traffic is not able to access the interface.
