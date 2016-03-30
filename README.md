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

* -c : CPU
* -m : Memory
* -d : Disk
* -n : Network (not yet implemented)
* -f : Reporting frequency, this requires an integer as the argument

## Examples

Report only CPU and Memory every 10 seconds

    docker run -v=/proc:/prochost:ro pitrho/docker-host-stats -cm -f 10
