import os
import sys
import argparse
import subprocess
import paramiko
import json
import shlex
import time

with open('config.json', 'r') as file:
    info = json.load(file)

hostname = info['base']['hostname']
port = info['base']['port']
username = info['base']['username']
pathKcptunServer = info['base']['pathKcptunServer']
pathKcptunClient = info['base']['pathKcptunClient']
pathOutJsonFile = info['base']['pathOutJsonFile']
portKcptunServer = info['base']['portKcptunServer']
portKcptunClient = info['base']['portKcptunClient']
errorSkip = info['base']['errorSkip']
setConfig = info['setConfig']
optionalConfig = info['optionalConfig']

options = {
    'crypt': [
        'aes',
        'aes-128',
        'aes-192',
        'salsa20',
        'blowfish',
        'twofish',
        'cast5',
        '3des',
        'tea',
        'xtea',
        'xor',
        'sm4',
        'none'
    ],
    'mode': [
        'fast3',
        'fast2',
        'fast',
        'normal'
    ],
    'sndwnd': [
        '128',
        '256',
        '512',
        '1024',
        '2048'
    ],
    'rcvwnd': [
        '128',
        '256',
        '512',
        '1024',
        '2048'
    ],
    'datashard': [
        5,
        10,
        15,
        20
    ],
    'parityshard': list(range(10)),
    'nocomp': [
        True,
        False
    ],
    'sockbuf': [
        '2097152',
        '4194304',
        '8388608',
        '16777216'
    ],
    'smuxver': [
        '1',
        '2'
    ],
    'smuxbuf': [
        # '1048571' would probably cause iperf3 error.
        '2097152',
        '4194304',
        '8388608',
        '16777216'
    ],
    # streambuf only available on smuxver 2
    'streambuf': [
        '2097152',
        '4194304',
        '8388608'
        # '16777216' would probably cause iperf3 error.
    ]
}

logout = {}
ifIPv6 = '.' not in hostname
clientSSH = None
countDone = 0
countALL = 0
TBEG = None
TimeOUT = 0


def sec2time(sec):
    hour = sec // 3600
    minute = (sec - hour * 3600) // 60
    secnew = sec % 60
    return hour, minute, secnew


def speedtest(config):
    global countDone
    global logout
    global TimeOUT

    configServer = ' '.join([('--%s %s' % (key, value))
                             for key, value in config.items()])
    configClient = configServer.replace('sndwnd', 'rcvtmp')
    configClient = configClient.replace('rcvwnd', 'sndwnd')
    configClient = configClient.replace('rcvtmp', 'rcvwnd')
    if ifIPv6:
        configServer = ('-l [::]:%s -t [::1]:5201 ' %
                        portKcptunServer) + configServer
        configClient = ('-l [::]:%s -r [%s]:%s ' %
                        (portKcptunClient, hostname, portKcptunServer)) + configClient
    else:
        configServer = ('-l 0.0.0.0:%s -t 127.0.0.1:5201 ' %
                        portKcptunServer) + configServer
        configClient = ('-l 0.0.0.0:%s -r %s:%s ' %
                        (portKcptunClient, hostname, portKcptunServer)) + configClient

    clientSSH.exec_command("%s %s" % (pathKcptunServer, configServer))
    clientKCP = subprocess.Popen(shlex.split(
        "%s %s" % (pathKcptunClient, configClient)), stderr=subprocess.DEVNULL)

    with os.popen('iperf3 -c ::1 -p %s -i 2 -t 2 -R' % portKcptunClient) as infoiperf:
        infoiperf = infoiperf.readlines()

    clientSSH.exec_command(
        'kill $(ps aux | grep \"%s\" | grep -v \"grep\" | awk \'{print $2}\')' % pathKcptunServer)
    clientKCP.kill()

    if infoiperf[-4:-2] == []:
        TimeOUT += 1
        if TimeOUT == 3:
            if not errorSkip:
                clientSSH.close()
                print("connection error.")
                exit(-1)
        else:
            speedtest(config)
    else:
        logout[configServer] = infoiperf[-4:-2]
        if countALL % 5 == 0:
            with open(pathOutJsonFile, 'w+') as file:
                json.dump(logout, file)

        countDone += 1
        print("\r[%02.0f:%02.0f:%02.0f/%02.0f:%02.0f:%02.0f]: %4.0f/%.0f" % (sec2time(time.time() -
                                                                                      TBEG) + sec2time((time.time()-TBEG)/countDone*countALL) + (countDone, countALL)), end='')

    return


'''
if pos[optionA] > pos[optionB]:
    swap(pos[A], pos[B])
'''


def posSwap(optionA, optionB):
    if optionA in optionalConfig and optionB in optionalConfig:
        tmpA = optionalConfig.index(optionA)
        tmpB = optionalConfig.index(optionB)
        if tmpA > tmpB:
            optionalConfig[tmpA] = optionB
            optionalConfig[tmpB] = optionA


def TestOption(config, optionalConfig):

    if len(optionalConfig) == 0:
        print("optionalConfig should has at least one element.")
        exit(-1)

    thisOption = optionalConfig.pop()
    if thisOption == 'streambuf' and config['smuxver'] == '1':
        if len(optionalConfig) == 0:
            speedtest(config)
        else:
            TestOption(config, optionalConfig)
        optionalConfig.append(thisOption)
        return

    for candidate in options[thisOption]:
        # streambuf should be smaller than smuxbuf
        if thisOption == 'streambuf':
            if candidate > config['smuxbuf']:
                continue
        if thisOption == 'smuxbuf' and 'streambuf' in config and config['smuxver'] == '2':
            if candidate < config['streambuf']:
                continue
        config[thisOption] = candidate
        if len(optionalConfig) == 0:
            speedtest(config)
        else:
            TestOption(config, optionalConfig)
        del config[thisOption]
    optionalConfig.append(thisOption)
    return


