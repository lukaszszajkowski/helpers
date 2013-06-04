
Installing CloudWatchMonitoringScripts on CentOs 6

yum install unzip wget perl-libwww-perl perl-Compress-Zlib perl-Compress-Raw-Zlib perl-Crypt-SSLeay perl-Net-SSLeay perl-Digest-SHA1 perl-Digest-SHA
   
cd
pwd
mkdir aws-scripts-mon
cd aws-scripts-mon
wget http://ec2-downloads.s3.amazonaws.com/cloudwatch-samples/CloudWatchMonitoringScripts.zip
unzip CloudWatchMonitoringScripts.zip
cat CloudWatchClient.pm |  sed 's/LWP 6/LWP 5/' > CloudWatchClient_tmp.pm
mv CloudWatchClient_tmp.pm CloudWatchClient.pm
