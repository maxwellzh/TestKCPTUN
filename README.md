# TestKCPTUN

A script for speedtest and get the best config of kcptun.

简单的python脚本用于测试获得[KCPTUN](https://github.com/xtaci/kcptun)的**最优**（带宽最大）配置。

## 依赖

1. Python3.6+. 请自行搜索如何安装（*nix系统应该都有自带的python3程序，但是有些可能是python3.5，不保证能正常运行，或许可用）；

2. OS: OSX/Linux，如果是windows建议用WSL

3. 安装依赖包：

   ```shell
   pip3 install -r requiements.txt --user
   ```

4. iperf3，服务器和本地都需要安装

   ```shell
   # for ubuntu
   sudo apt install iperf3
   # for macOS, firstly install homebrew, then run
   brew install iperf3
   ```

5. 将服务器设置为免密码登录方式（**请在自己的计算机上执行本操作，非个人计算机请勿执行**）

   首先看本机上有没有ssh-key

   ```shell
   ls ~/.ssh/id_rsa.pub
   ```

   如果没有这个文件（有可以跳过这一步），运行

   ```shell
   ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
   ```

   中间一直按回车即可；

   将本机ssh-key发送到服务器

   ```shell
   ssh-copy-id -i ~/.ssh/id_rsa.pub user@host
   ```

   一般来说会需要输入服务器的密码，输入即可。

6. 本机下载了kcptun客户端，远程服务器下载有kcptun服务端

## 使用

1. 在文件`config.json`中的，填入对应的信息

   ```json
   {
       "base":{
           "hostname" : "192.168.0.1",
           "port" : 22,
           "username" : "root",
           "pathKcptunServer" : "/kcptun/server_linux_amd64",
           "pathKcptunClient" : "./client_darwin_amd64",
           "pathOutJsonFile" : "./log.json",
           "portKcptunServer" : "9990",
           "portKcptunClient" : "9469",
           "errorSkip" : true
       },
       "setConfig" : {
           "crypt": "aes",
           "sndwnd": "1024",
           "rcvwnd": "1024",
           "quiet": "",
           "nocomp":""
       },
       "optionalConfig" : [
           "parityshard",
           "datashard"
       ]
   }
   ```
   
   各个参数的意义：
   
   - `hostname`：服务器IP地址，支持IPv4和IPv6（IPv6地址不用加中括号）
   - `port`：ssh登录端口，一般默认`22`即可
   - `username`：ssh用户名，默认是`root`
   - `pathKcptunServer`：服务器端kcptun程序的位置（建议用绝对路径）
- `pathKcptunClient`：客户端kcptun程序的位置（建议用绝对路径）
   - `pathOutJsonFile`：测速结果输出文件
- `portKcptunServer`：服务端kcptun监听端口，如果没冲突默认即可
   - `portKcptunClient`：客户端kcptun监听端口，如果没冲突默认即可
   - `errorSkip`：iperf3出错时是否自动跳过错误，默认为`true`，如果希望出错后脚本停止可设置为`false`
   - `setconfig`：设定**服务端**部分固定不需要改的配置（客户端配置会自动生成）
   - `optionalConfig`：添加需要搜索的选项
   
2. 在远端服务器上运行iperf3（在本地启动有问题尚未解决，因此需要在远端服务器运行）

   ```bash
   iperf3 -s
   ```

3. 在本地运行命令，测试一下服务器iperf3是否正常

   ```bash
   iperf3 -c  hostname -t 2
   ```

   如果一切服务器连接正常应该输出类似下面的结果

   ```bash
   Connecting to host hostname, port 5201
   [  5] local localIP port 65484 connected to hostname port 5201
   [ ID] Interval           Transfer     Bitrate
   [  5]   0.00-1.00   sec   140 KBytes  1.14 Mbits/sec
   [  5]   1.00-2.01   sec  44.0 KBytes   360 Kbits/sec
   - - - - - - - - - - - - - - - - - - - - - - - - -
   [ ID] Interval           Transfer     Bitrate
   [  5]   0.00-2.01   sec   184 KBytes   750 Kbits/sec                  sender
   [  5]   0.00-2.01   sec  81.8 KBytes   334 Kbits/sec                  receiver

   iperf Done.
   ```

   网络连接问题请自行Baidu/Google查询

4. 若连接正常即可运行脚本

   ```bash
   python3 autokcp.py run
   ```

5. 等待结果

## 其他

1. 脚本运行时间取决于搜索的参数选项数量，示例中搜索了`parityshard`和`datashard`，总搜索次数40，需要搜索时间大约为3min28s，还是需要比较多时间的，所以建议一次不要同时搜索太多参数；

2. **按流量计费的VPS谨慎使用**，会产生大量流量消耗（～T\*Bandwidth)