def getNumberOptions(config, optionalConfig):
    countALL = 1

    for thisOption in optionalConfig:
        if thisOption not in ('streambuf', 'smuxver', 'smuxbuf'):
            countALL *= len(options[thisOption])

    candidate_smuxbuf = []
    candidate_streambuf = []
    if 'smuxbuf' in config:
        candidate_smuxbuf = [config['smuxbuf']]
    elif 'smuxbuf' in optionalConfig:
        candidate_smuxbuf = options['smuxbuf']
    else:
        candidate_smuxbuf = ['4194304']
        config['smuxbuf'] = '4194304'

    if 'streambuf' in config:
        candidate_streambuf = [config['streambuf']]
    elif 'streambuf' in optionalConfig:
        candidate_streambuf = options['streambuf']
    else:
        candidate_streambuf = ['2097152']
        config['streambuf'] = '2097152'

    #print(len(candidate_smuxbuf), len(candidate_streambuf))

    count = 0
    for smuxCdd in candidate_smuxbuf:
        for streamCdd in candidate_streambuf:
            if streamCdd > smuxCdd:
                continue
            else:
                count += 1

    if 'smuxver' in config:
        if config['smuxver'] == '1':
            countALL *= len(candidate_smuxbuf)
        else:
            countALL *= count
    elif 'smuxver' in optionalConfig:
        countALL *= (count + len(candidate_smuxbuf))
    else:
        countALL *= len(candidate_smuxbuf)
        config['smuxver'] = '1'

    posSwap('streambuf', 'smuxver')
    posSwap('streambuf', 'smuxbuf')
    posSwap('smuxbuf', 'smuxver')

    return countALL


def Run(args):
    global clientSSH
    global countALL
    global TBEG

    clientSSH = paramiko.SSHClient()
    clientSSH.set_missing_host_key_policy(paramiko.AutoAddPolicy)
    clientSSH.connect(hostname=hostname, port=port, username=username)

    config = setConfig

    print('Searching for:')
    print(optionalConfig)
    countALL = getNumberOptions(config, optionalConfig)

    TBEG = time.time()

    TestOption(config, optionalConfig)
    
    clientSSH.close()
    with open(pathOutJsonFile, 'w+') as file:
        json.dump(logout, file)
    print("")
    return

def CheckConnect(args):

    clientSSH = paramiko.SSHClient()
    clientSSH.set_missing_host_key_policy(paramiko.AutoAddPolicy)
    clientSSH.connect(hostname=hostname, port=port, username=username)

    clientSSH.exec_command("iperf3 -s")
    os.system("iperf3 -c %s -t 2" % hostname)
    clientSSH.exec_command(
        'kill $(ps aux | grep \"iperf3\" | grep -v \"grep\" | awk \'{print $2}\')')
    clientSSH.close()

def Clean(args):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy)
    client.connect(hostname=hostname, port=port, username=username)
    client.exec_command(
        'kill $(ps aux | grep \"%s\" | grep -v \"grep\" | awk \'{print $2}\')' % pathKcptunServer)
    client.close()
    os.system(
        "kill $(ps aux | grep \"%s\" | grep -v \"grep\" | awk \'{print $2}\')" % pathKcptunClient)


def Fetch(args):
    filename = args.LogFile

    with open(filename, 'r') as file:
        data = json.load(file)

    for config, speed in data.items():
        if len(speed) != 2:
            data[config] = 0
            continue
        if len(speed[1]) < 42:
            data[config] = 0
            continue
        speed = float(speed[1][38:42])
        data[config] = speed

    data = [(key, value) for key, value in data.items()]
    data = sorted(data, key=lambda item: item[1], reverse=True)
    print("  Download: |        optional ")
    print("  Mbits/sec |     configurations")
    print("------------|------------------------")
    for i in range(min(10, len(data))):
        # remove unrelative options
        tmp_configs = data[i][0].split(' ')
        out_configs = []
        last_item = None
        for item in tmp_configs:
            if item in ("-l", "-t") or last_item in ("-l", "-t"):
                pass
            elif item == "--quiet":
                pass
            else:
                out_configs.append(item)
            last_item = item

        speed = "{:8.1f}".format(data[i][1])
        print("{}{}| {}".format(speed, ' '*(12-len(speed)), ' '.join(out_configs)))
    return


def main():
    parser = argparse.ArgumentParser("Kcptun testing tool.")
    sub_parsers = parser.add_subparsers()
    run_parset = sub_parsers.add_parser("run", help="run speed test.")
    run_parset.set_defaults(func=Run)

    clean_parset = sub_parsers.add_parser("clean", help="clean remained process.")
    clean_parset.set_defaults(func=Clean)

    fetch_parset = sub_parsers.add_parser("fetch", help="fetch configs from log file.")
    fetch_parset.add_argument(
        "-i", type=str, default=pathOutJsonFile, dest='LogFile', help="specify the log file.")
    fetch_parset.set_defaults(func=Fetch)

    test_parset = sub_parsers.add_parser("test", help="check iperf3 connectivity")
    test_parset.set_defaults(func=CheckConnect)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
