#!/usr/bin/env python
'''
Created on March 20, 2013

@author: Lukasz Szajkowski
@contact: Lukasc.Szajkowski@bbc.co.uk
@version: 1.0
@summary: Parse svn log and provide statistics about authors 
      
Examples:
    
    export "SLP_CFGFILE=/usr/local/etc/aws-ec2-monitor.conf" - Set the path to configuration file
    ./%prog [options]    
    ./%prog -h - show this help message and exit 
'''
log = None

import os
import sys
import logging
import logging.handlers

# By default all errors go to /var/log/messages
# This can be disabled by setting option syslog to False
syslog_handler = logging.handlers.SysLogHandler(address='/dev/log')
def init_log(log):
    """ All Errors go to stderr and /var/log/messages"""
    
    log = logging.getLogger('aws-ec2-manager')
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s " + "%(levelname)s\t%(message)s")
    handler.setFormatter(formatter)            
    log.addHandler(handler)
    
    syslog_handler.setLevel(logging.ERROR)
    formatter = logging.Formatter("aws-ec2-manager %(levelname)s\t%(message)s")
    syslog_handler.setFormatter(formatter)            
    log.addHandler(syslog_handler)
    
    return log

log = init_log(log)

try:
    import time
    import random
    import subprocess
    import httplib
    import datetime 
    import re
    from glob import glob
    from datetime import datetime, timedelta
    from optparse import OptionParser, TitledHelpFormatter
    from ConfigParser import SafeConfigParser
    import traceback
    import commands

except ImportError:
    # Checks the installation of the necessary python modules
    msg = ((os.linesep * 2).join(["An error found importing one module:",
    str(sys.exc_info()[1]), "You need to install it", "Exit..."]))
    log.error(msg)
    sys.exit(-2)
except SyntaxError, e:
    # Checks the installation of the necessary python modules
    msg = (os.linesep * 2).join(["An error found importing one module:",
            str(sys.exc_info()[1]), "You need to install correct versions of libraries (Python 2.6 and boto 2.5.2)", "Exit..."])
    log.error(msg)
    sys.exit(-2)

    
class OptionsError(Exception): pass
class CommandError(Exception): pass

VERSION = '0.0.1'
appName = None


class SampleConf(object):
    """ A class which ... """
    def __init__(self):
        """Constructor"""
        self.__conf = {}
        
    def get(self, key):
        """The function returns configuration value by key"""
        return self.__conf[key] 
    
    def set(self, key, value):
        """The function sets configuration value by key"""
        self.__conf[key] = value 
        

class SvnClient(object):
        
    def __init__(self, conf, results_procesor=None):
        self.conf = conf
        self.results_procesor = results_procesor
                
    def parse_svn_log(self, conf):
        ''' List authors'''

        svn_log_fields = {"revision":0, "raw_email":1, "raw_date":2, "lines":3}        
        svn_paths = conf.svn_paths.strip().split(",")
        svn_log_command = conf.svn_log_command 
        
        total_code_lines = 0
        total_authors = 0
        authors_map = {}
        
        for svn_path in svn_paths:
            command = "%s %s" % (conf.svn_log_command, svn_path)
            (status, results_str) = commands.getstatusoutput(command)        
            if status != 0:
                raise CommandError(command)
            component_name = svn_path.split("/")[-2]
            log.debug("log file for  %s" %(component_name))
            lines = results_str.splitlines()
            #log.debug("parse_svn_log lines %s" %(lines))
            for line in lines:
                if "r" in line and "|" in line:
                    fields = line.split('|')
                    if len(fields) != 4:
                        #log.error("parse_svn_log fields %s" %(fields))
                        continue
                    #log.debug("parse_svn_log fields %s" %(fields)) 
                    revision = fields[svn_log_fields['revision']]
                    author_fields = fields[svn_log_fields['raw_email']].split('/')
                    raw_date = fields[svn_log_fields['raw_date']].strip().split(" ")[0]
                    code_lines = int(fields[svn_log_fields['lines']].strip().split(" ")[0])
                    #raw_email = fields[svn_log_fields['raw_email']]
                    author_email = author_fields[1].split("=")[1]
                    
                    from_date="Mon Feb 15 2010"
                
                    date = time.strptime(raw_date.strip(),"%Y-%m-%d")
                    
                    if author_email not in authors_map:
                        authors_map[author_email] = {"lines":code_lines, "modifications":1, 'start_date':date, 'end_date':date}
                        authors_map[author_email]["components"] = {}
                        #log.debug("++author %s\t%s" %(author_email, authors_map[author_email]))
                    else:
                        authors_map[author_email]["lines"] = authors_map[author_email]["lines"] + code_lines
                        authors_map[author_email]["modifications"] = authors_map[author_email]["modifications"] + 1
                    
                    if component_name not in authors_map[author_email]["components"]:
                        authors_map[author_email]["components"][component_name] = 1
                    else:
                        #authors_map[author_email]["components"][component_name] = {}
                        authors_map[author_email]["components"][component_name] = authors_map[author_email]["components"][component_name] + 1
                        ##log.debug("---author %s\t%s" %(author_email, authors_map[author_email]))
                    
                    if date < authors_map[author_email]["start_date"]:
                        authors_map[author_email]["start_date"] = date
                    if date > authors_map[author_email]["end_date"]:
                        authors_map[author_email]["start_date"] = date
                    total_code_lines = total_code_lines + code_lines
            
        print "%35s\t%s - %s\t%s\t%s\t%s\t" %("Author email", "start_date", "end_date", "lines", "modifications", "components")
        for author in  authors_map:
            authors_map[author]["start_date"] = time.strftime("%Y-%m-%d", authors_map[author]["start_date"])
            authors_map[author]["end_date"] = time.strftime("%Y-%m-%d", authors_map[author]["end_date"])
            #log.debug("author %s\t%s" %(author, authors_map[author]))
            map = authors_map[author]
            print "%35s\t%s - %s\t%s\t%s\t%s\t" %(author, map["start_date"], map["end_date"], map["lines"], map["modifications"], map["components"],)
                
        log.debug("total_code_lines  %s\ttotal authors %s" %(total_code_lines, len(authors_map)))
    
    def run(self):
        
        self.parse_svn_log(self.conf)