3. 脚本运行中如果出错了，或者是人为中断后，请运行以下命令以清理进程（可能需要等一会儿）

   ```shell
   python3 autokcp.py clean
   ```

   运行后可能会出现如下内容，这是正常现象

   ```shell
   kill: usage: kill [-s sigspec | -n signum | -sigspec] pid | jobspec ... or kill -l [sigspec]
   ```

4. 从日志文件中获取最优配置信息

   ```shell
   python3 autokcp.py fetch
   ```

## 使用示例

1. 固定其他配置，搜索不同加密方式对于速度的影响

   ```json
   "setConfig" : {
           "sndwnd": "1024",
           "rcvwnd": "1024",
           "quiet": "",
           "nocomp":""
       },
   "optionalConfig" : [
           "crypt"
       ]
   ```

   运行脚本，等待测试结束后，运行`python3 autokcp.py fetch`结果如下

   ```shell
     Download: |        optional 
     Mbits/sec |     configurations
   ------------|------------------------
       44.9    | --sndwnd 1024 --rcvwnd 1024  --nocomp  --smuxbuf 4194304 --streambuf 2097152 --smuxver 1 --crypt blowfish
       39.6    | --sndwnd 1024 --rcvwnd 1024  --nocomp  --smuxbuf 4194304 --streambuf 2097152 --smuxver 1 --crypt cast5
       38.4    | --sndwnd 1024 --rcvwnd 1024  --nocomp  --smuxbuf 4194304 --streambuf 2097152 --smuxver 1 --crypt tea
       36.0    | --sndwnd 1024 --rcvwnd 1024  --nocomp  --smuxbuf 4194304 --streambuf 2097152 --smuxver 1 --crypt twofish
       35.3    | --sndwnd 1024 --rcvwnd 1024  --nocomp  --smuxbuf 4194304 --streambuf 2097152 --smuxver 1 --crypt xor
       34.3    | --sndwnd 1024 --rcvwnd 1024  --nocomp  --smuxbuf 4194304 --streambuf 2097152 --smuxver 1 --crypt xtea
       31.7    | --sndwnd 1024 --rcvwnd 1024  --nocomp  --smuxbuf 4194304 --streambuf 2097152 --smuxver 1 --crypt aes-192
       29.9    | --sndwnd 1024 --rcvwnd 1024  --nocomp  --smuxbuf 4194304 --streambuf 2097152 --smuxver 1 --crypt aes
       27.7    | --sndwnd 1024 --rcvwnd 1024  --nocomp  --smuxbuf 4194304 --streambuf 2097152 --smuxver 1 --crypt sm4
       27.0    | --sndwnd 1024 --rcvwnd 1024  --nocomp  --smuxbuf 4194304 --streambuf 2097152 --smuxver 1 --crypt salsa20
   ```

2. 固定其他配置，搜索不同`mode`对于速度的影响

   ```json
   "setConfig" : {
           "sndwnd": "1024",
           "rcvwnd": "1024",
           "quiet": "",
           "nocomp":""
       },
   "optionalConfig" : [
           "mode"
    ]
   ```

   运行脚本，等待搜索结束后，运行`python3 autokcp.py fetch`结果如下
   
   ```shell
     Download: |        optional 
     Mbits/sec |     configurations
   ------------|------------------------
       39.6    | --sndwnd 1024 --rcvwnd 1024  --nocomp  --smuxbuf 4194304 --streambuf 2097152 --smuxver 1 --mode fast
       37.3    | --sndwnd 1024 --rcvwnd 1024  --nocomp  --smuxbuf 4194304 --streambuf 2097152 --smuxver 1 --mode fast2
       25.4    | --sndwnd 1024 --rcvwnd 1024  --nocomp  --smuxbuf 4194304 --streambuf 2097152 --smuxver 1 --mode fast3
       25.1    | --sndwnd 1024 --rcvwnd 1024  --nocomp  --smuxbuf 4194304 --streambuf 2097152 --smuxver 1 --mode normal
   ```
