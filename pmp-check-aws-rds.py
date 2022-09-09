#!/usr/bin/env python2
"""Nagios plugin for Amazon RDS monitoring.

This program is part of $PROJECT_NAME$
License: GPL License (see COPYING)

Author Roman Vynar
Copyright 2014-2015 Percona LLC and/or its affiliates
"""

import datetime
import optparse
import pprint
import sys

import boto
import boto.rds
import boto.ec2.cloudwatch

# Nagios status codes
OK = 0
WARNING = 1
CRITICAL = 2
UNKNOWN = 3


class RDS(object):

    """RDS connection class"""

    def __init__(self, region, profile=None, identifier=None):
        """Get RDS instance details"""
        self.region = region
        self.profile = profile
        self.identifier = identifier

        if self.region == 'all':
            self.regions_list = [reg.name for reg in boto.rds.regions()]
        else:
            self.regions_list = [self.region]

        self.info = None
        if self.identifier:
            for reg in self.regions_list:
                try:
                    rds = boto.rds.connect_to_region(reg, profile_name=self.profile)
                    self.info = rds.get_all_dbinstances(self.identifier)
                except (boto.provider.ProfileNotFoundError, boto.exception.BotoServerError) as msg:
                    debug(msg)
                else:
                    # Exit on the first region and identifier match
                    self.region = reg
                    break

    def get_info(self):
        """Get RDS instance info"""
        if self.info:
            return self.info[0]
        else:
            return None

    def get_list(self):
        """Get list of available instances by region(s)"""
        result = dict()
        for reg in self.regions_list:
            try:
                rds = boto.rds.connect_to_region(reg, profile_name=self.profile)
                result[reg] = rds.get_all_dbinstances()
            except (boto.provider.ProfileNotFoundError, boto.exception.BotoServerError) as msg:
                debug(msg)

        return result

    def get_metric(self, metric, start_time, end_time, step):
        """Get RDS metric from CloudWatch"""
        cw_conn = boto.ec2.cloudwatch.connect_to_region(self.region, profile_name=self.profile)
        result = cw_conn.get_metric_statistics(
            step,
            start_time,
            end_time,
            metric,
            'AWS/RDS',
            'Average',
            dimensions={'DBInstanceIdentifier': [self.identifier]}
        )
        if result:
            if len(result) > 1:
                # Get the last point
                result = sorted(result, key=lambda k: k['Timestamp'])
                result.reverse()

            result = float('%.2f' % result[0]['Average'])

        return result


def debug(val):
    """Debugging output"""
    global options
    if options.debug:
        print 'DEBUG: %s' % val


