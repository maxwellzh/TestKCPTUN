#!/usr/bin/python3
import os
import sys
import subprocess
import paramiko
import json
import copy
import shlex
import time

deepcp = copy.deepcopy

####################  Modify here  ####################
# hostname Examples:
# IPv4:
#     hostname = '192.168.0.1'
# IPv6:
#     hostname = 'ff08::1'
hostname = '192.168.0.1'
port = 22
username = 'root'
pathKcptunServer = '/root/kcptun/server_linux_amd64'
pathKcptunClient = './client_darwin_amd64'
pathOutJsonFile = './log.json'
portKcptunServer = '9990'
portKcptunClient = '9469'
errorSkip = True
setConfig = {
    'crypt': 'aes',
    'sndwnd': '1024',
    'rcvwnd': '256',
    'quiet': '',
    'nocomp':''
}
optionList = [
    'mode',
    'streambuf',
    'smuxbuf',
    'smuxver'
]
#######################################################

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
    'parityshard': [x for x in range(1 + 10)],
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
        print("\r[%02.0f:%02.0f:%02.0f]: %4.0f/%.0f" %
              (sec2time(time.time()-TBEG) + (countDone, countALL)), end='')

    return


'''
if pos[optionA] > pos[optionB]:
    swap(pos[A], pos[B])
'''


def posSwap(optionA, optionB):
    if optionA in optionList and optionB in optionList:
        tmpA = optionList.index(optionA)
        tmpB = optionList.index(optionB)
        if tmpA > tmpB:
            optionList[tmpA] = optionB
            optionList[tmpB] = optionA


def addconfig(config, config_stack, info):
    config = deepcp(config_stack)
    config.append(info)
    config_stack.append(info)
    return config, config_stack


def TestOption(config, optionList):

    if len(optionList) == 0:
        print("optionList should has at least one element.")
        exit(-1)

    thisOption = optionList.pop()
    if thisOption == 'streambuf' and config['smuxver'] == '1':
        if len(optionList) == 0:
            speedtest(config)
        else:
            TestOption(config, optionList)
        optionList.append(thisOption)
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
        if len(optionList) == 0:
            speedtest(config)
        else:
            TestOption(config, optionList)
        del config[thisOption]
    optionList.append(thisOption)
    return


def getNumberOptions(config, optionList):
    countALL = 1

    for thisOption in optionList:
        if thisOption not in ('streambuf', 'smuxver', 'smuxbuf'):
            countALL *= len(options[thisOption])

    candidate_smuxbuf = []
    candidate_streambuf = []
    if 'smuxbuf' in config:
        candidate_smuxbuf = [config['smuxbuf']]
    elif 'smuxbuf' in optionList:
        candidate_smuxbuf = options['smuxbuf']
    else:
        candidate_smuxbuf = ['4194304']
        config['smuxbuf'] = '4194304'

    if 'streambuf' in config:
        candidate_streambuf = [config['streambuf']]
    elif 'streambuf' in optionList:
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
    elif 'smuxver' in optionList:
        countALL *= (count + len(candidate_smuxbuf))
    else:
        countALL *= len(candidate_smuxbuf)
        config['smuxver'] = '1'

    posSwap('streambuf', 'smuxver')
    posSwap('streambuf', 'smuxbuf')
    posSwap('smuxbuf', 'smuxver')

    return countALL


def Run():
    global clientSSH
    global countALL
    global TBEG

    clientSSH = paramiko.SSHClient()
    clientSSH.set_missing_host_key_policy(paramiko.AutoAddPolicy)
    clientSSH.connect(hostname=hostname, port=port, username=username)

    config = setConfig

    print('Searching for:')
    print(optionList)
    countALL = getNumberOptions(config, optionList)
    #print(countALL)
    print('Est time: %02.0f:%02.0f:%02.0f' % (sec2time(countALL * 3.18)))
    TBEG = time.time()

    TestOption(config, optionList)

    clientSSH.close()
    with open(pathOutJsonFile, 'w+') as file:
        json.dump(logout, file)
    print("")
    return


def Clean():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy)
    client.connect(hostname=hostname, port=port, username=username)
    client.exec_command(
        'kill $(ps aux | grep \"%s\" | grep -v \"grep\" | awk \'{print $2}\')' % pathKcptunServer)
    client.close()
    os.system(
        "kill $(ps aux | grep \"%s\" | grep -v \"grep\" | awk \'{print $2}\')" % pathKcptunClient)


def Process(filename=pathOutJsonFile):

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
    for i in range(min(10, len(data))):
        print(data[i][0])
        print('=' * 24)
        print("Download: %.1fMbits/sec" % data[i][1])
        print('=' * 24)
    return


def main():
    if len(sys.argv[1:]) == 0:
        print("Require a command followed with script.\nAvailable command: run, clean, process")
        exit(-1)

    if sys.argv[1] == 'run':
        Run()
        Process()
    elif sys.argv[1] == 'clean':
        Clean()
    elif sys.argv[1] == 'process':
        if sys.argv[1:] == 2:
            Process(sys.argv[2])
        else:
            Process()
    else:
        print(
            "Unknown command \'%s\'.\nAvailable command: run, clean, process" % sys.argv[1])
        exit(-1)
    return


if __name__ == "__main__":
    main()