### Main
def configure_log_file(conf):
    """If configured then log rotating log file will be used"""
     
    if conf.log_file_path is not None and conf.log_file_path.strip() != "":
        #if os.path.isfile(conf.log_file_path):
        try:
            handler = logging.handlers.RotatingFileHandler(conf.log_file_path, mode='a', maxBytes=100000, backupCount=3)
            handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter("%(asctime)s " + "%(levelname)s\t%(message)s")
            handler.setFormatter(formatter)        
            log.addHandler(handler)
            log.info("Starting new aws-ec2-monitor with %s log file" % (conf.log_file_path))
        except Exception, (errno):
            log.error("Could not open the log file %s - %s" % (conf.log_file_path, errno))
    
    if conf.syslog == False:
        log.removeHandler(syslog_handler)
        
def parse_tags_list(tags_string):
    """Parse string into tags"""
    tags = {}
    if len(tags_string.strip()) == 0:
        return tags
    
    list = tags_string.split(",")
    for item in list:
        t = item.split(":")
        if len(t) != 2:
            raise OptionsError("parsing aws-metrics-tags parameter [%s]" % (tags_string))
        tags[t[0]] = t[1]
    return tags

def buildParams(cfg, parser):
    # Required options
    defcfg = cfg.defaults()
    # Optional
    parser.add_option('--config_file', dest='config_file', type="string", default=None,
        help='path to config file. Can be provided by --config_file or ENV')

    parser.add_option('--log-file-path', dest='log_file_path', type="string",
        help='path to log file. Default is disabled (None)', default=defcfg.get("log-file-path", None))    

    parser.add_option('--syslog', action="store_true", dest='syslog',
        help='send all script errors syslog (/var/log/messages), Default is enabled', default=defcfg.get("syslog", "True") == "True")    

    parser.add_option('--svn-paths', dest='svn_paths', type="string",
        help='List of svn repositories (path)', default=defcfg.get("svn-paths", None))    

    parser.add_option('--svn-log-command', dest='svn_log_command', type="string",
        help='SVN log command', default=defcfg.get("svn-log-command", "svn log"))    

    parser.add_option('-v', '--verbose', dest='verbose', type="int", help='Verbose level - 0 default is None', default=defcfg.get("verbose", 0))

    parser.add_option('-d', '--debug', action="store_true", dest='debug', help='run the script in the debug mode')

    return parser

def readCommadLine(env, arguments, usage):
    """Read the command line -  returns options"""
    config_file = os.environ.get(env, None)
    
    is_help = False
    
    if not config_file:
        try:
            # If config_file in command line parse it
            config_file = [arg.split("=")[1] for arg in arguments if "--config_file" in arg][0]
        except (ValueError, IndexError): pass
    
    parser = OptionParser(usage, version="%s" % VERSION, formatter=TitledHelpFormatter(width=255, indent_increment=4))
    cfg = SafeConfigParser()

    if is_help == False:
        if config_file is None or not os.path.isfile(config_file):
            raise OptionsError("config_file %s does not exist. Specify path to configuration file in environment %s or in command line --config_file" % (str(config_file), str(env)))
        try:
            cfg.read(config_file)
        except:
            raise OptionsError("reading config_file %s." % (str(config_file)))

    buildParams(cfg, parser)    
    options, args = parser.parse_args(arguments)    
    
    return options

def runMain(arguments, output=sys.stdout):
    """The main function"""
    
    usage = """
    %prog [options]
    
      Parse svn log and provide statistics about authors 
      
Examples:
    
    export "SLP_CFGFILE=/usr/local/etc/aws-ec2-monitor.conf" - Set the path to configuration file
    ./%prog [options]    
    ./%prog -h - show this help message and exit """
       
    log.setLevel(logging.ERROR)    
    conf = readCommadLine("SLP_CFGFILE", arguments, usage)
    
    if conf.verbose > 0:
        log.setLevel(logging.INFO)    

    if conf.verbose > 3:
        log.setLevel(logging.DEBUG)    
    
    configure_log_file(conf)

    app_conf = SampleConf()
    executor = SvnClient(conf)
        
    try:
        executor.run()
    except Exception, (errno):
        log.error(errno)
        if conf.verbose > 0:
            traceback.print_exc(file=sys.stdout)
        sys.exit(1)
    except:
        if conf.verbose > 0:
            traceback.print_stack() 
        log.error("Unexpected error")
        sys.exit(1)
        

if __name__ == '__main__':    
    runMain(sys.argv[1:])
