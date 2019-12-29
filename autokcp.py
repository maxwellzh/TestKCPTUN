#!/usr/bin/python3
import os
import sys
import subprocess
import paramiko
import json
import copy
import shlex

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
pathKcptunClient = './client_linux_amd64'
pathOutJsonFile = './log.json'
portKcptunServer = '9990'
portKcptunClient = '9469'
setConfig = {
    'crypt': 'aes',
    'nocomp':'',
    'mode': 'fast2',
    'quiet': '',
    'smuxver': '2'
}
optionList = [
    'sockbuf',
    'smuxbuf'
]
#######################################################

options = {
    'crtpy': [
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
        0,
        5,
        10
    ],
    'parityshard': [x for x in range(11)],
    'nocomp': [
        True,
        False
    ],
    'sockbuf': [
        '4194304',
        '8388608',
        '16777216'
    ],
    'smuxver': [
        '1',
        '2'
    ],
    'smuxbuf': [
        '4194304',
        '8388608',
        '16777216'
    ],
    # streambuf only available on smuxver 2
    'streambuf': [
        '2097152',
        '4194304',
        '8388608'
    ]
}

logout = {}
ifIPv6 = '.' not in hostname
clientSSH = None


def speedtest(config):
    configServer = ' '.join([('--%s %s' % (key, value))
                             for key, value in config.items()])
    configClient = configServer.replace('sndwnd', 'rcvwnd')
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

    global logout

    clientSSH.exec_command("%s %s" % (pathKcptunServer, configServer))

    clientKCP = subprocess.Popen(shlex.split("%s %s" % (pathKcptunClient, configClient)))

    infoiperf = os.popen('iperf3 -c ::1 -p %s -i 5 -t 5 -R' % portKcptunClient)
    infoiperf = infoiperf.readlines()

    logout[configServer] = infoiperf[-4:-2]
    with open(pathOutJsonFile, 'w+') as file:
        json.dump(logout, file)

    clientSSH.exec_command(
        'kill $(ps aux | grep \"%s\" | grep -v \"grep\" | awk \'{print $2}\')' % pathKcptunServer)
    clientKCP.kill()
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
        # streambuf should be smaller than sockbuf
        if thisOption == 'streambuf':
            if candidate > config['smuxbuf']:
                continue
        config[thisOption] = candidate
        if len(optionList) == 0:
            speedtest(config)
        else:
            TestOption(config, optionList)
        del config[thisOption]
    optionList.append(thisOption)
    return

def Run():
    global clientSSH
    clientSSH = paramiko.SSHClient()
    clientSSH.set_missing_host_key_policy(paramiko.AutoAddPolicy)
    clientSSH.connect(hostname=hostname, port=port, username=username)

    config = setConfig
    if 'smuxver' not in config:
        config['smuxver'] = '1'
    if 'smuxbuf' not in config:
        config['smuxbuf'] = '4194304'
    posSwap('streambuf', 'smuxver')
    posSwap('streambuf', 'smuxbuf')

    print(optionList)
    TestOption(config, optionList)

    clientSSH.close()
    with open(pathOutJsonFile, 'w+') as file:
        json.dump(logout, file)
    os.system('clear')
    return

def Clean():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy)
    client.connect(hostname=hostname, port=port, username=username)
    client.exec_command('kill $(ps aux | grep \"%s\" | grep -v \"grep\" | awk \'{print $2}\')' % pathKcptunServer)
    client.close()
    os.system("kill $(ps aux | grep \"%s\" | grep -v \"grep\" | awk \'{print $2}\')" % pathKcptunClient)  

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
        print("Download: %.1fMbits/sec" % data[i][1])
    return

def main():
    if len(sys.argv[1:]) == 0:
        print("Require a command followed with script.")
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
    return


if __name__ == "__main__":
    main()
