#!/bin/bash
apt install nagios-nrpe-server nagios-plugins -y 
cd /usr/lib/nagios/plugins/
curl -o check_inode https://raw.githubusercontent.com/smrithinns/plugin/master/check_inode 
curl -o check_mem.pl  https://raw.githubusercontent.com/smrithinns/plugin/master/check_mem.pl
curl -o pmp-check-mysql-deadlocks https://raw.githubusercontent.com/smrithinns/plugin/master/pmp-check-mysql-deadlocks
curl -o pmp-check-mysql-innodb https://raw.githubusercontent.com/smrithinns/plugin/master/pmp-check-mysql-innodb
curl -o pmp-check-mysql-status https://raw.githubusercontent.com/smrithinns/plugin/master/pmp-check-mysql-status
chmod +x check_mem.pl  check_inode pmp-check-mysql-deadlocks pmp-check-mysql-innodb pmp-check-mysql-status
curl -o /etc/nagios/nrpe.cfg https://raw.githubusercontent.com/smrithinns/plugin/master/nrpe.cfg
/etc/init.d/nagios-nrpe-server restart