def main():
    """Main function"""
    global options

    short_status = {
        OK: 'OK',
        WARNING: 'WARN',
        CRITICAL: 'CRIT',
        UNKNOWN: 'UNK'
    }

    # DB instance classes as listed on
    # http://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.DBInstanceClass.html
    db_classes = {
                    'db.m6g.16xlarge': 256,
        'db.m6g.12xlarge': 192,
        'db.m6g.8xlarge': 128,
        'db.m6g.4xlarge': 64,
        'db.m6g.2xlarge': 32,
        'db.m6g.xlarge': 16,
        'db.m6g.large': 8,
        'db.m6gd.16xlarge': 256,
        'db.m6gd.12xlarge': 192,
        'db.m6gd.8xlarge': 128,
        'db.m6gd.4xlarge': 64,
        'db.m6gd.2xlarge': 32,
        'db.m6gd.xlarge': 16,
        'db.m6gd.large': 8,
        'db.m6i.32xlarge': 512,
        'db.m6i.24xlarge': 384,
        'db.m6i.16xlarge': 256,
        'db.m6i.12xlarge': 192,
        'db.m6i.8xlarge': 128,
        'db.m6i.4xlarge': 64,
        'db.m6i.2xlarge': 32,
        'db.m6i.xlarge': 16,
        'db.m6i.large': 8,
        'db.m5d.24xlarge': 384,
        'db.m5d.16xlarge': 256,
        'db.m5d.12xlarge': 192,
        'db.m5d.8xlarge': 128,
        'db.m5d.4xlarge': 64,
        'db.m5d.2xlarge': 32,
        'db.m5d.xlarge': 16,
        'db.m5d.large': 8,
        'db.m5.24xlarge': 384,
        'db.m5.16xlarge': 256,
        'db.m5.12xlarge': 192,
        'db.m5.8xlarge': 128,
        'db.m5.4xlarge': 64,
        'db.m5.2xlarge': 32,
        'db.m5.xlarge': 16,
        'db.m5.large': 8,
        'db.m4.16xlarge': 256,
        'db.m4.10xlarge': 160,
        'db.m4.4xlarge': 64,
        'db.m4.2xlarge': 32,
        'db.m4.xlarge': 16,
        'db.m4.large': 8,
        'db.m3.2xlarge': 30,
        'db.m3.xlarge': 15,
        'db.m3.large': 7.5,
        'db.m3.medium': 3.75,
        'db.m1.xlarge': 15,
        'db.m1.large': 7.5,
        'db.m1.medium': 3.75,
        'db.m1.small': 1.7,
        'db.x2g.16xlarge': 1024,
        'db.x2g.12xlarge': 768,
        'db.x2g.8xlarge': 512,
        'db.x2g.4xlarge': 256,
        'db.x2g.2xlarge': 128,
        'db.x2g.xlarge': 64,
        'db.x2g.large': 32,
        'db.z1d.12xlarge': 384,
        'db.z1d.6xlarge': 192,
        'db.z1d.3xlarge': 96,
        'db.z1d.2xlarge': 64,
        'db.z1d.xlarge': 32,
        'db.z1d.large': 16,
        'db.x1e.32xlarge': 3904,
        'db.x1e.16xlarge': 1952,
        'db.x1e.8xlarge': 976,
        'db.x1e.4xlarge': 488,
        'db.x1e.2xlarge': 244,
        'db.x1e.xlarge': 122,
        'db.x1.32xlarge': 1952,
        'db.x1.16xlarge': 976,
        'db.r6g.16xlarge': 512,
        'db.r6g.12xlarge': 384,
        'db.r6g.8xlarge': 256,
        'db.r6g.4xlarge': 128,
        'db.r6g.2xlarge': 64,
        'db.r6g.xlarge': 32,
        'db.r6g.large': 16,
        'db.r6gd.16xlarge': 512,
        'db.r6gd.12xlarge': 384,
        'db.r6gd.8xlarge': 256,
        'db.r6gd.4xlarge': 128,
        'db.r6gd.2xlarge': 64,
        'db.r6gd.xlarge': 32,
        'db.r6gd.large': 16,
        'db.r6i.32xlarge': 1024,
        'db.r6i.24xlarge': 768,
        'db.r6i.16xlarge': 512,
        'db.r6i.12xlarge': 384,
        'db.r6i.8xlarge': 256,
        'db.r6i.4xlarge': 128,
        'db.r6i.2xlarge': 64,
        'db.r6i.xlarge': 32,
        'db.r6i.large': 16,
        'db.r5d.24xlarge': 768,
        'db.r5d.16xlarge': 512,
        'db.r5d.12xlarge': 384,
        'db.r5d.8xlarge': 256,
        'db.r5d.4xlarge': 128,
        'db.r5d.2xlarge': 64,
        'db.r5d.xlarge': 32,
        'db.r5d.large': 16,
        'db.r5b.24xlarge': 768,
        'db.r5b.16xlarge': 512,
        'db.r5b.12xlarge': 384,
        'db.r5b.8xlarge': 256,
        'db.r5b.4xlarge': 128,
        'db.r5b.2xlarge': 64,
        'db.r5b.xlarge': 32,
        'db.r5b.large': 16,
        'db.r5.24xlarge': 768,
        'db.r5.16xlarge': 512,
        'db.r5.12xlarge': 384,
        'db.r5.8xlarge': 256,
        'db.r5.4xlarge': 128,
        'db.r5.2xlarge': 64,
        'db.r5.xlarge': 32,
        'db.r5.large': 16,
        'db.r4.16xlarge': 488,
        'db.r4.8xlarge': 244,
        'db.r4.4xlarge': 122,
        'db.r4.2xlarge': 61,
        'db.r4.xlarge': 30.5,
        'db.r4.large': 15.25,
        'db.r3.8xlarge': 244,
        'db.r3.4xlarge': 122,
        'db.r3.2xlarge': 61,
        'db.r3.xlarge': 30.5,
        'db.r3.large': 15.25,
        'db.t4g.2xlarge': 32,
        'db.t4g.xlarge': 16,
        'db.t4g.large': 8,
        'db.t4g.medium': 4,
        'db.t4g.small': 2,
        'db.t4g.micro': 1,
        'db.t3.2xlarge': 32,
        'db.t3.xlarge': 16,
        'db.t3.large': 8,
        'db.t3.medium': 4,
        'db.t3.small': 2,
        'db.t3.micro': 1,
        'db.t2.2xlarge': 32,
        'db.t2.xlarge': 16,
        'db.t2.large': 8,
        'db.t2.medium': 4,
        'db.t2.small': 2,
        'db.t2.micro': 1,
    }


    # RDS metrics http://docs.aws.amazon.com/AmazonCloudWatch/latest/DeveloperGuide/rds-metricscollected.html
    metrics = {
        'status': 'RDS availability',
        'load': 'CPUUtilization',
        'memory': 'FreeableMemory',
        'storage': 'FreeStorageSpace'
    }

    units = ('percent', 'GB')

    # Parse options
    parser = optparse.OptionParser()
    parser.add_option('-l', '--list', help='list of all DB instances',
                      action='store_true', default=False, dest='db_list')
    parser.add_option('-n', '--profile', default=None,
                      help='AWS profile from ~/.boto or /etc/boto.cfg. Default: None, fallbacks to "[Credentials]".')
    parser.add_option('-r', '--region', default='us-east-1',
                      help='AWS region. Default: us-east-1. If set to "all", we try to detect the instance region '
                           'across all of them, note this will be slower than if you specify the region explicitly.')
    parser.add_option('-i', '--ident', help='DB instance identifier')
    parser.add_option('-p', '--print', help='print status and other details for a given DB instance',
                      action='store_true', default=False, dest='printinfo')
    parser.add_option('-m', '--metric', help='metric to check: [%s]' % ', '.join(metrics.keys()))
    parser.add_option('-w', '--warn', help='warning threshold')
    parser.add_option('-c', '--crit', help='critical threshold')
    parser.add_option('-u', '--unit', help='unit of thresholds for "storage" and "memory" metrics: [%s].'
                      'Default: percent' % ', '.join(units), default='percent')
    parser.add_option('-t', '--time', help='time period in minutes to query. Default: 5',
                      type='int', default=5)
    parser.add_option('-a', '--avg', help='time average in minutes to request. Default: 1',
                      type='int', default=1)
    parser.add_option('-f', '--forceunknown', help='force alerts on unknown status. This prevents issues related to '
                      'AWS Cloudwatch throttling limits Default: False',
                      action='store_true', default=False)
    parser.add_option('-d', '--debug', help='enable debug output',
                      action='store_true', default=False)
    options, _ = parser.parse_args()

    if options.debug:
        boto.set_stream_logger('boto')

    rds = RDS(region=options.region, profile=options.profile, identifier=options.ident)

    # Check args
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit()
    elif options.db_list:
        info = rds.get_list()
        print 'List of all DB instances in %s region(s):' % (options.region,)
        pprint.pprint(info)
        sys.exit()
    elif not options.ident:
        parser.print_help()
        parser.error('DB identifier is not set.')
    elif options.printinfo:
        info = rds.get_info()
        if info:
            pprint.pprint(vars(info))
        else:
            print 'No DB instance "%s" found on your AWS account and %s region(s).' % (options.ident, options.region)

        sys.exit()
    elif not options.metric or options.metric not in metrics.keys():
        parser.print_help()
        parser.error('Metric is not set or not valid.')
    elif not options.warn and options.metric != 'status':
        parser.print_help()
        parser.error('Warning threshold is not set.')
    elif not options.crit and options.metric != 'status':
        parser.print_help()
        parser.error('Critical threshold is not set.')
    elif options.avg <= 0 and options.metric != 'status':
        parser.print_help()
        parser.error('Average must be greater than zero.')
    elif options.time <= 0 and options.metric != 'status':
        parser.print_help()
        parser.error('Time must be greater than zero.')

    now = datetime.datetime.utcnow()
    status = None
    note = ''
    perf_data = None

    # RDS Status
    if options.metric == 'status':
        info = rds.get_info()
        if not info:
            status = UNKNOWN
            note = 'Unable to get RDS instance'
        else:
            status = OK
            try:
                version = info.EngineVersion
            except:
                version = info.engine_version

            note = '%s %s. Status: %s' % (info.engine, version, info.status)

    # RDS Load Average
    elif options.metric == 'load':
        # Check thresholds
        try:
            warns = [float(x) for x in options.warn.split(',')]
            crits = [float(x) for x in options.crit.split(',')]
            fail = len(warns) + len(crits)
        except:
            fail = 0

        if fail != 6:
            parser.error('Warning and critical thresholds should be 3 comma separated numbers, e.g. 20,15,10')

        loads = []
        fail = False
        j = 0
        perf_data = []
        for i in [1, 5, 15]:
            if i == 1:
                # Some stats are delaying to update on CloudWatch.
                # Let's pick a few points for 1-min load avg and get the last point.
                points = 5
            else:
                points = i

            load = rds.get_metric(metrics[options.metric], now - datetime.timedelta(seconds=points * 60), now, i * 60)
            if not load:
                status = UNKNOWN
                note = 'Unable to get RDS statistics'
                perf_data = None
                break

            loads.append(str(load))
            perf_data.append('load%s=%s;%s;%s;0;100' % (i, load, warns[j], crits[j]))

            # Compare thresholds
            if not fail:
                if warns[j] > crits[j]:
                    parser.error('Parameter inconsistency: warning threshold is greater than critical.')
                elif load >= crits[j]:
                    status = CRITICAL
                    fail = True
                elif load >= warns[j]:
                    status = WARNING

            j = j + 1

        if status != UNKNOWN:
            if status is None:
                status = OK

            note = 'Load average: %s%%' % '%, '.join(loads)
            perf_data = ' '.join(perf_data)

    # RDS Free Storage
    # RDS Free Memory
    elif options.metric in ['storage', 'memory']:
        # Check thresholds
        try:
            warn = float(options.warn)
            crit = float(options.crit)
        except:
            parser.error('Warning and critical thresholds should be integers.')

        if crit > warn:
            parser.error('Parameter inconsistency: critical threshold is greater than warning.')

        if options.unit not in units:
            parser.print_help()
            parser.error('Unit is not valid.')

        info = rds.get_info()
        free = rds.get_metric(metrics[options.metric], now - datetime.timedelta(seconds=options.time * 60),
                              now, options.avg * 60)
        if not info or not free:
            status = UNKNOWN
            note = 'Unable to get RDS details and statistics'
        else:
            if options.metric == 'storage':
                storage = float(info.allocated_storage)
            elif options.metric == 'memory':
                try:
                    storage = db_classes[info.instance_class]
                except:
                    print 'Unknown DB instance class "%s"' % info.instance_class
                    sys.exit(CRITICAL)

            free = '%.2f' % (free / 1024 ** 3)
            free_pct = '%.2f' % (float(free) / storage * 100)
            if options.unit == 'percent':
                val = float(free_pct)
                val_max = 100
            elif options.unit == 'GB':
                val = float(free)
                val_max = storage

            # Compare thresholds
            if val <= crit:
                status = CRITICAL
            elif val <= warn:
                status = WARNING

            if status is None:
                status = OK

            note = 'Free %s: %s GB (%.0f%%) of %s GB' % (options.metric, free, float(free_pct), storage)
            perf_data = 'free_%s=%s;%s;%s;0;%s' % (options.metric, val, warn, crit, val_max)

    # Final output
    if status != UNKNOWN and perf_data:
        print '%s %s | %s' % (short_status[status], note, perf_data)
    elif status == UNKNOWN and not options.forceunknown:
        print '%s %s | null' % ('OK', note)
        sys.exit(0)
    else:
        print '%s %s' % (short_status[status], note)

    sys.exit(status)


if __name__ == '__main__':
    main()
